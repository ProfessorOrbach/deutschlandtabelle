"""Erzeugt die statische HTML-Seite für GitHub Pages sowie JSON und CSV."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from . import landing

TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FCR Deutschland — die komplette Tabelle</title>
<meta name="description" content="Tagesaktuelle Rangfolge deutscher Fußballvereine über alle erfassten Ligastufen, aus den Spielen der laufenden Saison.">
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --line:#e3e6ea; --ink:#14171c; --muted:#666e79;
  --accent:#1a6b3c; --accent-soft:#e6f2ea; --up:#137a3d; --down:#b02a2a;
  --t1:#0b3d91; --t2:#1a6b3c; --t3:#8a6100; --t4:#7a3aa8; --t5:#a3442c;
  --t6:#0d6b74; --t7:#7a5a1f; --t8:#8a2f5e; --t9:#3f5aa6; --t10:#5c6b1f; --t11:#6b4a8a; --t12:#1f6b5c; --t13:#8a4a2f; --t14:#4a4a6b;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f1216; --panel:#161a20; --line:#262c34; --ink:#e8ebef; --muted:#98a2ae;
    --accent:#4ec27f; --accent-soft:#17301f; --up:#4ec27f; --down:#e8695f;
    --t1:#6ea8ff; --t2:#4ec27f; --t3:#e0b453; --t4:#c194ea; --t5:#f0937a;
    --t6:#5ec9d4; --t7:#d9b26a; --t8:#ef8ab8; --t9:#8fa8ee; --t10:#b3c96a; --t11:#bfa0e0; --t12:#66c9b4; --t13:#e0a184; --t14:#a0a4d4;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 18px 56px}
a.zurueck{display:inline-block;margin:0 0 10px;color:var(--accent);
  text-decoration:none;font-size:14px;font-weight:600}
a.zurueck:hover{text-decoration:underline}
header h1{margin:0 0 6px;font-size:clamp(22px,3.4vw,32px);letter-spacing:-.02em}
header p{margin:0;color:var(--muted)}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;min-width:118px}
.stat b{display:block;font-size:20px;letter-spacing:-.01em}
.stat span{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 12px}
input[type=search],select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  border-radius:8px;padding:9px 11px;font-size:14px;max-width:100%;min-width:0}
select{text-overflow:ellipsis}
input[type=search]{flex:1 1 240px;min-width:180px}
/* Bewusst KEIN overflow hier. Ein Scroll-Container würde den fixierten
   Spaltenkopf aushebeln: ein sticky <th> klebt am oberen Rand seines
   Scroll-Containers, nicht am Fenster. Damit die Tabelle trotzdem in schmale
   Fenster passt, fallen dort weiter unten Nebenspalten weg. */
.tablewrap{background:var(--panel);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{position:sticky;top:0;z-index:3;background:var(--panel);
  font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);font-weight:600;
  box-shadow:inset 0 -1px 0 var(--line)}
th:nth-child(3),td:nth-child(3),th:nth-child(4),td:nth-child(4){text-align:left}
/* Jede Ligastufe bekommt einen eigenen, sehr blassen Hintergrund. Der
   Farbton ist derselbe wie beim Stufen-Abzeichen, nur stark aufgehellt --
   dadurch liest man den Ligensprung, ohne dass die Tabelle bunt wirkt. */
tbody tr.t1 {background:color-mix(in srgb, var(--t1)  7%, var(--panel))}
tbody tr.t2 {background:color-mix(in srgb, var(--t2)  7%, var(--panel))}
tbody tr.t3 {background:color-mix(in srgb, var(--t3)  7%, var(--panel))}
tbody tr.t4 {background:color-mix(in srgb, var(--t4)  7%, var(--panel))}
tbody tr.t5 {background:color-mix(in srgb, var(--t5)  7%, var(--panel))}
tbody tr.t6 {background:color-mix(in srgb, var(--t6)  7%, var(--panel))}
tbody tr.t7 {background:color-mix(in srgb, var(--t7)  7%, var(--panel))}
tbody tr.t8 {background:color-mix(in srgb, var(--t8)  7%, var(--panel))}
tbody tr.t9 {background:color-mix(in srgb, var(--t9)  7%, var(--panel))}
tbody tr.t10{background:color-mix(in srgb, var(--t10) 7%, var(--panel))}
tbody tr.t11{background:color-mix(in srgb, var(--t11) 7%, var(--panel))}
tbody tr.t12{background:color-mix(in srgb, var(--t12) 7%, var(--panel))}
tbody tr.t13{background:color-mix(in srgb, var(--t13) 7%, var(--panel))}
tbody tr.t14{background:color-mix(in srgb, var(--t14) 7%, var(--panel))}
/* Erste Zeile einer Stufe: kräftige Kante in der Farbe der Stufe.
   Nur die Rahmenfarbe setzen -- über `color` liefe die Tönung sonst per
   Vererbung in den Zeilentext. */
tbody tr.step > td{border-top:2px solid var(--line)}
tbody tr.step.t1 >td{border-top-color:var(--t1)}
tbody tr.step.t2 >td{border-top-color:var(--t2)}
tbody tr.step.t3 >td{border-top-color:var(--t3)}
tbody tr.step.t4 >td{border-top-color:var(--t4)}
tbody tr.step.t5 >td{border-top-color:var(--t5)}
tbody tr.step.t6 >td{border-top-color:var(--t6)}
tbody tr.step.t7 >td{border-top-color:var(--t7)}
tbody tr.step.t8 >td{border-top-color:var(--t8)}
tbody tr.step.t9 >td{border-top-color:var(--t9)}
tbody tr.step.t10>td{border-top-color:var(--t10)}
tbody tr.step.t11>td{border-top-color:var(--t11)}
tbody tr.step.t12>td{border-top-color:var(--t12)}
tbody tr.step.t13>td{border-top-color:var(--t13)}
tbody tr.step.t14>td{border-top-color:var(--t14)}
tbody tr:hover{background:var(--accent-soft)}
td.rank{font-weight:700;width:52px}
td.delta{width:56px;font-size:13px}
.club{display:flex;align-items:center;gap:9px;min-width:0}
.club img{width:20px;height:20px;object-fit:contain;flex:0 0 20px}
.club span{overflow:hidden;text-overflow:ellipsis;max-width:250px}
.tier{display:inline-block;padding:2px 7px;border-radius:999px;font-size:11px;font-weight:600;
  border:1px solid currentColor}
.tier1{color:var(--t1)}.tier2{color:var(--t2)}.tier3{color:var(--t3)}
.tier4{color:var(--t4)}.tier5{color:var(--t5)}.tier6{color:var(--t6)}
.tier7{color:var(--t7)}.tier8{color:var(--t8)}.tier9{color:var(--t9)}
.tier10{color:var(--t10)}.tier11{color:var(--t11)}.tier12{color:var(--t12)}.tier13{color:var(--t13)}
.tier14{color:var(--t14)}
/* Staffelnamen wie "IGA 2027 Landesliga Staffel 3 · Westfalen" sprengen sonst
   die Tabellenbreite und erzwingen waagerechtes Scrollen der ganzen Seite.
   Gekappt mit Auslassungspunkten; der volle Name steht im title-Attribut. */
.league{color:var(--muted);font-size:13px;display:inline-block;max-width:205px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--muted)}
.empty{padding:28px;text-align:center;color:var(--muted)}
.tip{margin:0 0 10px;font-size:13px;color:var(--muted)}
.count{margin:0 0 8px;font-size:12px;color:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.legend span{font-size:11px;padding:3px 9px;border-radius:999px;
  border:1px solid currentColor;font-weight:600}
.foot a{color:var(--accent)}
.note{background:var(--panel);border:1px solid var(--line);
  border-left:3px solid var(--t3);border-radius:8px;padding:12px 14px;
  margin:16px 0;font-size:14px;color:var(--muted)}
.note summary{cursor:pointer;color:var(--ink);font-weight:600;list-style:none}
.note summary::-webkit-details-marker{display:none}
.note summary::before{content:"▸ ";color:var(--muted)}
.note[open] summary::before{content:"▾ "}
.note p{margin:8px 0 0}
.foot{display:block;margin-top:30px;color:var(--muted);font-size:13px;line-height:1.7}
.foot summary{cursor:pointer;font-weight:600;color:var(--ink);list-style:none}
.foot summary::-webkit-details-marker{display:none}
.foot summary::before{content:"▸ ";color:var(--muted)}
.foot[open] summary::before{content:"▾ "}
/* Schmale Fenster: Nebenspalten ausblenden, statt die Tabelle seitlich
   scrollen zu lassen. Der Scroll-Container würde den fixierten Kopf kosten. */
@media (max-width:1100px){
  th:nth-child(5),td:nth-child(5),      /* Pl. in der Staffel */
  th:nth-child(7),td:nth-child(7),      /* S */
  th:nth-child(8),td:nth-child(8),      /* U */
  th:nth-child(9),td:nth-child(9){display:none}   /* N */
  .club span{max-width:130px}
  .league{max-width:150px}
}
@media (max-width:860px){
  th:nth-child(2),td:nth-child(2),      /* Vorwochen-Differenz */
  th:nth-child(10),td:nth-child(10),    /* Tore */
  th:nth-child(11),td:nth-child(11),    /* Diff */
  th:nth-child(12),td:nth-child(12){display:none} /* Pkt -- Pkt/Sp bleibt,
                                          das ist das Sortierkriterium */
  th,td{padding:8px 6px;white-space:normal}
  /* Statt zu kappen hier umbrechen lassen: so schrumpft die Tabelle auf jede
     Breite, ohne dass die Seite seitlich scrollen muss. */
  .club span,.league{max-width:none;white-space:normal;overflow:visible;
    text-overflow:clip;display:inline;min-width:0}
  .club{align-items:flex-start}
  /* Feste Spaltenbreiten: die automatische Tabellenbreite hält sich hier nicht
     an den Container und schiebt die Verein-Spalte auf Maximalbreite. */
  table{table-layout:fixed}
  th:nth-child(1),td:nth-child(1){width:11%}
  th:nth-child(3),td:nth-child(3){width:41%}
  th:nth-child(4),td:nth-child(4){width:25%}
  th:nth-child(6),td:nth-child(6){width:9%}
  th:nth-child(13),td:nth-child(13){width:14%}
  /* Silbentrennung statt harter Umbruch mitten im Wort: die Seite ist
     lang="de", der Browser trennt "Mönchen-gladbach" statt "Mönchengladbac|h". */
  td:nth-child(3),td:nth-child(4){overflow-wrap:break-word;hyphens:auto}
  td.rank{width:11%}
  .league{font-size:11px}
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <a class="zurueck" href="index.html">← FCR Deutschland</a>
  <h1>Die komplette Tabelle</h1>
  <p>Alle erfassten deutschen Fußballmannschaften in einer Rangfolge · Saison __SEASON__ · Stand __GENERATED__</p>
</header>

<div class="stats">
  <div class="stat"><b>__N_TEAMS__</b><span>Mannschaften</span></div>
  <div class="stat"><b>__N_LEAGUES__</b><span>Staffeln</span></div>
  <div class="stat"><b>__N_MATCHES__</b><span>Spiele</span></div>
  <div class="stat"><b>__N_TIERS__</b><span>Ligastufen</span></div>
</div>

__NOTE__

<div class="controls">
  <input type="search" id="q" placeholder="Verein suchen …" autocomplete="off">
  <select id="verbandFilter"><option value="">Alle Verbände</option>__VERBAND_OPTIONS__</select>
  <select id="tierFilter"><option value="">Alle Ligastufen</option>__TIER_OPTIONS__</select>
  <select id="leagueFilter"><option value="">Alle Staffeln</option>__LEAGUE_OPTIONS__</select>
</div>

<p class="tip">Unterhalb der Regionalliga gibt es zwischen den Landesverbänden keine
sportliche Verbindung — für einen belastbaren Vergleich oben einen <b>Verband</b> wählen.</p>

<div class="legend" id="legend"></div>
<p class="count" id="zaehler"></p>

<div class="tablewrap">
  <table>
    <thead><tr>
      <th>#</th><th title="Veränderung gegenüber der Vorwoche">± Wo.</th>
      <th>Verein</th><th>Liga</th><th title="Platz in der eigenen Staffel">Pl.</th>
      <th>Sp</th><th>S</th><th>U</th><th>N</th><th>Tore</th><th>Diff</th><th>Pkt</th>
      <th title="Punkte pro Spiel — Sortierkriterium innerhalb der Ligastufe">Pkt/Sp</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div class="empty" id="empty" hidden>Keine Treffer.</div>
</div>

<details class="foot">
  <summary>Methodik, Quellen und Abdeckung</summary>
  <p><b>Wie sortiert wird.</b> Erstes Kriterium ist die Ligastufe — ein Regionalligist
  steht nie vor einem Drittligisten. Innerhalb einer Stufe entscheiden
  <b>Punkte pro Spiel</b>, dann Tordifferenz pro Spiel, dann Tore pro Spiel.
  Punkte <em>pro Spiel</em> deshalb, weil parallele Staffeln derselben Stufe
  unterschiedlich weit sind: die Regionalligen starten Wochen vor der Bundesliga.
  Die Spalte <b>± Wo.</b> zeigt die Veränderung des Rankingplatzes gegenüber dem Stand
  vor sieben Tagen, nachgerechnet aus denselben Spieldaten. Ein „–" heißt: vor einer
  Woche hatte diese Mannschaft noch kein Spiel absolviert.</p>
  <p>Grundlage sind ausschließlich die Ligaspiele der laufenden Saison __SEASON__.
  Daten: <a href="https://www.openligadb.de/">OpenLigaDB</a>. Wappen von Wikimedia Commons.
  Erzeugt am __GENERATED__.</p>
</details>
</div>

<script>
// Die Zeilen stecken als Arrays statt als Objekte in der Seite, Staffel- und
// Verbandsnamen nur einmal in einer Nachschlagetabelle. Bei über 5000
// Mannschaften spart das rund zwei Drittel der Dateigröße.
const DATA = __DATA__;
const RANKING = DATA.rows.map(a => ({
  rank: a[0], delta: a[1], name: a[2], icon: a[3], tier: a[4],
  league: DATA.leagues[a[5]], verband: DATA.verbaende[a[6]],
  leaguePos: a[7], played: a[8], won: a[9], drawn: a[10], lost: a[11],
  goalsFor: a[12], goalsAgainst: a[13], goalDiff: a[14], points: a[15], ppg: a[16],
}));
const rows = document.getElementById('rows');
const empty = document.getElementById('empty');
const q = document.getElementById('q');
const tierFilter = document.getElementById('tierFilter');
const leagueFilter = document.getElementById('leagueFilter');
const verbandFilter = document.getElementById('verbandFilter');
const zaehler = document.getElementById('zaehler');

const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function deltaCell(d){
  if (d === null || d === undefined) return '<span class="flat">–</span>';
  if (d === 0) return '<span class="flat">±0</span>';
  return d > 0 ? `<span class="up">▲ ${d}</span>` : `<span class="down">▼ ${-d}</span>`;
}

// Bei knapp 27.000 Mannschaften wären rund 350.000 DOM-Knoten nötig. Deshalb
// wird nur ein Stück gerendert und beim Scrollen nachgelegt; gefiltert und
// sortiert wird weiterhin über den vollen Datensatz.
const STUECK = 400;
let gefiltert = [];
let gezeigt = 0;
let letzteStufe = null;

function zeile(r, step){
  const icon = r.icon ? `<img src="${esc(r.icon)}" alt="" loading="lazy"
    onerror="this.style.visibility='hidden'">` : '<img alt="" style="visibility:hidden">';
  return `<tr class="t${r.tier}${step ? ' step' : ''}">
    <td class="rank">${r.rank}</td>
    <td class="delta">${deltaCell(r.delta)}</td>
    <td><div class="club">${icon}<span title="${esc(r.name)}">${esc(r.name)}</span></div></td>
    <td><span class="tier tier${r.tier}">${r.tier}</span>
        <span class="league" title="${esc(r.league)}">${esc(r.league)}</span></td>
    <td>${r.leaguePos ?? '–'}</td>
    <td>${r.played}</td><td>${r.won}</td><td>${r.drawn}</td><td>${r.lost}</td>
    <td>${r.goalsFor}:${r.goalsAgainst}</td>
    <td>${r.goalDiff > 0 ? '+' : ''}${r.goalDiff}</td>
    <td><b>${r.points}</b></td>
    <td>${r.ppg.toFixed(2)}</td>
  </tr>`;
}

function nachladen(){
  const teil = gefiltert.slice(gezeigt, gezeigt + STUECK);
  if (teil.length){
    const html = teil.map(r => {
      const step = r.tier !== letzteStufe;
      letzteStufe = r.tier;
      return zeile(r, step);
    });
    rows.insertAdjacentHTML('beforeend', html.join(''));
    gezeigt += teil.length;
  }
  zaehler.textContent = gezeigt < gefiltert.length
    ? `${gezeigt.toLocaleString('de-DE')} von ${gefiltert.length.toLocaleString('de-DE')} angezeigt — weiterscrollen lädt nach`
    : `${gefiltert.length.toLocaleString('de-DE')} Mannschaften`;
  // Füllt das Stück den Bildschirm noch nicht, gleich weiterlegen -- sonst
  // gäbe es nichts zu scrollen und das Nachladen käme nie in Gang.
  if (gezeigt < gefiltert.length &&
      document.body.scrollHeight <= window.innerHeight + 200) nachladen();
}

function render(){
  const term = q.value.trim().toLowerCase();
  const tier = tierFilter.value;
  const league = leagueFilter.value;
  const verband = verbandFilter.value;
  gefiltert = RANKING.filter(r =>
    (!tier || String(r.tier) === tier) &&
    (!league || r.league === league) &&
    (!verband || r.verband === verband) &&
    (!term || r.name.toLowerCase().includes(term)));
  gezeigt = 0;
  letzteStufe = null;
  rows.innerHTML = '';
  empty.hidden = gefiltert.length > 0;
  nachladen();
}

window.addEventListener('scroll', () => {
  if (gezeigt >= gefiltert.length) return;
  if (window.scrollY + window.innerHeight >= document.body.scrollHeight - 800) nachladen();
}, {passive: true});

document.getElementById('legend').innerHTML =
  [...new Set(RANKING.map(r => r.tier))].sort((a, b) => a - b)
    .map(t => `<span class="tier${t}">${t}. Stufe</span>`).join('');

const parameter = new URLSearchParams(location.search);
if (parameter.get('q')) q.value = parameter.get('q');
if (parameter.get('verband')) verbandFilter.value = parameter.get('verband');
if (parameter.get('stufe')) tierFilter.value = parameter.get('stufe');

[q, tierFilter, leagueFilter, verbandFilter].forEach(
  el => el.addEventListener('input', render));
render();
</script>
</body>
</html>
"""


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


def _write_vereine(out_dir: Path, ranking: list[dict]) -> None:
    """Eine Zeile je Mannschaft, mit vollständiger Einordnung in die Pyramide."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([name for name, _ in VEREINE_SPALTEN])
    for r in ranking:
        w.writerow(["" if r.get(key) is None else r.get(key)
                    for _, key in VEREINE_SPALTEN])
    (out_dir / "vereine.csv").write_text(buf.getvalue(), encoding="utf-8")


def _write_ligen(out_dir: Path, ranking: list[dict], meta: dict) -> None:
    """Eine Zeile je Staffel -- der Logikbaum ohne die Vereine.

    Über `staffel_id` lässt sich vereine.csv daran anfügen; zusammen ergeben
    beide Dateien die Kette Verband -> Ligastufe -> Spielklasse -> Gebiet ->
    Staffel -> Verein.
    """
    gruppen: dict[str, dict] = {}
    for r in ranking:
        sid = r.get("staffelId") or r["league"]
        g = gruppen.setdefault(sid, {
            "staffel_id": sid, "staffel": r["league"], "ligastufe": r["tier"],
            "spielklasse": r.get("spielklasse"), "verband": r.get("verband"),
            "gebiet": r.get("area"), "quelle": r.get("quelle"),
            "mannschaften": 0, "spiele_gesamt": 0, "tore_gesamt": 0,
            "punkte_gesamt": 0, "bester": None, "bester_pkt": None,
        })
        g["mannschaften"] += 1
        g["spiele_gesamt"] += r["played"]
        g["tore_gesamt"] += r["goalsFor"]
        g["punkte_gesamt"] += r["points"]
        if r.get("leaguePos") == 1:
            g["bester"], g["bester_pkt"] = r["name"], r["points"]

    spalten = ["staffel_id", "verband", "gebiet", "ligastufe", "spielklasse",
               "staffel", "mannschaften", "spiele_gesamt", "tore_gesamt",
               "punkte_gesamt", "tabellenfuehrer", "tabellenfuehrer_punkte",
               "quelle"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(spalten)
    for g in sorted(gruppen.values(),
                    key=lambda g: (g["ligastufe"], g["verband"] or "",
                                   g["gebiet"] or "", g["staffel"])):
        w.writerow([
            g["staffel_id"], g["verband"] or "", g["gebiet"] or "",
            g["ligastufe"], g["spielklasse"] or "", g["staffel"],
            g["mannschaften"], g["spiele_gesamt"] // 2, g["tore_gesamt"],
            g["punkte_gesamt"], g["bester"] or "",
            "" if g["bester_pkt"] is None else g["bester_pkt"], g["quelle"] or "",
        ])
    (out_dir / "ligen.csv").write_text(buf.getvalue(), encoding="utf-8")


def _compact(ranking: list[dict]) -> dict:
    """Zeilen als Arrays, Staffel- und Verbandsnamen als Nachschlagetabelle.

    Bei 5000+ Mannschaften wiederholen sich die Staffelnamen hundertfach und
    die Objektschlüssel bei jeder Zeile -- beides fliegt hier raus.
    """
    leagues: list[str] = []
    verbaende: list[str] = []
    index: dict[tuple[str, str], tuple[int, int]] = {}
    rows = []
    for r in ranking:
        lg, vb = r["league"] or "", r["verband"] or ""
        if (lg, vb) not in index:
            if lg not in leagues:
                leagues.append(lg)
            if vb not in verbaende:
                verbaende.append(vb)
            index[(lg, vb)] = (leagues.index(lg), verbaende.index(vb))
        li, vi = index[(lg, vb)]
        rows.append([
            r["rank"], r["delta"], r["name"], r["icon"], r["tier"], li, vi,
            r["leaguePos"], r["played"], r["won"], r["drawn"], r["lost"],
            r["goalsFor"], r["goalsAgainst"], r["goalDiff"], r["points"], r["ppg"],
        ])
    return {"leagues": leagues, "verbaende": verbaende, "rows": rows}


def _options(pairs):
    return "".join(f'<option value="{v}">{l}</option>' for v, l in pairs)


def write_site(out_dir: Path, ranking, meta) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    verbaende = sorted({r["verband"] for r in ranking if r.get("verband")})
    verband_opts = _options((v, v) for v in verbaende)
    tiers = sorted({r["tier"] for r in ranking})
    tier_opts = _options((str(t), f"{t}. Ligastufe") for t in tiers)
    leagues = sorted({(r["tier"], r["league"]) for r in ranking})
    league_opts = _options((name, name) for _, name in leagues)

    note = ""
    if meta.get("note"):
        note = ('<details class="note"><summary>' + meta["note_summary"]
                + "</summary><p>" + meta["note"] + "</p></details>")

    html = TEMPLATE
    for key, value in {
        "__GENERATED__": meta["generated"],
        "__N_TEAMS__": f'{len(ranking):,}'.replace(",", "."),
        "__N_LEAGUES__": str(meta["leagues"]),
        "__N_MATCHES__": f'{meta["matches"]:,}'.replace(",", "."),
        "__N_TIERS__": str(len(tiers)),
        "__SEASON__": meta["season_label"],
        "__TIER_OPTIONS__": tier_opts,
        "__VERBAND_OPTIONS__": verband_opts,
        "__LEAGUE_OPTIONS__": league_opts,
        "__NOTE__": note,
        "__DATA__": json.dumps(_compact(ranking), ensure_ascii=False,
                               separators=(",", ":")),
    }.items():
        html = html.replace(key, value)

    (out_dir / "tabelle.html").write_text(html, encoding="utf-8")
    (out_dir / "ranking.json").write_text(
        json.dumps({"meta": meta, "ranking": ranking}, ensure_ascii=False,
                   separators=(",", ":")),
        encoding="utf-8")

    _write_vereine(out_dir, ranking)
    _write_ligen(out_dir, ranking, meta)
    landing.write_landing(out_dir, ranking, meta)
    (out_dir / ".nojekyll").write_text("")
