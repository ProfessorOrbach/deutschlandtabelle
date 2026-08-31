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
        groups = fussballde.fetch(cache_dir)
        external = load.merge_standings(teams, groups)
        leagues += [{"shortcut": g["staffel"], "tier": g["tier"], "name": g["name"],
                     "matches": None, "source": "fussball.de"} for g in groups]

    ranking = rank.build(matches, teams, external)

    found = {lg["name"] for lg in leagues}
    gaps = [name for name in EXPECTED_TIER4 if name not in found]
    parts = []
    if gaps:
        parts.append("Auf Ligastufe 4 fehlen " + ", ".join(gaps)
                     + " — für diese Staffeln stellt OpenLigaDB keine Daten bereit.")
    if external:
        parts.append("Die Ligastufen 5 bis 11 sind <b>nicht bundesweit</b> erfasst, "
                     "sondern ausschließlich für den Kreis Berg (Oberberg): "
                     "von der Mittelrheinliga bis zur Kreisliga D. Ein Kreisligist "
                     "steht hier also stellvertretend für tausende nicht erfasste "
                     "Vereine derselben Stufe.")
    note = ("<b>Abdeckung.</b> " + " ".join(parts)) if parts else None

    meta = {
        "generated": dt.datetime.now().strftime("%d.%m.%Y, %H:%M Uhr"),
        "generatedIso": dt.datetime.now().isoformat(timespec="seconds"),
        "season": season,
        "season_label": f"{season}/{str(season + 1)[2:]}",
        "teams": len(ranking),
        "leagues": len(leagues),
        "matches": len(matches),
        "note": note,
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
