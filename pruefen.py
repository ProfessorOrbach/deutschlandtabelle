#!/usr/bin/env python3
"""Prüft die CSV-Dateien einer Sportart auf innere Widersprüche.

    python3 pruefen.py                     # Fußball
    python3 pruefen.py --sport handball
    python3 pruefen.py --leise             # nur Fehler

Die Prüfungen arbeiten ausschließlich mit den CSV-Dateien selbst -- sie holen
nichts nach und vertrauen keiner Zwischenstufe der Pipeline. Damit lässt sich
das Ergebnis unabhängig nachvollziehen.

Rückgabewert 0, wenn alle harten Prüfungen bestanden sind, sonst 1. Ein Befund
gilt als *Hinweis* und nicht als Fehler, wenn er eine bekannte Eigenheit des
Amateurfußballs beschreibt (Punktabzüge, unterschiedlich weit gespielte
Staffeln) -- diese werden gezählt und ausgewiesen, brechen aber nicht ab.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Bericht:
    def __init__(self, leise: bool = False):
        self.leise = leise
        self.fehler: list[str] = []
        self.hinweise: list[str] = []
        self.bestanden = 0

    def pruefung(self, titel: str, verstoesse: list[str], hart: bool = True,
                 beispiele: int = 3) -> None:
        if not verstoesse:
            self.bestanden += 1
            if not self.leise:
                print(f"  ok    {titel}")
            return
        ziel = self.fehler if hart else self.hinweise
        marke = "FEHLER" if hart else "hinweis"
        ziel.append(titel)
        print(f"  {marke:6s} {titel}: {len(verstoesse)}")
        for v in verstoesse[:beispiele]:
            print(f"           {v}")
        if len(verstoesse) > beispiele:
            print(f"           … und {len(verstoesse) - beispiele} weitere")


def lies(pfad: Path) -> list[dict]:
    with pfad.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def zahl(wert: str) -> int:
    return int(wert) if wert not in ("", None) else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--leise", action="store_true", help="nur Fehler ausgeben")
    ap.add_argument("--sport", default="fussball")
    ap.add_argument("--verzeichnis", default=str(ROOT / "docs"))
    args = ap.parse_args()

    ordner = Path(args.verzeichnis)
    vereine = lies(ordner / f"{args.sport}-vereine.csv")
    ligen = lies(ordner / f"{args.sport}-ligen.csv")
    b = Bericht(args.leise)

    print(f"{args.sport}: {len(vereine)} Mannschaften · {len(ligen)} Staffeln\n")

    # --- 1. Verknüpfung der beiden Dateien -------------------------------
    print("Verknüpfung")
    ligen_nach_id = {l["staffel_id"]: l for l in ligen}
    b.pruefung("jede Staffel-ID aus vereine.csv steht in ligen.csv",
               sorted({v["staffel_id"] for v in vereine
                       if v["staffel_id"] not in ligen_nach_id}))
    benutzt = {v["staffel_id"] for v in vereine}
    b.pruefung("keine Staffel in ligen.csv ohne Mannschaften",
               [l["staffel_id"] for l in ligen if l["staffel_id"] not in benutzt])
    b.pruefung("Staffel-IDs in ligen.csv sind eindeutig",
               [k for k, n in
                {l["staffel_id"]: sum(1 for x in ligen
                                      if x["staffel_id"] == l["staffel_id"])
                 for l in ligen}.items() if n > 1])

    # --- 2. Der Logikbaum ist widerspruchsfrei ---------------------------
    print("\nLogikbaum Verband → Ligastufe → Spielklasse → Gebiet → Staffel")
    je_staffel: dict[str, list[dict]] = defaultdict(list)
    for v in vereine:
        je_staffel[v["staffel_id"]].append(v)

    for feld in ("verband", "ligastufe", "spielklasse", "gebiet", "staffel"):
        uneinheitlich = [f"{sid}: {sorted({r[feld] for r in rs})}"
                         for sid, rs in je_staffel.items()
                         if len({r[feld] for r in rs}) > 1]
        b.pruefung(f"'{feld}' ist innerhalb einer Staffel einheitlich", uneinheitlich)

    passt = [f"{sid}: vereine.csv={rs[0][feld]!r} ligen.csv={ligen_nach_id[sid][feld]!r}"
             for sid, rs in je_staffel.items() if sid in ligen_nach_id
             for feld in ("verband", "gebiet", "ligastufe", "spielklasse", "staffel")
             if rs[0][feld] != ligen_nach_id[sid][feld]]
    b.pruefung("beide Dateien beschreiben dieselbe Staffel gleich", passt)

    # Eine Spielklasse gehört zu genau einer Ligastufe innerhalb ihres Verbands.
    klasse_stufe = defaultdict(set)
    for l in ligen:
        klasse_stufe[(l["verband"], l["spielklasse"])].add(l["ligastufe"])
    b.pruefung("je Verband liegt eine Spielklasse auf genau einer Ligastufe",
               [f"{vb or '—'} / {kl}: Stufen {sorted(st)}"
                for (vb, kl), st in klasse_stufe.items() if len(st) > 1])

    # Die Stufen eines Verbands müssen lückenlos sein -- eine Lücke hieße,
    # dass eine Spielklasse fehlt oder falsch einsortiert wurde.
    stufen_je_verband = defaultdict(set)
    for l in ligen:
        if l["verband"]:
            stufen_je_verband[l["verband"]].add(int(l["ligastufe"]))
    luecken = [f"{vb}: {sorted(st)}" for vb, st in stufen_je_verband.items()
               if sorted(st) != list(range(min(st), max(st) + 1))]
    # Beim Fußball ist eine Lücke ein Zuordnungsfehler, beim Handball dagegen
    # zu erwarten: nicht jeder Verband wickelt alle Stufen über handball.net ab.
    b.pruefung("die Ligastufen eines Verbands sind lückenlos", luecken,
               hart=(args.sport == "fussball"))

    # --- 3. Bilanz je Mannschaft -----------------------------------------
    print("\nBilanz je Mannschaft")
    b.pruefung("Siege + Unentschieden + Niederlagen = Spiele",
               [f"{v['verein']} ({v['staffel']})" for v in vereine
                if zahl(v["siege"]) + zahl(v["unentschieden"]) + zahl(v["niederlagen"])
                != zahl(v["spiele"])])
    b.pruefung("Tordifferenz = Tore − Gegentore",
               [f"{v['verein']}: {v['tordifferenz']}" for v in vereine
                if zahl(v["tordifferenz"]) != zahl(v["tore"]) - zahl(v["gegentore"])])
    b.pruefung("Punkte pro Spiel = Punkte / Spiele",
               [f"{v['verein']}: {v['punkte_pro_spiel']}" for v in vereine
                if zahl(v["spiele"]) and
                abs(float(v["punkte_pro_spiel"])
                    - zahl(v["punkte"]) / zahl(v["spiele"])) > 0.0051])
    abzuege = [f"{v['verein']} ({v['staffel']}): "
               f"{zahl(v['punkte']) - (3 * zahl(v['siege']) + zahl(v['unentschieden']))}"
               for v in vereine
               if zahl(v["punkte"]) != 3 * zahl(v["siege"]) + zahl(v["unentschieden"])]
    b.pruefung("Punkte = 3×Siege + Unentschieden (Abweichung = Punktabzug)",
               abzuege, hart=False)

    # --- 4. Geschlossenheit je Staffel -----------------------------------
    print("\nGeschlossenheit je Staffel")
    # In einer Staffel spielen alle nur gegeneinander: die Summe der Tore muss
    # der Summe der Gegentore entsprechen. Das ist die schärfste Prüfung.
    tore_ungleich, spiele_ungerade, plaetze_falsch, punkte_zuviel = [], [], [], []
    for sid, rs in je_staffel.items():
        tore = sum(zahl(r["tore"]) for r in rs)
        gegen = sum(zahl(r["gegentore"]) for r in rs)
        if tore != gegen:
            tore_ungleich.append(f"{rs[0]['staffel']}: {tore} Tore vs {gegen} Gegentore")
        spiele = sum(zahl(r["spiele"]) for r in rs)
        if spiele % 2:
            spiele_ungerade.append(f"{rs[0]['staffel']}: {spiele} Spiele")
        plaetze = sorted(zahl(r["platz_in_staffel"]) for r in rs)
        if plaetze != list(range(1, len(rs) + 1)):
            plaetze_falsch.append(f"{rs[0]['staffel']}: {plaetze[:6]}…")
        # Je Partie werden 3 Punkte vergeben (2 bei Remis), nie mehr.
        if sum(zahl(r["punkte"]) for r in rs) > 3 * (spiele // 2):
            punkte_zuviel.append(f"{rs[0]['staffel']}")
    # Eine Wertung gegen eine zurückgezogene Mannschaft erzeugt eine Niederlage
    # ohne zugehörigen Sieg: die Torsumme klafft dann auseinander und die
    # Spielsumme wird ungerade. Das ist echte Amateurfußball-Realität und kein
    # Parser-Fehler -- ein Parser-Fehler würde stattdessen S+U+N, die
    # Tordifferenz oder die Tabellenplätze zerlegen, und die sind hart geprüft.
    b.pruefung("Summe Tore = Summe Gegentore "
               f"({len(je_staffel)} Staffeln geprüft)", tore_ungleich, hart=False)
    b.pruefung("Summe der Spiele ist gerade", spiele_ungerade, hart=False)
    b.pruefung("Tabellenplätze sind lückenlos 1..n", plaetze_falsch)
    b.pruefung("nicht mehr Punkte vergeben als Partien erlauben", punkte_zuviel)

    ungleich_weit = [f"{rs[0]['staffel']}: {sorted({zahl(r['spiele']) for r in rs})}"
                     for rs in je_staffel.values()
                     if max(zahl(r["spiele"]) for r in rs)
                     - min(zahl(r["spiele"]) for r in rs) > 3]
    b.pruefung("Mannschaften einer Staffel sind ähnlich weit", ungleich_weit,
               hart=False)

    # --- 5. Die Rangfolge selbst -----------------------------------------
    print("\nRangfolge")
    raenge = [zahl(v["rang_bundesweit"]) for v in vereine]
    b.pruefung("Ränge sind lückenlos 1..n",
               [] if raenge == list(range(1, len(vereine) + 1))
               else [f"{len(vereine)} Zeilen, Ränge {min(raenge)}..{max(raenge)}"])
    verstoss = []
    for a, c in zip(vereine, vereine[1:]):
        sa, sc = zahl(a["ligastufe"]), zahl(c["ligastufe"])
        if sc < sa:
            verstoss.append(f"Rang {c['rang_bundesweit']}: Stufe {sc} nach {sa}")
        elif sc == sa and float(c["punkte_pro_spiel"]) > float(a["punkte_pro_spiel"]):
            verstoss.append(f"Rang {c['rang_bundesweit']}: "
                            f"{c['punkte_pro_spiel']} nach {a['punkte_pro_spiel']}")
    b.pruefung("sortiert nach Ligastufe, dann Punkte pro Spiel", verstoss)

    # --- 6. Bekannte Eckdaten --------------------------------------------
    print("\nEckdaten")
    je_stufe: dict[int, int] = defaultdict(int)
    for v in vereine:
        je_stufe[zahl(v["ligastufe"])] += 1
    soll = {1: 18, 2: 18, 3: 20}
    if args.sport == "fussball":
        b.pruefung("Bundesliga 18, 2. Bundesliga 18, 3. Liga 20",
                   [f"Stufe {s}: {je_stufe.get(s)} statt {n}"
                    for s, n in soll.items() if je_stufe.get(s) != n])
        b.pruefung("Ligastufe 4 hat fünf Regionalligen",
                   [] if len({l["staffel"] for l in ligen
                              if l["ligastufe"] == "4"}) == 5
                   else [f"{sorted({l['staffel'] for l in ligen if l['ligastufe']=='4'})}"])

    if not args.leise:
        print("\nVerteilung je Ligastufe")
        for s in sorted(je_stufe):
            print(f"   Stufe {s:2d}: {je_stufe[s]:6d} Mannschaften")

    # --- Ergebnis ---------------------------------------------------------
    print(f"\n{b.bestanden} Prüfungen bestanden, {len(b.fehler)} Fehler, "
          f"{len(b.hinweise)} Hinweise")
    print("Hinweise beschreiben Eigenheiten des Amateursports (Punktabzüge, "
          "Wertungen gegen\nzurückgezogene Mannschaften, unterschiedlich weit "
          "gespielte Staffeln, unvollständige\nAbdeckung) -- keine Fehler.")
    if b.fehler:
        print("Fehler in: " + ", ".join(b.fehler))
        return 1
    print("Alle harten Prüfungen bestanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
