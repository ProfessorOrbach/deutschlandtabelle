"""Die Bestenlisten: die Tabelle einmal quer gelesen.

Acht Kennzahlen ohne Rücksicht auf die Ligastufe -- der beste Verein des
Landes kann in der Kreisklasse spielen. Berechnet aus demselben Datensatz,
den auch die Tabelle zeigt; es gibt keine zweite Wahrheit.

Die Seitenvorlage steht in `site.py`.
"""
from __future__ import annotations


# Ein einziges gutes Spiel soll niemanden zum besten Verein Deutschlands
# machen. Die Schwelle sinkt automatisch, wenn zu Saisonbeginn noch kaum
# jemand so weit ist.
MIN_SPIELE_STUFEN = (5, 4, 3, 2, 1)
MIN_KANDIDATEN = 50


def _schwelle(ranking: list[dict]) -> int:
    for n in MIN_SPIELE_STUFEN:
        if sum(1 for r in ranking if r["played"] >= n) >= MIN_KANDIDATEN:
            return n
    return 1


def _pro_spiel(r: dict, feld: str) -> float:
    return r[feld] / r["played"] if r["played"] else 0.0


def kennzahlen(ranking: list[dict]) -> dict:
    """Die Bestenlisten quer zur Ligastufe."""
    n = _schwelle(ranking)
    feld = [r for r in ranking if r["played"] >= n]

    def bester(schluessel, quelle=None):
        kandidaten = quelle if quelle is not None else feld
        return max(kandidaten, key=schluessel) if kandidaten else None

    mit_delta = [r for r in ranking if r.get("delta") is not None]

    karten = [
        {
            "icon": "🏆", "titel": "Bester Verein Deutschlands",
            "erklaerung": f"Ohne Rücksicht auf die Ligastufe: die meisten Punkte "
                          f"pro Spiel, bei Gleichstand die bessere Tordifferenz "
                          f"pro Spiel. Mindestens {n} Spiele.",
            "team": bester(lambda r: (_pro_spiel(r, "points"),
                                      _pro_spiel(r, "goalDiff"))),
            "wert": lambda r: f"{_pro_spiel(r, 'points'):.2f} Punkte/Spiel",
        },
        {
            "icon": "🔥", "titel": "Der heißeste Club",
            "erklaerung": f"Die größte Tordifferenz pro Spiel — wer nicht nur "
                          f"gewinnt, sondern auseinandernimmt. Mindestens {n} Spiele.",
            "team": bester(lambda r: (_pro_spiel(r, "goalDiff"),
                                      _pro_spiel(r, "points"))),
            "wert": lambda r: f"{_pro_spiel(r, 'goalDiff'):+.2f} Tore/Spiel",
        },
        {
            "icon": "⚽", "titel": "Die Torfabrik",
            "erklaerung": f"Meiste eigene Tore pro Spiel. Mindestens {n} Spiele.",
            "team": bester(lambda r: _pro_spiel(r, "goalsFor")),
            "wert": lambda r: f"{_pro_spiel(r, 'goalsFor'):.2f} Tore/Spiel",
        },
        {
            "icon": "🧱", "titel": "Das Bollwerk",
            "erklaerung": f"Wenigste Gegentore pro Spiel. Mindestens {n} Spiele.",
            "team": bester(lambda r: (-_pro_spiel(r, "goalsAgainst"),
                                      _pro_spiel(r, "points"))),
            "wert": lambda r: f"{_pro_spiel(r, 'goalsAgainst'):.2f} Gegentore/Spiel",
        },
        {
            "icon": "📈", "titel": "Aufsteiger der Woche",
            "erklaerung": "Größter Sprung im bundesweiten Ranking gegenüber der "
                          "Vorwoche. Nur für Ligastufen mit Spieldaten — siehe unten.",
            "team": bester(lambda r: r["delta"], mit_delta),
            "wert": lambda r: f"{r['delta']:+d} Plätze auf Rang {r['rank']}",
        },
        {
            "icon": "📉", "titel": "Absteiger der Woche",
            "erklaerung": "Größter Verlust im bundesweiten Ranking gegenüber der "
                          "Vorwoche.",
            "team": bester(lambda r: -r["delta"], mit_delta),
            "wert": lambda r: f"{r['delta']:+d} Plätze auf Rang {r['rank']}",
        },
        {
            "icon": "🥶", "titel": "Das Schlusslicht",
            "erklaerung": f"Die schwächste Punkteausbeute des Landes. "
                          f"Mindestens {n} Spiele.",
            "team": bester(lambda r: (-_pro_spiel(r, "points"),
                                      -_pro_spiel(r, "goalDiff"))),
            "wert": lambda r: f"{_pro_spiel(r, 'points'):.2f} Punkte/Spiel",
        },
        {
            "icon": "💥", "titel": "Die dickste Klatsche",
            "erklaerung": f"Schlechteste Tordifferenz pro Spiel. "
                          f"Mindestens {n} Spiele.",
            "team": bester(lambda r: (-_pro_spiel(r, "goalDiff"),
                                      -_pro_spiel(r, "points"))),
            "wert": lambda r: f"{_pro_spiel(r, 'goalDiff'):+.2f} Tore/Spiel",
        },
    ]

    fertig = []
    for k in karten:
        r = k["team"]
        if not r:
            continue
        fertig.append({
            "icon": k["icon"], "titel": k["titel"], "erklaerung": k["erklaerung"],
            "verein": r["name"], "liga": r["league"], "stufe": r["tier"],
            "verband": r.get("verband") or "überregional",
            "rang": r["rank"], "wert": k["wert"](r),
        })
    return {"karten": fertig, "min_spiele": n}
