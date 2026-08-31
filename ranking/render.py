"""Erzeugt die statische HTML-Seite für GitHub Pages sowie JSON und CSV."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deutschlandweites Vereinsranking</title>
<meta name="description" content="Tagesaktuelle Rangfolge deutscher Fußballvereine über alle erfassten Ligastufen, aus den Spielen der laufenden Saison.">
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --line:#e3e6ea; --ink:#14171c; --muted:#666e79;
  --accent:#1a6b3c; --accent-soft:#e6f2ea; --up:#137a3d; --down:#b02a2a;
  --t1:#0b3d91; --t2:#1a6b3c; --t3:#8a6100; --t4:#7a3aa8; --t5:#a3442c;
  --t6:#0d6b74; --t7:#7a5a1f; --t8:#8a2f5e; --t9:#3f5aa6; --t10:#5c6b1f; --t11:#6b4a8a;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f1216; --panel:#161a20; --line:#262c34; --ink:#e8ebef; --muted:#98a2ae;
    --accent:#4ec27f; --accent-soft:#17301f; --up:#4ec27f; --down:#e8695f;
    --t1:#6ea8ff; --t2:#4ec27f; --t3:#e0b453; --t4:#c194ea; --t5:#f0937a;
    --t6:#5ec9d4; --t7:#d9b26a; --t8:#ef8ab8; --t9:#8fa8ee; --t10:#b3c96a; --t11:#bfa0e0;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 18px 64px}
header h1{margin:0 0 6px;font-size:clamp(22px,3.4vw,32px);letter-spacing:-.02em}
header p{margin:0;color:var(--muted)}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;min-width:118px}
.stat b{display:block;font-size:20px;letter-spacing:-.01em}
.stat span{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 12px;
  position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:5}
input[type=search],select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  border-radius:8px;padding:9px 11px;font-size:14px}
input[type=search]{flex:1 1 240px;min-width:180px}
.tablewrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;min-width:800px;font-variant-numeric:tabular-nums}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:var(--panel);font-size:11px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);font-weight:600}
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
tbody tr:hover{background:var(--accent-soft)}
td.rank{font-weight:700;width:52px}
td.delta{width:56px;font-size:13px}
.club{display:flex;align-items:center;gap:9px}
.club img{width:20px;height:20px;object-fit:contain;flex:0 0 20px}
.club span{overflow:hidden;text-overflow:ellipsis;max-width:250px}
.tier{display:inline-block;padding:2px 7px;border-radius:999px;font-size:11px;font-weight:600;
  border:1px solid currentColor}
.tier1{color:var(--t1)}.tier2{color:var(--t2)}.tier3{color:var(--t3)}
.tier4{color:var(--t4)}.tier5{color:var(--t5)}.tier6{color:var(--t6)}
.tier7{color:var(--t7)}.tier8{color:var(--t8)}.tier9{color:var(--t9)}
.tier10{color:var(--t10)}.tier11{color:var(--t11)}
.league{color:var(--muted);font-size:13px}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--muted)}
.empty{padding:28px;text-align:center;color:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.legend span{font-size:11px;padding:3px 9px;border-radius:999px;
  border:1px solid currentColor;font-weight:600}
footer{margin-top:34px;color:var(--muted);font-size:13px;line-height:1.7}
footer a{color:var(--accent)}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--t3);
  border-radius:8px;padding:12px 14px;margin:16px 0;font-size:14px;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Deutschlandweites Vereinsranking</h1>
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
  <select id="tierFilter"><option value="">Alle Ligastufen</option>__TIER_OPTIONS__</select>
  <select id="leagueFilter"><option value="">Alle Staffeln</option>__LEAGUE_OPTIONS__</select>
</div>

<div class="legend" id="legend"></div>

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

<footer>
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
</footer>
</div>

<script>
const DATA = __DATA__;
const rows = document.getElementById('rows');
const empty = document.getElementById('empty');
const q = document.getElementById('q');
const tierFilter = document.getElementById('tierFilter');
const leagueFilter = document.getElementById('leagueFilter');

const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function deltaCell(d){
  if (d === null || d === undefined) return '<span class="flat">–</span>';
  if (d === 0) return '<span class="flat">±0</span>';
  return d > 0 ? `<span class="up">▲ ${d}</span>` : `<span class="down">▼ ${-d}</span>`;
}

function render(){
  const term = q.value.trim().toLowerCase();
  const tier = tierFilter.value;
  const league = leagueFilter.value;
  let n = 0;
  let lastTier = null;
  const html = [];
  for (const r of DATA.ranking){
    if (tier && String(r.tier) !== tier) continue;
    if (league && r.league !== league) continue;
    if (term && !r.name.toLowerCase().includes(term)) continue;
    n++;
    const step = r.tier !== lastTier;
    lastTier = r.tier;
    const icon = r.icon ? `<img src="${esc(r.icon)}" alt="" loading="lazy"
      onerror="this.style.visibility='hidden'">` : '<img alt="" style="visibility:hidden">';
    html.push(`<tr class="t${r.tier}${step ? ' step' : ''}">
      <td class="rank">${r.rank}</td>
      <td class="delta">${deltaCell(r.delta)}</td>
      <td><div class="club">${icon}<span>${esc(r.name)}</span></div></td>
      <td><span class="tier tier${r.tier}">${r.tier}</span>
          <span class="league">${esc(r.league)}</span></td>
      <td>${r.leaguePos ?? '–'}</td>
      <td>${r.played}</td><td>${r.won}</td><td>${r.drawn}</td><td>${r.lost}</td>
      <td>${r.goalsFor}:${r.goalsAgainst}</td>
      <td>${r.goalDiff > 0 ? '+' : ''}${r.goalDiff}</td>
      <td><b>${r.points}</b></td>
      <td>${r.ppg.toFixed(2)}</td>
    </tr>`);
  }
  rows.innerHTML = html.join('');
  empty.hidden = n > 0;
}

document.getElementById('legend').innerHTML =
  [...new Set(DATA.ranking.map(r => r.tier))].sort((a, b) => a - b)
    .map(t => `<span class="tier${t}">${t}. Stufe</span>`).join('');

[q, tierFilter, leagueFilter].forEach(el => el.addEventListener('input', render));
render();
</script>
</body>
</html>
"""


def _options(pairs):
    return "".join(f'<option value="{v}">{l}</option>' for v, l in pairs)


def write_site(out_dir: Path, ranking, meta) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    tiers = sorted({r["tier"] for r in ranking})
    tier_opts = _options((str(t), f"{t}. Ligastufe") for t in tiers)
    leagues = sorted({(r["tier"], r["league"]) for r in ranking})
    league_opts = _options((name, name) for _, name in leagues)

    note = f'<div class="note">{meta["note"]}</div>' if meta.get("note") else ""

    html = TEMPLATE
    for key, value in {
        "__GENERATED__": meta["generated"],
        "__N_TEAMS__": f'{len(ranking):,}'.replace(",", "."),
        "__N_LEAGUES__": str(meta["leagues"]),
        "__N_MATCHES__": f'{meta["matches"]:,}'.replace(",", "."),
        "__N_TIERS__": str(len(tiers)),
        "__SEASON__": meta["season_label"],
        "__TIER_OPTIONS__": tier_opts,
        "__LEAGUE_OPTIONS__": league_opts,
        "__NOTE__": note,
        "__DATA__": json.dumps({"ranking": ranking}, ensure_ascii=False),
    }.items():
        html = html.replace(key, value)

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / "ranking.json").write_text(
        json.dumps({"meta": meta, "ranking": ranking}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    buf = io.StringIO()
    cols = ["rank", "delta", "name", "tier", "league", "leaguePos", "played", "won",
            "drawn", "lost", "goalsFor", "goalsAgainst", "goalDiff", "points", "ppg"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(ranking)
    (out_dir / "ranking.csv").write_text(buf.getvalue(), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("")
