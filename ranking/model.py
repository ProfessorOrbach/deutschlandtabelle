"""Datenmodell und Normalisierung der OpenLigaDB-Rohdaten."""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Match:
    date: dt.datetime
    league_name: str
    tier: int
    home: str                # kanonische Team-ID
    away: str
    home_goals: int
    away_goals: int


@dataclass
class Team:
    key: str
    name: str
    icon: str | None = None
    tier: int | None = None
    league_name: str | None = None
    verband: str | None = None


# --- Vereinsidentität -----------------------------------------------------

_RESERVE = re.compile(r"\b(ii|2|zwei|u\s?23|u23|amateure)\b\.?$", re.I)
_NOISE = re.compile(r"[^a-z0-9 ]+")
_PREFIX = re.compile(
    r"^(1\.?|2\.?|vf[lbr]|fs?v|sv|sc|fc|tsv|tsg|spvgg|sg|bsc|dsc|msv|ksc|vfb)\s+", re.I
)


def normalize_name(name: str) -> str:
    """Schlüssel für die Vereinsidentität.

    OpenLigaDB vergibt für dieselbe Mannschaft in community-gepflegten Ligen
    teils neue teamIds und leicht abweichende Schreibweisen. Deshalb wird über
    den normalisierten Namen zusammengeführt. Die Reserve-Kennung (II / U23)
    bleibt erhalten, damit "Borussia Dortmund II" nicht mit "Borussia Dortmund"
    verschmilzt.
    """
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower().replace("ae", "a").replace("oe", "o").replace("ue", "u")
    reserve = bool(_RESERVE.search(s))
    s = _RESERVE.sub("", s)
    s = _NOISE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _PREFIX.sub("", s).strip() or s
    return f"{s} ii" if reserve else s


def final_result(match: dict) -> tuple[int, int] | None:
    """Endergebnis aus dem OpenLigaDB-Match. None, wenn nicht auswertbar."""
    results = match.get("matchResults") or []
    for res in results:
        if (res.get("resultName") or "").lower().startswith("endergebnis"):
            return int(res["pointsTeam1"]), int(res["pointsTeam2"])
    for res in results:
        if res.get("resultTypeID") == 2:
            return int(res["pointsTeam1"]), int(res["pointsTeam2"])
    goals = match.get("goals") or []
    if goals and goals[-1].get("scoreTeam1") is not None:
        return int(goals[-1]["scoreTeam1"]), int(goals[-1]["scoreTeam2"])
    if results:
        res = min(results, key=lambda r: r.get("resultOrderID") or 0)
        return int(res["pointsTeam1"]), int(res["pointsTeam2"])
    return None
