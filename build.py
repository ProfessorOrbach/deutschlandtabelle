#!/usr/bin/env python3
"""Baut das deutschlandweite Vereinsranking und schreibt die Seite nach docs/.

    python3 build.py            # normaler Lauf (nutzt den Cache)
    python3 build.py --no-cache # Cache verwerfen und alles neu laden
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from ranking import fussballde, load, rank, render
from ranking.api import OpenLigaDB
from ranking.leagues import EXPECTED_TIER4, current_season

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-cache", action="store_true", help="Cache vorher leeren")
    parser.add_argument("--out", default=str(ROOT / "docs"), help="Zielverzeichnis")
    parser.add_argument("--season", type=int, default=None, help="Saison überschreiben")
    parser.add_argument("--no-fussballde", action="store_true",
                        help="Staffeln unterhalb der Regionalliga weglassen "
                             "(Quelle fussball.de, siehe ranking/fussballde.py)")
    args = parser.parse_args()

    cache_dir = ROOT / "data" / "cache"
    if args.no_cache and cache_dir.exists():
        shutil.rmtree(cache_dir)

    season = args.season or current_season()
    print(f"Saison {season}/{str(season + 1)[2:]}", file=sys.stderr)

    client = OpenLigaDB(cache_dir)
    matches, teams, leagues = load.load(client, season)
    if not matches:
        print("Keine Spieldaten erhalten — Abbruch.", file=sys.stderr)
        return 1

    external = {}
    if not args.no_fussballde:
        groups = fussballde.fetch(cache_dir, season)
        external = load.merge_standings(teams, groups)
        leagues += [{"shortcut": g["staffel"], "tier": g["tier"], "name": g["name"],
                     "verband": g["verband"], "matches": None,
                     "source": "fussball.de"} for g in groups]

    ranking = rank.build(matches, teams, external)

    found = {lg["name"] for lg in leagues}
    gaps = [name for name in EXPECTED_TIER4 if name not in found]
    verbaende = sorted({lg["verband"] for lg in leagues
                        if lg.get("source") == "fussball.de" and lg.get("verband")})
    note = None
    note_summary = "Abdeckung"
    if external:
        note_summary = ("Ab Ligastufe 5 nur innerhalb eines Landesverbands "
                        "sinnvoll vergleichbar")
        note = (f"Erfasst sind alle {len(verbaende)} Landesverbände, von der "
                "Bundesliga bis hinunter zur Kreisklasse. <b>Aber:</b> unterhalb "
                "der Regionalliga gibt es zwischen den Verbänden keine sportliche "
                "Verbindung — ein Kreisligist aus Oberberg und einer aus Sachsen "
                "begegnen sich nie, weder direkt noch über eine Auf- und "
                "Abstiegskette. Die bundesweite Rangfolge ordnet dort nur nach "
                "Ligastufe und Punkten pro Spiel; ein sportliches Kräftemessen "
                "ist sie nicht. Wer vergleichen will, wählt oben einen Verband. "
                "Innerhalb eines Verbands ist die Rangfolge belastbar, weil dort "
                "alle Staffeln über Auf- und Abstieg zusammenhängen.")
    if gaps:
        note = ((note or "") + " Auf Ligastufe 4 fehlen zudem "
                + ", ".join(gaps) + ".")

    meta = {
        "generated": dt.datetime.now().strftime("%d.%m.%Y, %H:%M Uhr"),
        "generatedIso": dt.datetime.now().isoformat(timespec="seconds"),
        "season": season,
        "season_label": f"{season}/{str(season + 1)[2:]}",
        "teams": len(ranking),
        "leagues": len(leagues),
        "matches": len(matches),
        "note": note,
        "note_summary": note_summary,
        "coverage": leagues,
    }

    out = Path(args.out)
    render.write_site(out, ranking, meta)

    print(f"\n{len(matches)} Spiele · {len(ranking)} Mannschaften · "
          f"{len(leagues)} Staffeln", file=sys.stderr)
    print(f"geschrieben: {out / 'index.html'}\n", file=sys.stderr)
    for r in ranking[:8] + ranking[-6:]:
        d = "  –" if r["delta"] is None else f"{r['delta']:+3d}"
        print(f"  {r['rank']:3d}. {d}  {r['name']:<30.30s} {r['league']:<22.22s} "
              f"{r['points']:3d} Pkt / {r['played']:2d} Sp = {r['ppg']:.2f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
