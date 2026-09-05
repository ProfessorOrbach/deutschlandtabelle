"""Ausgabe: die CSV-Dateien und die kompakte Fassung für die Seite.

Die Seitenvorlagen stehen in `site.py`; hier geht es nur um die Daten.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

# Spaltenname -> Feld im Ranking-Datensatz. Die Reihenfolge ist die Reihenfolge
# in der Datei: erst die Einordnung (wer, wo, welche Stufe), dann die Bilanz.
VEREINE_SPALTEN = [
    ("rang_bundesweit", "rank"),
    ("verein", "name"),
    ("verband", "verband"),
    ("gebiet", "area"),
    ("ligastufe", "tier"),
    ("spielklasse", "spielklasse"),
    ("staffel", "league"),
    ("staffel_id", "staffelId"),
    ("platz_in_staffel", "leaguePos"),
    ("spiele", "played"),
    ("siege", "won"),
    ("unentschieden", "drawn"),
    ("niederlagen", "lost"),
    ("tore", "goalsFor"),
    ("gegentore", "goalsAgainst"),
    ("tordifferenz", "goalDiff"),
    ("punkte", "points"),
    ("punkte_pro_spiel", "ppg"),
    ("rangaenderung_vorwoche", "delta"),
    ("quelle", "quelle"),
]

LIGEN_SPALTEN = ["staffel_id", "verband", "gebiet", "ligastufe", "spielklasse",
                 "staffel", "mannschaften", "spiele_gesamt", "tore_gesamt",
                 "punkte_gesamt", "tabellenfuehrer", "tabellenfuehrer_punkte",
                 "quelle"]


def write_vereine(out_dir: Path, ranking: list[dict], slug: str) -> None:
    """Eine Zeile je Mannschaft, mit vollständiger Einordnung in die Pyramide."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([name for name, _ in VEREINE_SPALTEN])
    for r in ranking:
        w.writerow(["" if r.get(key) is None else r.get(key)
                    for _, key in VEREINE_SPALTEN])
    (out_dir / f"{slug}-vereine.csv").write_text(buf.getvalue(), encoding="utf-8")


def write_ligen(out_dir: Path, ranking: list[dict], slug: str) -> None:
    """Eine Zeile je Staffel -- der Logikbaum ohne die Vereine.

    Über `staffel_id` lässt sich die Vereinsdatei daran anfügen; zusammen
    ergeben beide die Kette Verband -> Ligastufe -> Spielklasse -> Gebiet ->
    Staffel -> Verein.
    """
    gruppen: dict[str, dict] = {}
    for r in ranking:
        sid = r.get("staffelId") or r["league"]
        g = gruppen.setdefault(sid, {
            "staffel_id": sid, "staffel": r["league"], "ligastufe": r["tier"],
            "spielklasse": r.get("spielklasse"), "verband": r.get("verband"),
            "gebiet": r.get("area"), "quelle": r.get("quelle"),
            "mannschaften": 0, "spiele": 0, "tore": 0, "punkte": 0,
            "bester": None, "bester_pkt": None,
        })
        g["mannschaften"] += 1
        g["spiele"] += r["played"]
        g["tore"] += r["goalsFor"]
        g["punkte"] += r["points"]
        if r.get("leaguePos") == 1:
            g["bester"], g["bester_pkt"] = r["name"], r["points"]

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(LIGEN_SPALTEN)
    for g in sorted(gruppen.values(),
                    key=lambda g: (g["ligastufe"], g["verband"] or "",
                                   g["gebiet"] or "", g["staffel"])):
        w.writerow([
            g["staffel_id"], g["verband"] or "", g["gebiet"] or "", g["ligastufe"],
            g["spielklasse"] or "", g["staffel"], g["mannschaften"],
            g["spiele"] // 2, g["tore"], g["punkte"], g["bester"] or "",
            "" if g["bester_pkt"] is None else g["bester_pkt"], g["quelle"] or "",
        ])
    (out_dir / f"{slug}-ligen.csv").write_text(buf.getvalue(), encoding="utf-8")


def compact(ranking: list[dict]) -> dict:
    """Zeilen als Arrays, Staffel- und Verbandsnamen als Nachschlagetabelle.

    Bei zehntausenden Mannschaften wiederholen sich die Staffelnamen hundertfach
    und die Objektschlüssel bei jeder Zeile -- beides fliegt hier raus und drückt
    die Datei auf etwa ein Viertel.
    """
    leagues: list[str] = []
    verbaende: list[str] = []
    li: dict[str, int] = {}
    vi: dict[str, int] = {}
    rows = []
    for r in ranking:
        lg, vb = r["league"] or "", r["verband"] or ""
        if lg not in li:
            li[lg] = len(leagues)
            leagues.append(lg)
        if vb not in vi:
            vi[vb] = len(verbaende)
            verbaende.append(vb)
        rows.append([
            r["rank"], r["delta"], r["name"], r["icon"], r["tier"],
            li[lg], vi[vb], r["leaguePos"], r["played"], r["won"], r["drawn"],
            r["lost"], r["goalsFor"], r["goalsAgainst"], r["goalDiff"],
            r["points"], r["ppg"],
        ])
    return {"leagues": leagues, "verbaende": verbaende, "rows": rows}
