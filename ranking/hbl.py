"""Adapter für die 1. und 2. Handball-Bundesliga.

Die HBL läuft nicht über handball.net, sondern auf einer eigenen Seite
(opel-hbl.de), deren Tabellen-Widget von Sportradar kommt:

    https://embed-api.eui.connect.sportradar.com/v1/embed/<id>/standings?locale=de-DE

Der Endpunkt antwortet ohne jeden Header. Saison-Parameter ignoriert er --
jede Embed-ID ist fest auf einen Wettbewerb *und* dessen laufende Saison
konfiguriert. Deshalb sind die IDs hier hart hinterlegt, und zur Sicherheit
wird der Wettbewerbsname gegengeprüft: Embed 257 etwa liefert ebenfalls
18 Mannschaften der 1. Bundesliga, aber die abgeschlossene Vorsaison.

Punkte stehen im deutschen Handball-Format "4:0" (Plus- zu Minuspunkten); es
zählt die Zahl vor dem Doppelpunkt. Das passt zum Zwei-Punkte-System, das auch
handball.net liefert.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENABLED = True

BASE = "https://embed-api.eui.connect.sportradar.com/v1/embed"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# (Embed-ID, Ligastufe, erwarteter Wettbewerbsname, Anzeigename)
LIGEN = [
    (248, 1, "1. Handball-Bundesliga", "1. Handball-Bundesliga"),
    (254, 2, "2. Handball-Bundesliga", "2. Handball-Bundesliga"),
]


class Sportradar:
    def __init__(self, cache_dir: Path, min_interval: float = 0.6,
                 ttl: float = 3 * 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.ttl = ttl
        self._last = 0.0

    def standings(self, embed_id: int):
        url = f"{BASE}/{embed_id}/standings?locale=de-DE"
        key = hashlib.sha1(url.encode()).hexdigest()[:20]
        blob = self.cache_dir / f"srd_{key}.json"
        if blob.exists() and (time.time() - blob.stat().st_mtime) < self.ttl:
            try:
                return json.loads(blob.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                text = resp.read().decode("utf-8", "ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            self._last = time.monotonic()
            return None
        self._last = time.monotonic()
        try:
            daten = json.loads(text)
        except json.JSONDecodeError:
            return None
        blob.write_text(text, encoding="utf-8")
        return daten


def _punkte(wert) -> int:
    """"4:0" -> 4. Auch eine blanke Zahl wird akzeptiert."""
    if isinstance(wert, (int, float)):
        return int(wert)
    text = str(wert or "0")
    return int(text.split(":")[0].strip() or 0)


def fetch(cache_dir: Path, verbose: bool = True) -> list[dict]:
    """Liefert je Liga {name, tier, verband, area, spielklasse, staffel, rows}."""
    if not ENABLED:
        return []
    client = Sportradar(cache_dir)
    raus = []
    for embed_id, tier, erwartet, anzeige in LIGEN:
        antwort = client.standings(embed_id)
        daten = (antwort or {}).get("data") or {}
        namen = {c.get("name") for c
                 in ((daten.get("seasons") or {}).get("competitions") or {}).values()}
        if erwartet not in namen:
            # Die Embed-ID zeigt auf etwas anderes als erwartet -- lieber
            # auslassen als eine falsche Liga einmischen.
            print(f"  HBL: Embed {embed_id} liefert {namen or 'nichts'}, "
                  f"erwartet war {erwartet!r} — übersprungen", file=sys.stderr)
            continue
        zeilen = []
        for gruppe in daten.get("standings") or []:
            for z in gruppe.get("rows") or []:
                team = z.get("team") or {}
                erg = z.get("results") or {}
                if not team.get("name"):
                    continue
                zeilen.append({
                    "name": team["name"],
                    "played": int(erg.get("played") or 0),
                    "won": int(erg.get("wins") or 0),
                    "drawn": int(erg.get("draws") or 0),
                    "lost": int(erg.get("losses") or 0),
                    "goals_for": int(erg.get("scoredFor") or 0),
                    "goals_against": int(erg.get("scoredAgainst") or 0),
                    "points": _punkte(erg.get("combinedStandingPoints")),
                })
        if not zeilen:
            continue
        raus.append({
            "name": anzeige, "tier": tier, "verband": None, "area": None,
            "spielklasse": anzeige, "staffel": f"hbl-{embed_id}", "rows": zeilen,
        })
        if verbose:
            print(f"  HBL: {anzeige} — {len(zeilen)} Mannschaften", file=sys.stderr)
    return raus
