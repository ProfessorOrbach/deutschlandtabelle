"""Adapter für handball.net -- der Spielbetrieb des DHB.

Die Seite handball.net führt ihren Wettbewerbsbaum über eine JSON-Schnittstelle,
die ohne Anmeldung antwortet -- sie verlangt allerdings einen `Referer`-Header,
sonst kommt HTTP 403 zurück.

    /api/new/competitions?season_id=<jjjj>&per_page=100&page=<n>
                          &has_phases=1&with_phases=1
        -> Wettbewerbe mit ihren Phasen; jede Phase trägt federation_id,
           Geschlecht und ein Flag has_standings

    /api/new/standings?phase_id=<id>
        -> die Tabelle: position, played, won, drawn, lost,
           goals_for, goals_against, points

    /api/new/federations/<id>
        -> Name des Verbands bzw. Kreises

Anders als beim Fußball muss die Ligastufe nicht je Landesverband hergeleitet
werden: handball.net führt zu jedem Wettbewerb eine `category`, deren Name
bundesweit vereinheitlicht ist ("Bezirksoberliga / Kreisoberliga /
Regionsoberliga"). Elf Namen decken die ganze Pyramide ab.

Vorsicht bei den Kategorie-*IDs*: die sind nicht die Ligastufe und wiederholen
sich je Altersklasse und Geschlecht -- id 3 und id 16 heißen beide "3. Liga".
Maßgeblich ist deshalb der Name.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENABLED = True

BASE = "https://www.handball.net/api/new"
REFERER = "https://www.handball.net/spielbetrieb/wettbewerbe"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Nur Erwachsene, nur Männer -- Jugend läuft unter eigenen Meisterschaften und
# teils unter dem Geschlecht "X" (gemischt).
MEISTERSCHAFT = "ERWACHSENE"
GESCHLECHT = "M"

# Freundschaftsspiele, Test- und Pokalrunden laufen bei handball.net unter
# denselben Feldern wie der Ligabetrieb: competition_type_id ist durchgängig 0,
# und einem Freundschaftsspiel wird munter die Kategorie "Oberliga" verpasst.
# Ein struktureller Marker fehlt also -- bleibt der Name.
KEIN_LIGABETRIEB = re.compile(
    r"freundschaft|testspiel|pokal|cup|qualifikation|turnier", re.I)

# Der bundesweit vereinheitlichte Kategoriename bestimmt die Ligastufe.
# Die 1. und 2. Bundesliga führt die HBL auf einer eigenen Plattform; sie
# fehlen hier und damit auch im Ranking -- siehe README.
TIER_BY_CATEGORY = {
    "3. Liga": 3,
    "Regionalliga": 4,
    "Oberliga": 5,
    "Verbandsliga": 6,
    "Landesliga": 7,
    "Bezirksoberliga / Kreisoberliga / Regionsoberliga": 8,
    "Bezirksliga / Kreisliga / Regionsliga": 9,
    "Bezirksklasse / Kreisklasse / Regionsklasse": 10,
    "2. Bezirksklasse / 2. Kreisklasse / 2. Regionsklasse": 11,
    "3. Bezirksklasse / 3. Kreisklasse / 3. Regionsklasse": 12,
    "4. Bezirksklasse / 4. Kreisklasse / 4. Regionsklasse": 13,
}

TIER_LABEL = {
    3: "3. Liga", 4: "4. Liga (Regionalliga)", 5: "5. Liga (Oberliga)",
    **{n: f"{n}. Ligastufe" for n in range(6, 14)},
}


def season_code(season: int) -> str:
    """2026 -> '2627', dieselbe Schreibweise wie beim Fußball."""
    return f"{season % 100:02d}{(season + 1) % 100:02d}"


def _titel(text: str) -> str:
    """handball.net liefert Namen in Versalien -- lesbar machen.

    Kurze Wörter bleiben groß, weil das fast immer Abkürzungen sind (VFL, TUS,
    HSG, MT). Längere werden kapitalisiert, auch nach Bindestrich und Schrägstrich
    ("RHEIN-NECKAR" -> "Rhein-Neckar"). Die originale Binnenschreibung mancher
    Vereine lässt sich aus Versalien nicht zurückgewinnen -- aus "VFL" wird
    hier "VFL" und nicht "VfL".
    """
    if not text or not text.isupper():
        return text
    def wort(w: str) -> str:
        if len(w) <= 4 and w.isalpha():
            return w
        teile = re.split(r"([-/.])", w)
        return "".join(t if t in "-/." else t.capitalize() for t in teile)
    return " ".join(wort(w) for w in text.split())


class HandballNet:
    def __init__(self, cache_dir: Path, min_interval: float = 0.6,
                 ttl: float = 3 * 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.ttl = ttl
        self._last = 0.0

    def _get(self, pfad: str):
        url = f"{BASE}/{pfad}"
        key = hashlib.sha1(url.encode()).hexdigest()[:20]
        blob = self.cache_dir / f"hbn_{key}.json"
        if blob.exists() and (time.time() - blob.stat().st_mtime) < self.ttl:
            try:
                return json.loads(blob.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Referer": REFERER, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
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

    # -- Discovery --------------------------------------------------------
    def wettbewerbe(self, season: int) -> list[dict]:
        """Alle Wettbewerbe der Saison, über alle Seiten."""
        sc = season_code(season)
        raus, seite = [], 1
        while True:
            d = self._get(f"competitions?season_id={sc}&per_page=100&page={seite}"
                          f"&has_phases=1&with_phases=1")
            if not d or not d.get("data"):
                break
            raus += d["data"]
            pg = d.get("pagination") or {}
            if seite >= (pg.get("last_page") or 1):
                break
            seite += 1
        return raus

    def verband(self, federation_id: int) -> str | None:
        d = self._get(f"federations/{federation_id}")
        daten = (d or {}).get("data") or {}
        return _titel(daten.get("name")) if daten.get("name") else None

    def tabelle(self, phase_id: int) -> list[dict]:
        """Aktuelle Tabelle einer Staffel.

        Achtung: der Endpunkt liefert eine Zeile je Mannschaft *und geplantem
        Spieltag* -- eine 16er-Staffel mit 30 Spieltagen ergibt 480 Zeilen, die
        derzeit alle denselben Stand tragen. Deshalb wird je Mannschaft die
        Zeile mit den meisten absolvierten Spielen genommen; das bleibt auch
        richtig, wenn die Runden im Saisonverlauf auseinanderlaufen.
        """
        d = self._get(f"standings?phase_id={phase_id}")
        neueste: dict[object, dict] = {}
        for z in (d or {}).get("data") or []:
            team = z.get("team") or {}
            tid = team.get("id") or team.get("name")
            if tid is None:
                continue
            rang = (z.get("played") or 0, z.get("round") or 0)
            vorhanden = neueste.get(tid)
            if vorhanden is None or rang > vorhanden[0]:
                neueste[tid] = (rang, z)

        zeilen = []
        for _, z in sorted(neueste.values(), key=lambda p: p[1].get("position") or 0):
            team = z.get("team") or {}
            name = team.get("name") or (team.get("club") or {}).get("name")
            if not name:
                continue
            try:
                zeilen.append({
                    "name": _titel(name),
                    "played": int(z.get("played") or 0),
                    "won": int(z.get("won") or 0),
                    "drawn": int(z.get("drawn") or 0),
                    "lost": int(z.get("lost") or 0),
                    "goals_for": int(z.get("goals_for") or 0),
                    "goals_against": int(z.get("goals_against") or 0),
                    "points": int(z.get("points") or 0),
                })
            except (TypeError, ValueError):
                continue
        return zeilen


def fetch(cache_dir: Path, season: int, verbose: bool = True) -> list[dict]:
    """Liefert je Staffel {name, tier, verband, area, spielklasse, rows}."""
    if not ENABLED:
        return []
    client = HandballNet(cache_dir)
    wettbewerbe = client.wettbewerbe(season)
    if verbose:
        print(f"  handball.net: {len(wettbewerbe)} Wettbewerbe", file=sys.stderr)

    kandidaten = []
    unbekannt: dict[str, int] = {}
    for w in wettbewerbe:
        meisterschaft = (w.get("championship") or {}).get("name")
        if meisterschaft != MEISTERSCHAFT:
            continue
        if KEIN_LIGABETRIEB.search(w.get("name") or ""):
            continue
        kategorie = (w.get("category") or {}).get("name")
        tier = TIER_BY_CATEGORY.get(kategorie)
        if tier is None:
            if kategorie:
                unbekannt[kategorie] = unbekannt.get(kategorie, 0) + 1
            continue
        for ph in w.get("phases") or []:
            if (ph.get("gender") or {}).get("id") != GESCHLECHT:
                continue
            if not ph.get("has_standings"):
                continue
            if KEIN_LIGABETRIEB.search(ph.get("name") or ""):
                continue
            kandidaten.append({
                "phase_id": ph["id"], "tier": tier, "spielklasse": kategorie,
                "name": ph.get("name") or w.get("name"),
                "federation_id": ph.get("federation_id"),
            })
    if verbose:
        print(f"  handball.net: {len(kandidaten)} Männer-Staffeln (Erwachsene)",
              file=sys.stderr)
        if unbekannt:
            print(f"  handball.net: ohne Ligastufe übersprungen: {unbekannt}",
                  file=sys.stderr)

    verbaende: dict[int, str | None] = {}
    raus, leer = [], 0
    benutzt: set[str] = set()
    for k in sorted(kandidaten, key=lambda k: (k["tier"], k["name"])):
        fid = k["federation_id"]
        if fid not in verbaende:
            verbaende[fid] = client.verband(fid) if fid else None
        zeilen = client.tabelle(k["phase_id"])
        if not zeilen:
            leer += 1
            continue
        label = k["name"]
        if label in benutzt:
            label = f"{label} · {verbaende[fid] or k['phase_id']}"
        if label in benutzt:
            label = f"{label} ({k['phase_id']})"
        benutzt.add(label)
        raus.append({
            "name": label, "tier": k["tier"], "verband": verbaende[fid],
            "area": verbaende[fid], "spielklasse": k["spielklasse"],
            "staffel": str(k["phase_id"]), "rows": zeilen,
        })
    if verbose:
        mannschaften = sum(len(g["rows"]) for g in raus)
        print(f"  handball.net: {len(raus)} Staffeln mit Tabelle, "
              f"{mannschaften} Mannschaften ({leer} ohne Tabelle)", file=sys.stderr)
    return raus
