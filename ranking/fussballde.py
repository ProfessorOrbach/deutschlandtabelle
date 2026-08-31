"""Adapter für fussball.de -- Staffeln unterhalb der Regionalliga.

Hintergrund: OpenLigaDB endet faktisch bei Ligastufe 4. Der Ergebnisdienst von
oberberg-aktuell.de, der ursprünglich als Quelle vorgeschlagen war, enthält
selbst keine Daten -- er verlinkt ausschließlich auf fussball.de. Von dort
stammen die Zahlen hier.

RECHTLICHER HINWEIS: Die Nutzungsbedingungen von fussball.de untersagen das
automatisierte Auslesen. Dieser Adapter ist ein Entwurf und lässt sich mit
`python3 build.py --no-fussballde` bzw. ENABLED = False abschalten. Für den
produktiven Betrieb ist der saubere Weg die DFBnet-Datenschnittstelle oder ein
lizenzierter Anbieter -- siehe PLAN.md §3.

Staffel-Discovery über die WAM-Schnittstelle
--------------------------------------------
Der Matchkalender von fussball.de füllt seine Auswahllisten aus statischen
JSON-Dateien. Damit lässt sich der Wettbewerbsbaum vollständig ablaufen, ohne
Staffel-IDs von Hand zu pflegen:

    wam_kinds_<mandant>_<saison>_<typ>.json
        -> Mannschaftsart -> Spielklasse -> Gebiet (die Fußballkreise)

    wam_competitions_<mandant>_<saison>_<typ>_<art>_<klasse>_<gebiet>.json
        -> {Staffel-URL: Anzeigename}, die URL enthält die Staffel-ID
           der laufenden Saison

Dadurch folgt der Adapter dem Saisonwechsel und neu eingerichteten Staffeln von
selbst. Für den kompletten Mittelrhein sind das rund 36 Discovery-Abrufe plus
ein Tabellenabruf je Staffel.

Geliefert werden fertige Tabellen, keine Einzelspiele: die Spielliste baut
fussball.de erst im Browser per JavaScript auf. Deshalb fehlt diesen Staffeln
die Vorwochen-Differenz -- ohne Spieldaten mit Datum lässt sie sich nicht
nachrechnen.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENABLED = True

BASE = "https://www.fussball.de"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

MANDANT = "23"        # Fußball-Verband Mittelrhein
COMP_TYPE = "1"       # Meisterschaften (keine Pokale, Turniere, Freundschaftsspiele)
TEAM_TYPE = "95"      # Herren
VERBAND = "Mittelrhein"

# Spielklassen-ID -> Ligastufe. Die Zuordnung gilt für den Mittelrhein; andere
# Landesverbände bauen ihre Pyramide anders (Bayern etwa mit Kreisklasse und
# A-Klasse unterhalb der Kreisliga). Für eine Ausweitung braucht jeder Verband
# seine eigene Tabelle.
TIER_BY_LEAGUE = {
    "129": 5,    # Verbandsliga = Mittelrheinliga
    "130": 6,    # Landesliga
    "132": 7,    # Bezirksliga
    "135": 8,    # Kreisliga A
    "136": 9,    # Kreisliga B
    "137": 10,   # Kreisliga C
    "138": 11,   # Kreisliga D
}

# fussball.de setzt in Vereinsnamen unsichtbare Trennzeichen, etwa
# "SG Hämmern /<U+200B> Heide". Die müssen vor der Anzeige raus.
_INVISIBLE = re.compile(r"[​‌‍­﻿]")


def _clean(fragment: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    text = _INVISIBLE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def season_code(season: int) -> str:
    """2026 -> '2627' (Schreibweise von fussball.de)."""
    return f"{season % 100:02d}{(season + 1) % 100:02d}"


class FussballDe:
    def __init__(self, cache_dir: Path, min_interval: float = 1.0,
                 ttl: float = 3 * 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.ttl = ttl
        self._last = 0.0

    def _get(self, url: str) -> str:
        key = hashlib.sha1(url.encode()).hexdigest()[:20]
        blob = self.cache_dir / f"fde_{key}.txt"
        if blob.exists() and (time.time() - blob.stat().st_mtime) < self.ttl:
            return blob.read_text(encoding="utf-8")
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", "ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            self._last = time.monotonic()
            return ""
        self._last = time.monotonic()
        # Leere Antworten nicht zwischenspeichern: fussball.de liefert HTTP 200
        # mit 0 Bytes für Staffeln, die noch nicht veröffentlicht sind. Sobald
        # sie starten, soll der nächste Lauf sie sofort sehen.
        if text.strip():
            blob.write_text(text, encoding="utf-8")
        return text

    def _json(self, url: str):
        raw = self._get(url)
        try:
            return json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            return None

    # -- Discovery --------------------------------------------------------
    def discover(self, season: int) -> list[dict]:
        """Alle Herren-Meisterschaftsstaffeln des Verbands der laufenden Saison."""
        sc = season_code(season)
        kinds = self._json(f"{BASE}/wam_kinds_{MANDANT}_{sc}_{COMP_TYPE}.json")
        if not kinds:
            return []
        areas_by_league = (kinds.get("Gebiet") or {}).get(TEAM_TYPE, {})
        out: list[dict] = []
        for league_id, tier in TIER_BY_LEAGUE.items():
            for area_key, area_name in (areas_by_league.get(league_id) or {}).items():
                area = area_key.lstrip("_")
                data = self._json(
                    f"{BASE}/wam_competitions_{MANDANT}_{sc}_{COMP_TYPE}"
                    f"_{TEAM_TYPE}_{league_id}_{area}.json")
                if not data:
                    continue
                for by_area in data.values():
                    for comps in by_area.values():
                        for url, name in comps.items():
                            sid = re.search(r"/staffel/([0-9A-Z]+-[GC])", url)
                            if sid:
                                out.append({"tier": tier, "area": area_name,
                                            "name": name, "staffel": sid.group(1)})
        return out

    # -- Tabelle ----------------------------------------------------------
    def table(self, staffel_id: str) -> list[dict]:
        """Tabelle einer Staffel: Platz, Mannschaft, Sp, G, U, V, Tore, Pkt."""
        page = self._get(f"{BASE}/ajax.table/-/staffel/{staffel_id}")
        body = re.search(r"<tbody>(.*?)</tbody>", page, re.S)
        if not body:
            return []
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S):
            cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            cells = [c for c in cells if c]
            # Spalten laut <thead>: Pl. | Mannschaft | Sp. | G | U | V |
            #                       Torverhältnis | Tordifferenz | Punkte
            # Davor steht eine leere Wappenzelle, die oben herausfällt.
            if len(cells) < 9 or not re.match(r"^\d+\.$", cells[0]):
                continue
            goals = re.match(r"^(\d+)\s*:\s*(\d+)$", cells[6])
            if not goals:
                continue
            try:
                rows.append({
                    "name": cells[1],
                    "played": int(cells[2]),
                    "won": int(cells[3]),
                    "drawn": int(cells[4]),
                    "lost": int(cells[5]),
                    "goals_for": int(goals.group(1)),
                    "goals_against": int(goals.group(2)),
                    # Punkte stehen immer ganz rechts, auch wenn fussball.de
                    # weitere Spalten ergänzt.
                    "points": int(cells[-1]),
                })
            except ValueError:
                continue
        return rows


def _label(entry: dict) -> str:
    """Eindeutiger Anzeigename. "Kreisliga A" gibt es in jedem der neun Kreise,
    deshalb muss der Kreis ab Stufe 8 mit in den Namen."""
    if entry["tier"] >= 8:
        return f"{entry['name']} · {entry['area']}"
    return entry["name"]


def fetch(cache_dir: Path, season: int, verbose: bool = True) -> list[dict]:
    """Liefert je Staffel {name, tier, verband, rows}. Leere Staffeln entfallen."""
    if not ENABLED:
        return []
    client = FussballDe(cache_dir)
    entries = client.discover(season)
    if verbose:
        print(f"  fussball.de: {len(entries)} Staffeln im Verband {VERBAND} gefunden",
              file=sys.stderr)

    out: list[dict] = []
    used: set[str] = set()
    empty = 0
    for entry in sorted(entries, key=lambda e: (e["tier"], e["area"], e["name"])):
        rows = client.table(entry["staffel"])
        if not rows:
            empty += 1
            continue
        label = _label(entry)
        if label in used:                       # Notnagel gegen Namensgleichheit
            label = f"{label} ({entry['staffel'][:6]})"
        used.add(label)
        out.append({"name": label, "tier": entry["tier"],
                    "verband": f"FVM / {entry['area']}",
                    "staffel": entry["staffel"], "rows": rows})
    if verbose:
        teams = sum(len(g["rows"]) for g in out)
        print(f"  fussball.de: {len(out)} Staffeln mit Daten, {teams} Mannschaften"
              f" ({empty} Staffeln noch ohne Tabelle)", file=sys.stderr)
    return out
