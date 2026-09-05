#!/usr/bin/env python3
"""Baut das Club-Ranking und schreibt die Seite nach docs/.

    python3 build.py --sport fussball     # Standard
    python3 build.py --sport handball
    python3 build.py --nur-huelle         # nur index.html aus vorhandenen Daten

Je Sportart entstehen:
    docs/data/<sport>.json      Rangfolge, Kennzahlen und Metadaten für die Seite
    docs/<sport>-vereine.csv    eine Zeile je Mannschaft
    docs/<sport>-ligen.csv      eine Zeile je Staffel
Dazu docs/index.html, das alle Sportarten unter #home/#fussball/… zeigt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

from ranking import (fussballde, handballnet, hbl, landing, load, rank,
                     render, site)
from ranking.api import OpenLigaDB
from ranking.leagues import EXPECTED_TIER4, current_season

ROOT = Path(__file__).resolve().parent

SPORTARTEN = {
    "fussball": {
        "name": "Fußball", "icon": "⚽", "torwort": "Tore",
        "hinweis": None,
    },
    "handball": {
        "name": "Handball", "icon": "🤾", "torwort": "Tore",
        "hinweis": None,
    },
    "basketball": {
        "name": "Basketball", "icon": "🏀", "torwort": "Körbe",
        "hinweis": "Die Datenquelle für den deutschen Basketball ist noch nicht "
                   "erschlossen. Sobald sie steht, erscheint hier dieselbe "
                   "Rangfolge wie bei Fußball und Handball.",
    },
}

VERGLEICH = ("Unterhalb der überregionalen Ligen gibt es zwischen den "
             "Landesverbänden keine sportliche Verbindung — für einen "
             "belastbaren Vergleich oben einen <b>Verband</b> wählen.")


# --- Fußball --------------------------------------------------------------
def baue_fussball(cache_dir: Path, season: int, ohne_fussballde: bool):
    client = OpenLigaDB(cache_dir)
    matches, teams, leagues = load.load(client, season)
    if not matches:
        return None

    external = {}
    if not ohne_fussballde:
        groups = fussballde.fetch(cache_dir, season)
        external = load.merge_standings(teams, groups)
        leagues += [{"shortcut": g["staffel"], "tier": g["tier"], "name": g["name"],
                     "verband": g["verband"], "matches": None,
                     "source": "fussball.de"} for g in groups]

    ranking = rank.build(matches, teams, external)

    found = {lg["name"] for lg in leagues}
    gaps = [n for n in EXPECTED_TIER4 if n not in found]
    verbaende = sorted({lg.get("verband") for lg in leagues
                        if lg.get("source") == "fussball.de" and lg.get("verband")})
    note = note_summary = None
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
                "ist sie nicht. Innerhalb eines Verbands ist sie belastbar, weil "
                "dort alle Staffeln über Auf- und Abstieg zusammenhängen.")
    if gaps:
        note = (note or "") + " Auf Ligastufe 4 fehlen zudem " + ", ".join(gaps) + "."

    return ranking, len(leagues), len(matches), note, note_summary


# --- Handball -------------------------------------------------------------
def baue_handball(cache_dir: Path, season: int):
    # Zwei Quellen: die Bundesligen laufen über das Sportradar-Widget der HBL,
    # alles darunter über handball.net.
    groups = hbl.fetch(cache_dir) + handballnet.fetch(cache_dir, season)
    if not groups:
        return None
    teams: dict = {}
    external = load.merge_standings(teams, groups)
    ranking = rank.build([], teams, external)
    verbaende = sorted({g["verband"] for g in groups if g["verband"]})
    note_summary = ("Ab Ligastufe 3 nur innerhalb eines Verbands sinnvoll "
                    "vergleichbar")
    note = ("Die 1. und 2. Bundesliga kommen von der HBL, alles darunter aus dem "
            f"Spielbetrieb auf handball.net mit {len(verbaende)} Verbänden und "
            "Kreisen. <b>Eine Lücke bleibt:</b> nicht jeder Landesverband wickelt "
            "seinen Spielbetrieb über handball.net ab, die Abdeckung unterhalb der "
            "überregionalen Ligen ist daher nicht flächendeckend. Und wie im Fußball "
            "gilt: zwischen Verbänden gibt es unterhalb der Regionalliga keine "
            "gemeinsame Auf- und Abstiegskette, ein Vergleich ist dort also nicht "
            "sportlich begründet.")
    return ranking, len(groups), 0, note, note_summary


# --- Ausgabe --------------------------------------------------------------
def schreibe_sport(out: Path, slug: str, ranking, leagues, matches,
                   note, note_summary, season) -> dict:
    meta = {
        "generated": dt.datetime.now().strftime("%d.%m.%Y, %H:%M Uhr"),
        "generatedIso": dt.datetime.now().isoformat(timespec="seconds"),
        "season": season,
        "season_label": f"{season}/{str(season + 1)[2:]}",
        "teams": len(ranking),
        "leagues": leagues,
        "matches": matches,
        "note": note,
        "note_summary": note_summary,
    }
    (out / "data").mkdir(parents=True, exist_ok=True)
    paket = render.compact(ranking)
    paket["meta"] = meta
    paket["kennzahlen"] = landing.kennzahlen(ranking)["karten"]
    (out / "data" / f"{slug}.json").write_text(
        json.dumps(paket, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    render.write_vereine(out, ranking, slug)
    render.write_ligen(out, ranking, slug)

    info = dict(SPORTARTEN[slug])
    info.update({
        "slug": slug, "ready": True, "teams": len(ranking), "leagues": leagues,
        "tiers": len({r["tier"] for r in ranking}),
        "season": meta["season_label"], "generated": meta["generated"],
        "vergleichHinweis": VERGLEICH,
        "fuss": (f'<p>Stand {meta["generated"]} · Saison {meta["season_label"]} · '
                 f'<a href="{slug}-vereine.csv">{slug}-vereine.csv</a> · '
                 f'<a href="{slug}-ligen.csv">{slug}-ligen.csv</a></p>'),
    })
    return info


def huelle(out: Path) -> None:
    """index.html aus den vorhandenen Sportdaten neu schreiben."""
    verzeichnis = out / "data"
    uebersicht = []
    for slug, vorgabe in SPORTARTEN.items():
        pfad = verzeichnis / f"{slug}.info.json"
        if pfad.exists():
            uebersicht.append(json.loads(pfad.read_text(encoding="utf-8")))
        else:
            uebersicht.append({**vorgabe, "slug": slug, "ready": False})
    site.write_shell(out, uebersicht)
    fertig = [s["slug"] for s in uebersicht if s.get("ready")]
    print(f"index.html geschrieben · Sportarten mit Daten: {', '.join(fertig) or '—'}",
          file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sport", choices=sorted(SPORTARTEN), default="fussball")
    ap.add_argument("--nur-huelle", action="store_true",
                    help="nur index.html neu bauen, nichts abrufen")
    ap.add_argument("--no-cache", action="store_true", help="Cache vorher leeren")
    ap.add_argument("--no-fussballde", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--season", type=int, default=None)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.nur_huelle:
        huelle(out)
        return 0

    cache_dir = ROOT / "data" / "cache"
    if args.no_cache and cache_dir.exists():
        shutil.rmtree(cache_dir)
    season = args.season or current_season()
    print(f"{SPORTARTEN[args.sport]['name']} · Saison {season}/{str(season+1)[2:]}",
          file=sys.stderr)

    if args.sport == "fussball":
        ergebnis = baue_fussball(cache_dir, season, args.no_fussballde)
    elif args.sport == "handball":
        ergebnis = baue_handball(cache_dir, season)
    else:
        print(f"Für {args.sport} gibt es noch keine Datenquelle.", file=sys.stderr)
        huelle(out)
        return 0

    if not ergebnis:
        print("Keine Daten erhalten — Abbruch.", file=sys.stderr)
        return 1

    ranking, leagues, matches, note, note_summary = ergebnis
    info = schreibe_sport(out, args.sport, ranking, leagues, matches,
                          note, note_summary, season)
    (out / "data" / f"{args.sport}.info.json").write_text(
        json.dumps(info, ensure_ascii=False), encoding="utf-8")
    huelle(out)

    print(f"\n{len(ranking)} Mannschaften · {leagues} Staffeln · "
          f"{info['tiers']} Ligastufen", file=sys.stderr)
    for r in ranking[:6]:
        print(f"  {r['rank']:5d}. {r['name']:<32.32s} {r['league']:<26.26s} "
              f"{r['points']:3d} Pkt / {r['played']:2d} Sp", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
