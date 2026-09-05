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
from dataclasses import dataclass
from pathlib import Path

ENABLED = True

BASE = "https://www.fussball.de"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

COMP_TYPE = "1"       # Meisterschaften (keine Pokale, Turniere, Freundschaftsspiele)


@dataclass(frozen=True)
class Verband:
    """Ein Landesverband mit seiner Ligapyramide.

    `klassen` sind die Spielklassen-IDs in Pyramidenreihenfolge, `start_tier`
    ist die Ligastufe der obersten davon. Die WAM-Datei liefert die Klassen
    bereits in dieser Reihenfolge -- in Schleswig-Holstein steht Landesliga
    (ID 78) vor Verbandsliga (ID 77), die Sortierung ist also inhaltlich und
    nicht numerisch. Deshalb reicht diese knappe Form für 144 Spielklassen.

    Die Pyramide ist nicht überall gleich tief: Bayern beginnt bei Stufe 4 mit
    der eigenen Regionalliga, Hessen reicht bis Stufe 14. Und wo die Oberliga
    einem Regionalverband gehört (NOFV, Rheinland-Pfalz/Saar,
    Baden-Württemberg), beginnt der Landesverband erst auf Stufe 6.

    Die Mannschaftsart "Herren" hat je Verband eine andere ID; sie wird zur
    Laufzeit aus der kinds-Datei gelesen.
    """
    mandant: str
    name: str
    start_tier: int
    klassen: tuple[str, ...]
    label: str | None = None           # Eintrag im Verbandsfilter; None = keiner
    only: frozenset[str] | None = None  # nur diese Wettbewerbe übernehmen

    @property
    def tiers(self) -> dict[str, int]:
        return {k: self.start_tier + i for i, k in enumerate(self.klassen)}


VERBAENDE = [
    # Überregional: die vier Regionalligen, die der Mandant "Deutschland"
    # führt (Nord und Nordost kommen mit Einzelspielen aus OpenLigaDB und
    # bleiben dort), sowie die drei Oberligen ohne eigenen Landesverband.
    Verband("89", "überregional", 4, ("4", "6"),
            only=frozenset({"Regionalliga West", "Regionalliga Südwest",
                            "Herren Oberliga Rheinland-Pfalz/Saar",
                            "NOFV-Oberliga Nord", "NOFV-Oberliga Süd"})),

    # --- Landesverbände ---------------------------------------------------
    # Die Spielklassen stehen in der WAM-Datei in Pyramidenreihenfolge -- in
    # Schleswig-Holstein etwa Landesliga vor Verbandsliga, also gerade nicht
    # nach ID sortiert. Deshalb genügen Startstufe und Reihenfolge.
    # Die Startstufe ist 5, wo der Verband seine Oberliga selbst betreibt,
    # und 6, wo sie einem Regionalverband gehört (NOFV, Rheinland-Pfalz/Saar,
    # Baden-Württemberg).
    # 4 Regionalliga Bayern · 5 Bayernliga · 6 Landesliga · 7 Bezirksliga · 8
    # Kreisliga · 9 Kreisklasse · 10 A Klasse · 11 B Klasse · 12 C Klasse
    Verband("31", "Bayern", 4, (
        "714", "520", "387", "390", "392", "393", "394", "395", "396"
    ), label="Bayern"),
    # 5 Verbandsliga · 6 Landesliga · 7 Bezirksliga · 8 1.Kreisliga (A) · 9
    # 2.Kreisliga (B)
    Verband("02", "Bremen", 5, (
        "46", "47", "49", "51", "52"
    ), label="Bremen"),
    # 5 Verbandsliga · 6 Landesliga · 7 Bezirksliga · 8 Kreisliga · 9
    # Kreisklasse
    Verband("03", "Hamburg", 5, (
        "65", "66", "67", "69", "74"
    ), label="Hamburg"),
    # 5 Hessenliga · 6 Verbandsliga · 7 Gruppenliga · 8 Kreisoberliga · 9
    # Kreisliga A · 10 Kreisliga B · 11 Kreisliga C · 12 Kreisliga D · 13
    # 1.Kreisklasse/Kreisklasse · 14 2.Kreisklasse
    Verband("34", "Hessen", 5, (
        "177", "594", "181", "627", "184", "185", "186", "187", "188", "411"
    ), label="Hessen"),
    # 5 Verbandsliga · 6 Landesliga · 7 Bezirksliga · 8 Kreisliga A · 9
    # Kreisliga B · 10 Kreisliga C · 11 Kreisliga D
    Verband("23", "Mittelrhein", 5, (
        "129", "130", "132", "135", "136", "137", "138"
    ), label="Mittelrhein"),
    # 5 Oberliga Niederrhein · 6 Landesliga · 7 Bezirksliga · 8 Kreisliga A ·
    # 9 Kreisliga B · 10 Kreisliga C · 11 Kreisliga D
    Verband("22", "Niederrhein", 5, (
        "584", "114", "116", "119", "120", "121", "122"
    ), label="Niederrhein"),
    # 5 Oberliga Niedersachsen · 6 Landesliga · 7 Bezirksliga · 8 Kreisliga ·
    # 9 1.Kreisklasse · 10 2.Kreisklasse · 11 3.Kreisklasse · 12 4.Kreisklasse
    # · 13 5.Kreisklasse
    Verband("01", "Niedersachsen", 5, (
        "597", "31", "32", "36", "38", "39", "40", "41", "42"
    ), label="Niedersachsen"),
    # 5 Oberliga Schleswig-Holstein · 6 Landesliga · 7 Verbandsliga · 8
    # Kreisliga · 9 Kreisklasse A · 10 Kreisklasse B · 11 Kreisklasse C
    Verband("04", "Schleswig-Holstein", 5, (
        "595", "78", "77", "84", "85", "86", "87"
    ), label="Schleswig-Holstein"),
    # 5 Oberliga Westfalen · 6 Verbandsliga · 7 Landesliga · 8 Bezirksliga · 9
    # Kreisliga A · 10 Kreisliga B · 11 Kreisliga C · 12 Kreisliga D
    Verband("21", "Westfalen", 5, (
        "361", "93", "94", "96", "99", "100", "101", "102"
    ), label="Westfalen"),
    # 5 Oberliga · 6 Verbandsliga · 7 Landesliga · 8 Bezirksliga · 9 Kreisliga
    # A; Kreisliga · 10 Kreisliga B · 11 Kreisliga C
    Verband("35", "Württemberg", 5, (
        "631", "190", "191", "195", "198", "199", "200"
    ), label="Württemberg"),
    # 6 Verbandsliga · 7 Landesliga · 8 Kreisliga · 9 Kreisklasse A · 10
    # Kreisklasse B · 11 Kreisklasse C
    Verband("32", "Baden", 6, (
        "145", "146", "150", "153", "154", "155"
    ), label="Baden"),
    # 6 Verbandsliga · 7 Landesliga · 8 Bezirksliga · 9 Kreisliga A · 10
    # Kreisliga B · 11 Kreisliga C
    Verband("66", "Berlin", 6, (
        "305", "306", "310", "313", "314", "315"
    ), label="Berlin"),
    # 6 Verbandsliga · 7 Landesliga · 8 Landesklasse · 9 Kreisoberliga · 10
    # Kreisliga · 11 1.Kreisklasse · 12 2.Kreisklasse
    Verband("61", "Brandenburg", 6, (
        "247", "248", "249", "735", "251", "252", "253"
    ), label="Brandenburg"),
    # 6 Verbandsliga · 7 Landesliga · 8 Landesklasse · 9 Kreisoberliga · 10
    # Kreisliga · 11 1.Kreisklasse
    Verband("62", "Mecklenburg-Vorpommern", 6, (
        "256", "257", "629", "262", "263", "264"
    ), label="Mecklenburg-Vorpommern"),
    # 6 Rheinlandliga · 7 Bezirksliga · 8 Kreisliga A · 9 Kreisliga B · 10
    # Kreisliga C
    Verband("41", "Rheinland", 6, (
        "207", "210", "213", "214", "215"
    ), label="Rheinland"),
    # 6 Saarland-Liga · 7 Verbandsliga · 8 Landesliga · 9 Bezirksliga · 10
    # Kreisliga A / Kreisliga · 11 Kreisliga B / 1.Kreisklasse
    Verband("43", "Saarland", 6, (
        "626", "232", "233", "235", "238", "239"
    ), label="Saarland"),
    # 6 Landesliga · 7 Landesklasse · 8 Kreisoberliga · 9 1.Kreisliga (A) · 10
    # 2.Kreisliga (B) · 11 3.Kreisliga (C) · 12 1.Kreisklasse · 13
    # 2.Kreisklasse
    Verband("63", "Sachsen", 6, (
        "268", "815", "702", "273", "274", "275", "277", "278"
    ), label="Sachsen"),
    # 6 Verbandsliga · 7 Landesliga · 8 Landesklasse · 9 Kreisoberliga · 10
    # Kreisliga · 11 1.Kreisklasse · 12 2.Kreisklasse · 13 3.Kreisklasse
    Verband("64", "Sachsen-Anhalt", 6, (
        "282", "283", "284", "286", "287", "288", "289", "290"
    ), label="Sachsen-Anhalt"),
    # 6 Verbandsliga · 7 Landesliga · 8 Bezirksliga · 9 1.Kreisliga (A) · 10
    # 2.Kreisliga (B) · 11 3.Kreisliga (C)
    Verband("33", "Südbaden", 6, (
        "158", "159", "162", "165", "166", "167"
    ), label="Südbaden"),
    # 6 Verbandsliga · 7 Landesliga · 8 Bezirksliga (Verband) · 9 A-Klasse ·
    # 10 B-Klasse · 11 C-Klasse
    Verband("42", "Südwest", 6, (
        "221", "222", "711", "713", "723", "724"
    ), label="Südwest"),
    # 6 Verbandsliga · 7 Landesklasse · 8 Kreisoberliga · 9 Kreisliga · 10
    # 1.Kreisklasse · 11 2.Kreisklasse
    Verband("65", "Thüringen", 6, (
        "292", "294", "299", "300", "301", "302"
    ), label="Thüringen"),
]


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
    def team_type(self, verband: Verband, season: int) -> tuple[str, dict] | None:
        """ID der Mannschaftsart "Herren" und der kinds-Baum des Verbands."""
        kinds = self._json(f"{BASE}/wam_kinds_{verband.mandant}"
                           f"_{season_code(season)}_{COMP_TYPE}.json")
        if not kinds:
            return None
        for key, label in (kinds.get("Mannschaftsart") or {}).items():
            if str(label).strip() == "Herren":
                return key.lstrip("_"), kinds
        return None

    def discover(self, verband: Verband, season: int) -> list[dict]:
        """Alle Herren-Meisterschaftsstaffeln eines Verbands der laufenden Saison."""
        found = self.team_type(verband, season)
        if not found:
            return []
        team_type, kinds = found
        sc = season_code(season)
        areas_by_league = (kinds.get("Gebiet") or {}).get(team_type, {})
        # Kategoriename der Spielklasse ("Kreisliga B", "Landesklasse", ...).
        # Er ist die Sprache des Verbands; der Staffelname darunter ist frei.
        klassen = {k.lstrip("_"): v for k, v
                   in ((kinds.get("Spielklasse") or {}).get(team_type, {})).items()}
        out: list[dict] = []
        for league_id, tier in verband.tiers.items():
            for area_key, area_name in (areas_by_league.get(league_id) or {}).items():
                area = area_key.lstrip("_")
                data = self._json(
                    f"{BASE}/wam_competitions_{verband.mandant}_{sc}_{COMP_TYPE}"
                    f"_{team_type}_{league_id}_{area}.json")
                if not data:
                    continue
                for by_area in data.values():
                    for comps in by_area.values():
                        for url, name in comps.items():
                            if verband.only and name not in verband.only:
                                continue
                            sid = re.search(r"/staffel/([0-9A-Z]+-[GC])", url)
                            if sid:
                                out.append({
                                    "tier": tier, "area": area_name,
                                    "verband": verband.label, "name": name,
                                    "spielklasse": klassen.get(league_id),
                                    "mandant": verband.mandant,
                                    "staffel": sid.group(1)})
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
    """Eindeutiger Anzeigename.

    "Kreisliga A" gibt es in jedem der rund 50 Kreise und "Landesliga" in jedem
    Verband -- allerdings auf unterschiedlichen Stufen. Deshalb kommt das Gebiet
    mit in den Namen, außer es steckt schon darin ("Oberliga Westfalen").
    """
    area = entry["area"]
    if not entry["verband"] or area == "Deutschland":
        return entry["name"]            # überregionale Staffeln stehen für sich
    kern = area.replace("Bezirk ", "").replace("Kreis ", "")
    if kern.lower() in entry["name"].lower():
        return entry["name"]
    return f"{entry['name']} · {area}"


def fetch(cache_dir: Path, season: int, verbose: bool = True) -> list[dict]:
    """Liefert je Staffel {name, tier, verband, rows}. Leere Staffeln entfallen."""
    if not ENABLED:
        return []
    client = FussballDe(cache_dir)

    entries: list[dict] = []
    for verband in VERBAENDE:
        gefunden = client.discover(verband, season)
        entries += gefunden
        if verbose:
            print(f"  fussball.de: {verband.name:12s} {len(gefunden):4d} Staffeln",
                  file=sys.stderr)

    out: list[dict] = []
    used: set[str] = set()
    empty = 0
    for entry in sorted(entries, key=lambda e: (e["tier"], e["verband"] or "",
                                                e["area"], e["name"])):
        rows = client.table(entry["staffel"])
        if not rows:
            empty += 1
            continue
        label = _label(entry)
        if label in used:                       # Notnagel gegen Namensgleichheit
            label = f"{label} ({entry['staffel'][:6]})"
        used.add(label)
        out.append({"name": label, "tier": entry["tier"],
                    "verband": entry["verband"], "area": entry["area"],
                    "spielklasse": entry["spielklasse"],
                    "mandant": entry["mandant"],
                    "staffel": entry["staffel"], "rows": rows})
    if verbose:
        teams = sum(len(g["rows"]) for g in out)
        print(f"  fussball.de: {len(out)} Staffeln mit Daten, {teams} Mannschaften"
              f" ({empty} noch ohne Tabelle)", file=sys.stderr)
    return out
