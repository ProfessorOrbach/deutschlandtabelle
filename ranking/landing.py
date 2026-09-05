"""Einstiegsseite: Marke, Beschreibung und die spannenden Kennzahlen.

Die Tabelle selbst liegt auf `tabelle.html`. Hier steht, worum es geht, und
was aus den Zahlen herausfällt, wenn man sie einmal quer zur Rangfolge liest.

Alle Kennzahlen werden aus demselben Datensatz berechnet, den auch die Tabelle
zeigt -- es gibt keine zweite Wahrheit.
"""
from __future__ import annotations

import json
from pathlib import Path

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


TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FCR Deutschland — dein Fußball-Club-Ranking</title>
<meta name="description" content="Alle __N_TEAMS__ deutschen Fußballmannschaften von der Bundesliga bis zur Kreisklasse in einer einzigen Rangfolge. Wo steht dein Verein?">
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --line:#e3e6ea; --ink:#14171c; --muted:#666e79;
  --accent:#1a6b3c; --accent-soft:#e6f2ea; --up:#137a3d; --down:#b02a2a;
  --hero1:#0f3d2a; --hero2:#1a6b3c;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f1216; --panel:#161a20; --line:#262c34; --ink:#e8ebef; --muted:#98a2ae;
    --accent:#4ec27f; --accent-soft:#17301f; --up:#4ec27f; --down:#e8695f;
    --hero1:#0a2419; --hero2:#14472a;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 60px}

/* --- Kopfbereich mit Platzhalter für das Headerbild --------------------- */
.hero{position:relative;margin:18px 0 0;border-radius:16px;overflow:hidden;
  background:linear-gradient(135deg,var(--hero1),var(--hero2));
  min-height:300px;display:flex;align-items:flex-end}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hero .schleier{position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(0,0,0,.15) 0%,rgba(0,0,0,.72) 100%)}
/* Der Platzhalter sitzt oben, damit er dem Markennamen unten nicht ins
   Gehege kommt, und verschwindet, sobald ein Headerbild geladen wird. */
.platzhalter{position:absolute;inset:14px;border:2px dashed rgba(255,255,255,.4);
  border-radius:10px;display:flex;align-items:flex-start;justify-content:center;
  padding:14px;pointer-events:none}
.platzhalter em{font-style:normal;background:rgba(0,0,0,.4);
  color:rgba(255,255,255,.92);font-size:12px;line-height:1.5;text-align:center;
  padding:7px 12px;border-radius:8px}
.platzhalter code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:11.5px;background:rgba(255,255,255,.16);padding:1px 5px;
  border-radius:4px}
.hero .inhalt{position:relative;padding:28px 26px 26px;color:#fff;width:100%}
.marke{font-size:clamp(30px,6vw,54px);font-weight:800;letter-spacing:-.03em;
  margin:0;line-height:1.05;text-shadow:0 2px 14px rgba(0,0,0,.45)}
.marke span{color:#8ff0b6}
.claim{margin:8px 0 0;font-size:clamp(15px,2.4vw,20px);font-weight:500;
  text-shadow:0 1px 10px rgba(0,0,0,.5)}

/* --- Beschreibung und Einstieg ----------------------------------------- */
.intro{margin:26px 0 0;font-size:17px;max-width:70ch}
.intro p{margin:0 0 12px}
.suche{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 0}
.suche input{flex:1 1 260px;min-width:0;background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-radius:10px;padding:13px 15px;font-size:16px}
.knopf{display:inline-block;background:var(--accent);color:#fff;border:0;
  border-radius:10px;padding:13px 22px;font-size:16px;font-weight:600;
  cursor:pointer;text-decoration:none;white-space:nowrap}
.knopf.leise{background:transparent;color:var(--accent);
  border:1px solid var(--accent)}

.stats{display:grid;gap:10px;margin:26px 0 0;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:14px 16px}
.stat b{display:block;font-size:26px;letter-spacing:-.02em}
.stat span{color:var(--muted);font-size:12px;text-transform:uppercase;
  letter-spacing:.06em}

h2{margin:42px 0 4px;font-size:24px;letter-spacing:-.02em}
h2 + p{margin:0 0 18px;color:var(--muted);font-size:15px}

.karten{display:grid;gap:12px;
  grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.karte{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:18px 18px 16px;display:flex;flex-direction:column;gap:6px}
.karte .kopf{display:flex;align-items:center;gap:9px;font-size:13px;
  text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:700}
.karte .kopf i{font-style:normal;font-size:20px}
.karte .verein{font-size:21px;font-weight:700;letter-spacing:-.01em;line-height:1.25}
.karte .wert{font-size:15px;font-weight:600;color:var(--accent)}
.karte .liga{font-size:13px;color:var(--muted)}
.karte .erklaerung{font-size:13px;color:var(--muted);margin-top:4px;
  padding-top:10px;border-top:1px solid var(--line)}

.hinweis{background:var(--panel);border:1px solid var(--line);
  border-left:3px solid #8a6100;border-radius:10px;padding:14px 16px;
  margin:26px 0 0;font-size:14px;color:var(--muted)}
footer{margin:40px 0 0;padding-top:20px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px;line-height:1.7}
footer a{color:var(--accent)}
</style>
</head>
<body>
<div class="wrap">

<div class="hero">
  <!-- Headerbild: einfach eine Datei docs/header.jpg ablegen, dann
       verschwindet der Platzhalter von selbst. Empfohlen 2000x700 px. -->
  <img src="header.jpg" alt="" onload="document.getElementById('platzhalter').remove()"
       onerror="this.remove()">
  <div class="schleier"></div>
  <div class="platzhalter" id="platzhalter"><em>Platzhalter für das Headerbild —
    Datei <code>docs/header.jpg</code> ablegen, empfohlen 2000 × 700 px</em></div>
  <div class="inhalt">
    <h1 class="marke">FCR <span>Deutschland</span></h1>
    <p class="claim">Dein Fußball-Club-Ranking — wo steht dein Verein?</p>
  </div>
</div>

<div class="intro">
  <p><b>Jede Mannschaft des Landes in einer einzigen Rangfolge.</b> Vom FC Bayern
  auf Platz 1 bis zur letzten Kreisklasse: __N_TEAMS__ Herrenmannschaften aus
  __N_STAFFELN__ Staffeln, __N_STUFEN__ Ligastufen und allen __N_VERBAENDE__
  Landesverbänden — Tag für Tag neu berechnet aus den Ergebnissen der laufenden
  Saison __SEASON__.</p>
  <p>Sortiert wird zuerst nach Ligastufe, innerhalb einer Stufe nach Punkten pro
  Spiel. Dadurch stehen parallele Staffeln nicht blockweise hintereinander,
  sondern verzahnen sich zu einer echten Rangfolge.</p>
</div>

<form class="suche" action="tabelle.html" method="get">
  <input type="search" name="q" placeholder="Vereinsnamen eingeben …" autocomplete="off">
  <button class="knopf" type="submit">Verein finden</button>
  <a class="knopf leise" href="tabelle.html">Zur kompletten Tabelle</a>
</form>

<div class="stats">
  <div class="stat"><b>__N_TEAMS__</b><span>Mannschaften</span></div>
  <div class="stat"><b>__N_STAFFELN__</b><span>Staffeln</span></div>
  <div class="stat"><b>__N_STUFEN__</b><span>Ligastufen</span></div>
  <div class="stat"><b>__N_VERBAENDE__</b><span>Landesverbände</span></div>
</div>

<h2>Die Bestenlisten</h2>
<p>Quer zur Tabelle gelesen — ohne Rücksicht darauf, in welcher Liga jemand spielt.</p>
<div class="karten" id="karten"></div>

<div class="hinweis">__NOTE__</div>

<footer>
  <p>Stand __GENERATED__ · Saison __SEASON__ · Daten:
  <a href="https://www.openligadb.de/">OpenLigaDB</a> und
  <a href="https://www.fussball.de/">fussball.de</a> ·
  <a href="vereine.csv">vereine.csv</a> ·
  <a href="ligen.csv">ligen.csv</a> ·
  <a href="ranking.json">ranking.json</a></p>
  <p>Die Vorwochen-Werte („Aufsteiger" und „Absteiger der Woche") gibt es nur für
  Ligastufen, zu denen Einzelspiele mit Datum vorliegen — das sind die Bundesligen,
  die 3. Liga sowie die Regionalligen Nord und Nordost. Für alle übrigen Staffeln
  liefert die Quelle nur fertige Tabellen, aus denen sich ein Stand von vor sieben
  Tagen nicht nachrechnen lässt.</p>
</footer>
</div>

<script>
const KARTEN = __KARTEN__;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('karten').innerHTML = KARTEN.map(k => `
  <div class="karte">
    <div class="kopf"><i>${k.icon}</i>${esc(k.titel)}</div>
    <div class="verein">${esc(k.verein)}</div>
    <div class="wert">${esc(k.wert)}</div>
    <div class="liga">${esc(k.liga)} · Ligastufe ${k.stufe} · ${esc(k.verband)}
      · bundesweit Rang ${k.rang.toLocaleString('de-DE')}</div>
    <div class="erklaerung">${esc(k.erklaerung)}</div>
  </div>`).join('');
</script>
</body>
</html>
"""


def write_landing(out_dir: Path, ranking: list[dict], meta: dict) -> None:
    zahlen = kennzahlen(ranking)
    verbaende = {r["verband"] for r in ranking if r.get("verband")}
    stufen = {r["tier"] for r in ranking}

    def tausend(n: int) -> str:
        return f"{n:,}".replace(",", ".")

    html = TEMPLATE
    for schluessel, wert in {
        "__N_TEAMS__": tausend(len(ranking)),
        "__N_STAFFELN__": tausend(meta["leagues"]),
        "__N_STUFEN__": str(len(stufen)),
        "__N_VERBAENDE__": str(len(verbaende)),
        "__SEASON__": meta["season_label"],
        "__GENERATED__": meta["generated"],
        "__NOTE__": meta.get("note") or "",
        "__KARTEN__": json.dumps(zahlen["karten"], ensure_ascii=False),
    }.items():
        html = html.replace(schluessel, wert)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
