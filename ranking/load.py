"""Lädt die Ligen der laufenden Saison und baut daraus Spiele und Mannschaften."""
from __future__ import annotations

import datetime as dt
import sys

from .api import OpenLigaDB
from .leagues import current_season, registry
from .model import Match, Team, final_result, normalize_name


def _parse_dt(row: dict) -> dt.datetime | None:
    """Anstoßzeit; einzelne Community-Datensätze lassen das Feld leer."""
    for field_name in ("matchDateTime", "matchDateTimeUTC", "lastUpdateDateTime"):
        value = row.get(field_name)
        if not value:
            continue
        try:
            return dt.datetime.fromisoformat(
                value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def load(client: OpenLigaDB, season: int | None = None, verbose: bool = True):
    season = season or current_season()
    matches: list[Match] = []
    teams: dict[str, Team] = {}
    leagues: list[dict] = []
    covered: set[str] = set()

    for ref in registry(season):
        if ref.name in covered:
            continue                      # Staffel schon über ein anderes Kürzel geladen
        raw = client.matches(ref.shortcut, season, is_current=True)
        kept = 0
        for row in raw:
            if not row.get("matchIsFinished"):
                continue
            score = final_result(row)
            if score is None:
                continue
            when = _parse_dt(row)
            if when is None:
                continue
            t1, t2 = row.get("team1") or {}, row.get("team2") or {}
            if not t1.get("teamName") or not t2.get("teamName"):
                continue
            h_key, a_key = normalize_name(t1["teamName"]), normalize_name(t2["teamName"])
            if h_key == a_key:
                continue
            for key, info in ((h_key, t1), (a_key, t2)):
                team = teams.get(key)
                if team is None:
                    team = teams[key] = Team(key=key, name=info["teamName"])
                team.name = info["teamName"]
                team.icon = info.get("teamIconUrl") or team.icon
                team.tier, team.league_name = ref.tier, ref.name
                team.verband = ref.verband
                team.spielklasse = ref.name
                team.staffel_id = f"{ref.shortcut}/{season}"
                team.quelle = "OpenLigaDB"
            matches.append(Match(
                date=when, league_name=ref.name, tier=ref.tier,
                home=h_key, away=a_key,
                home_goals=score[0], away_goals=score[1],
            ))
            kept += 1
        if kept:
            covered.add(ref.name)
            leagues.append({"shortcut": f"{ref.shortcut}/{season}",
                            "tier": ref.tier, "name": ref.name,
                            "verband": ref.verband, "area": None,
                            "spielklasse": ref.name, "matches": kept,
                            "source": "OpenLigaDB"})
        if verbose:
            print(f"  {'ok ' if kept else '-- '}{ref.shortcut:16s} "
                  f"{ref.name:24.24s} {kept:4d} Spiele", file=sys.stderr)

    matches.sort(key=lambda m: m.date)
    return matches, teams, leagues


def merge_standings(teams: dict[str, Team], groups: list[dict]):
    """Fertige Tabellen (fussball.de) in die Mannschaftsliste einhängen.

    Liefert die Bilanzen als {key: Stats} zurück. Bei Namenskollisionen mit
    einer bereits erfassten Mannschaft aus einer anderen Staffel wird der
    Schlüssel eindeutig gemacht, statt zwei Vereine stillschweigend zu
    verschmelzen -- in den Kreisligen gibt es Namen wie "Loope II" mehrfach.
    """
    from .rank import Stats

    external: dict[str, Stats] = {}
    for group in groups:
        for row in group["rows"]:
            key = normalize_name(row["name"])
            existing = teams.get(key)
            if existing is not None and existing.league_name != group["name"]:
                suffix = 2
                while f"{key}#{suffix}" in teams:
                    suffix += 1
                key = f"{key}#{suffix}"
            teams[key] = Team(
                key=key, name=row["name"], icon=None, tier=group["tier"],
                league_name=group["name"], verband=group["verband"],
                area=group["area"], spielklasse=group["spielklasse"],
                staffel_id=group["staffel"], quelle="fussball.de",
            )
            external[key] = Stats(
                played=row["played"], won=row["won"], drawn=row["drawn"],
                lost=row["lost"], goals_for=row["goals_for"],
                goals_against=row["goals_against"], points=row["points"],
            )
    return external
