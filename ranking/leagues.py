"""Liga-Registry: Zuordnung OpenLigaDB-Kürzel -> Ligastufe, Staffel, Verband.

OpenLigaDB pflegt die Stufen 1-3 zuverlässig. Alles ab Stufe 4 wird von der
Community eingestellt, ist lückenhaft und über wechselnde Kürzel verteilt --
daher die explizite Kandidatenliste unten statt einer Heuristik.

Jeder Kandidat wird gegen die laufende Saison probiert; wer keine Spiele
liefert, fällt still heraus. Sobald jemand eine fehlende Staffel bei
OpenLigaDB einstellt, taucht sie beim nächsten Lauf von selbst auf.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


def current_season(today: dt.date | None = None) -> int:
    """Spielzeit 2026/27 heißt bei OpenLigaDB '2026'; Wechsel Anfang Juli."""
    today = today or dt.date.today()
    return today.year if today.month >= 7 else today.year - 1


@dataclass(frozen=True)
class LeagueRef:
    shortcut: str
    season: int
    tier: int
    name: str                 # Anzeigename der Staffel
    verband: str | None


# Stufe 1-3: durchgehend gepflegt.
CORE = [
    ("bl1", 1, "Bundesliga", None),
    ("bl2", 2, "2. Bundesliga", None),
    ("bl3", 3, "3. Liga", None),
]

# Stufe 4/5: Kandidaten. Mehrere Kürzel pro Staffel sind Absicht -- die
# Community benennt sie von Saison zu Saison unterschiedlich. Greift das erste
# Kürzel mit Daten, werden die weiteren derselben Staffel übersprungen.
LOWER = [
    ("rlno",         4, "Regionalliga Nordost", "NOFV"),
    ("rlno_n",       4, "Regionalliga Nordost", "NOFV"),
    ("rl-no",        4, "Regionalliga Nordost", "NOFV"),
    ("rln",          4, "Regionalliga Nord",    "NFV/HFV/SHFV/BFV"),
    ("rl-nord",      4, "Regionalliga Nord",    "NFV/HFV/SHFV/BFV"),
    ("rlw",          4, "Regionalliga West",    "WDFV"),
    ("RLW",          4, "Regionalliga West",    "WDFV"),
    ("rlsw",         4, "Regionalliga Südwest", "SWFV"),
    ("RLSW",         4, "Regionalliga Südwest", "SWFV"),
    ("regio-bayern", 4, "Regionalliga Bayern",  "BFV"),
    ("rlbay",        4, "Regionalliga Bayern",  "BFV"),
    ("RLB",          4, "Regionalliga Bayern",  "BFV"),
    ("nofvon",       5, "NOFV-Oberliga Nord",   "NOFV"),
    ("OLW",          5, "Oberliga Westfalen",   "FLVW"),
    ("OLN",          5, "Oberliga Niederrhein", "FVN"),
]

# Staffeln, die zur Vollständigkeit einer Ligastufe fehlen würden.
EXPECTED_TIER4 = [
    "Regionalliga Nord", "Regionalliga Nordost", "Regionalliga West",
    "Regionalliga Südwest", "Regionalliga Bayern",
]


def registry(season: int | None = None) -> list[LeagueRef]:
    season = season or current_season()
    return [LeagueRef(sc, season, tier, name, verband)
            for sc, tier, name, verband in CORE + LOWER]


TIER_LABEL = {
    1: "1. Liga", 2: "2. Liga", 3: "3. Liga",
    4: "4. Liga (Regionalliga)", 5: "5. Liga (Oberliga)",
    6: "6. Liga (Landesliga)", 7: "7. Liga (Bezirksliga)",
    8: "8. Liga (Kreisliga A)", 9: "9. Liga (Kreisliga B)",
    10: "10. Liga (Kreisliga C)", 11: "11. Liga (Kreisliga D)",
}
