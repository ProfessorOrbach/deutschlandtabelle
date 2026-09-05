"""Tabelle und deutschlandweite Rangfolge aus den Spielen der laufenden Saison.

Rangfolge:
  1. Ligastufe -- ein Regionalligist steht nie vor einem Drittligisten.
  2. innerhalb der Stufe: Punkte pro Spiel, dann Tordifferenz pro Spiel,
     dann Tore pro Spiel, dann Name.

Punkte *pro Spiel* statt absoluter Punkte, weil parallele Staffeln derselben
Stufe unterschiedlich weit sind -- die Regionalligen starten Wochen vor der
Bundesliga und haben bereits mehr Spieltage absolviert.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .leagues import TIER_LABEL
from .model import Match, Team

WEEK = dt.timedelta(days=7)


@dataclass
class Stats:
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def ppg(self) -> float:
        return self.points / self.played if self.played else 0.0

    @property
    def gdpg(self) -> float:
        return self.goal_diff / self.played if self.played else 0.0

    @property
    def gfpg(self) -> float:
        return self.goals_for / self.played if self.played else 0.0


def standings(matches: list[Match], as_of: dt.datetime | None = None) -> dict[str, Stats]:
    """Bilanz aller Mannschaften, wahlweise nur bis zum Stichtag `as_of`."""
    table: dict[str, Stats] = {}
    for m in matches:
        if as_of is not None and m.date > as_of:
            continue
        home = table.setdefault(m.home, Stats())
        away = table.setdefault(m.away, Stats())
        home.played += 1
        away.played += 1
        home.goals_for += m.home_goals
        home.goals_against += m.away_goals
        away.goals_for += m.away_goals
        away.goals_against += m.home_goals
        if m.home_goals > m.away_goals:
            home.won += 1
            home.points += 3
            away.lost += 1
        elif m.home_goals < m.away_goals:
            away.won += 1
            away.points += 3
            home.lost += 1
        else:
            home.drawn += 1
            away.drawn += 1
            home.points += 1
            away.points += 1
    return table


EMPTY = Stats()


def _order(teams: dict[str, Team], table: dict[str, Stats]) -> list[str]:
    """Deutschlandweite Rangfolge: erst Ligastufe, dann Leistung in der Stufe.

    Es werden immer *alle* Mannschaften einsortiert, auch solche ohne Spiel.
    Nur so sind die Ranglisten von heute und von vor einer Woche vergleichbar --
    andernfalls verschöbe eine erst später startende Liga alle Plätze darunter.
    """
    keys = [k for k, t in teams.items() if t.tier]
    keys.sort(key=lambda k: (
        teams[k].tier,
        -table.get(k, EMPTY).ppg,
        -table.get(k, EMPTY).gdpg,
        -table.get(k, EMPTY).gfpg,
        teams[k].name,
    ))
    return keys


def _league_positions(teams: dict[str, Team], table: dict[str, Stats]) -> dict[str, int]:
    """Klassischer Tabellenplatz in der eigenen Staffel (absolute Punkte)."""
    groups: dict[str, list[str]] = {}
    for key, team in teams.items():
        if team.tier:
            groups.setdefault(team.league_name or "", []).append(key)
    positions: dict[str, int] = {}
    for members in groups.values():
        members.sort(key=lambda k: (
            -table.get(k, EMPTY).points, -table.get(k, EMPTY).goal_diff,
            -table.get(k, EMPTY).goals_for, teams[k].name))
        for i, key in enumerate(members, 1):
            positions[key] = i
    return positions


def build(matches: list[Match], teams: dict[str, Team],
          external: dict[str, Stats] | None = None,
          now: dt.datetime | None = None) -> list[dict]:
    """Aktuelles Ranking inklusive Platzveränderung gegenüber der Vorwoche.

    `external` sind fertige Tabellen aus Quellen, die keine Einzelspiele
    liefern (fussball.de). Sie fehlen dadurch zwangsläufig in der Vorwochen-
    Rechnung und bekommen kein Delta -- das ist gewollt, siehe unten.
    """
    now = now or dt.datetime.now()

    table = standings(matches)
    table.update(external or {})
    order = _order(teams, table)
    positions = _league_positions(teams, table)

    # Vorwoche aus derselben Datenbasis nachrechnen -- keine Momentaufnahmen nötig.
    prev_table = standings(matches, as_of=now - WEEK)
    prev_order = _order(teams, prev_table)
    prev_rank = {key: i for i, key in enumerate(prev_order, 1)}

    rows = []
    for rank, key in enumerate(order, 1):
        team = teams[key]
        stats = table.get(key, EMPTY)
        # Ohne Spiel in der Vorwoche war der damalige Platz beliebig (alle
        # punktgleich bei 0) -- dann lieber kein Vergleich als ein erfundener.
        had_history = prev_table.get(key, EMPTY).played > 0
        delta = prev_rank[key] - rank if had_history else None
        rows.append({
            "rank": rank,
            "delta": delta,
            "name": team.name,
            "icon": team.icon,
            "tier": team.tier,
            "tierLabel": TIER_LABEL.get(team.tier, "—"),
            "league": team.league_name,
            "verband": team.verband,
            "area": team.area,
            "spielklasse": team.spielklasse,
            "staffelId": team.staffel_id,
            "quelle": team.quelle,
            "leaguePos": positions.get(key),
            "played": stats.played,
            "won": stats.won,
            "drawn": stats.drawn,
            "lost": stats.lost,
            "goalsFor": stats.goals_for,
            "goalsAgainst": stats.goals_against,
            "goalDiff": stats.goal_diff,
            "points": stats.points,
            "ppg": round(stats.ppg, 2),
        })
    return rows
