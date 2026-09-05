"""Das Seitengerüst: eine Seite, vier Ansichten über die Adresszeile.

    #home        Marke, Beschreibung, Überblick über die Sportarten
    #fussball    Bestenlisten und komplette Tabelle
    #handball    dito
    #basketball  dito

Warum eine einzige Seite: so lauten die Adressen wie gewünscht
`.../#fussball`. Die Daten je Sportart liegen aber nicht in dieser Datei,
sondern in `data/<sport>.json` und werden erst beim Wechsel geladen -- die
Fußballtabelle allein wiegt gut zwei Megabyte, alle drei eingebettet wären
unbenutzbar. Dadurch startet die Seite in Millisekunden und lädt nur, was
wirklich angesehen wird.
"""
from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FCR Deutschland — dein Club-Ranking</title>
<meta name="description" content="Fußball, Handball und Basketball: alle deutschen Vereine von der Bundesliga bis zur Kreisklasse in einer Rangfolge. Wo steht dein Verein?">
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --line:#e3e6ea; --ink:#14171c; --muted:#666e79;
  --accent:#1a6b3c; --accent-soft:#e6f2ea; --up:#137a3d; --down:#b02a2a;
  --hero1:#0f3d2a; --hero2:#1a6b3c;
  --t1:#0b3d91; --t2:#1a6b3c; --t3:#8a6100; --t4:#7a3aa8; --t5:#a3442c;
  --t6:#0d6b74; --t7:#7a5a1f; --t8:#8a2f5e; --t9:#3f5aa6; --t10:#5c6b1f;
  --t11:#6b4a8a; --t12:#1f6b5c; --t13:#8a4a2f; --t14:#4a4a6b;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f1216; --panel:#161a20; --line:#262c34; --ink:#e8ebef; --muted:#98a2ae;
    --accent:#4ec27f; --accent-soft:#17301f; --up:#4ec27f; --down:#e8695f;
    --hero1:#0a2419; --hero2:#14472a;
    --t1:#6ea8ff; --t2:#4ec27f; --t3:#e0b453; --t4:#c194ea; --t5:#f0937a;
    --t6:#5ec9d4; --t7:#d9b26a; --t8:#ef8ab8; --t9:#8fa8ee; --t10:#b3c96a;
    --t11:#bfa0e0; --t12:#66c9b4; --t13:#e0a184; --t14:#a0a4d4;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 60px}
[hidden]{display:none!important}

/* --- Kopfleiste mit den Sportarten ------------------------------------- */
.topbar{position:sticky;top:0;z-index:20;background:var(--bg);
  border-bottom:1px solid var(--line)}
.topbar .inner{max-width:1080px;margin:0 auto;padding:10px 18px;
  display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.brand{font-weight:800;letter-spacing:-.02em;font-size:19px;color:var(--ink);
  text-decoration:none;white-space:nowrap}
.brand span{color:var(--accent)}
.topbar nav{display:flex;gap:4px;flex-wrap:wrap}
.topbar nav a{color:var(--muted);text-decoration:none;font-size:14px;
  font-weight:600;padding:7px 12px;border-radius:8px}
.topbar nav a[aria-current="page"]{background:var(--accent-soft);color:var(--accent)}
.topbar nav a.leer{opacity:.5}

/* --- Startseite --------------------------------------------------------- */
.hero{position:relative;margin:18px 0 0;border-radius:16px;overflow:hidden;
  background:linear-gradient(135deg,var(--hero1),var(--hero2));
  min-height:300px;display:flex;align-items:flex-end}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hero .schleier{position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(0,0,0,.15) 0%,rgba(0,0,0,.72) 100%)}
.platzhalter{position:absolute;inset:14px;border:2px dashed rgba(255,255,255,.4);
  border-radius:10px;display:flex;align-items:flex-start;justify-content:center;
  padding:14px;pointer-events:none}
.platzhalter em{font-style:normal;background:rgba(0,0,0,.4);
  color:rgba(255,255,255,.92);font-size:12px;line-height:1.5;text-align:center;
  padding:7px 12px;border-radius:8px}
.platzhalter code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:11.5px;background:rgba(255,255,255,.16);padding:1px 5px;border-radius:4px}
.hero .inhalt{position:relative;padding:28px 26px 26px;color:#fff;width:100%}
.marke{font-size:clamp(30px,6vw,54px);font-weight:800;letter-spacing:-.03em;
  margin:0;line-height:1.05;text-shadow:0 2px 14px rgba(0,0,0,.45)}
.marke span{color:#8ff0b6}
.claim{margin:8px 0 0;font-size:clamp(15px,2.4vw,20px);font-weight:500;
  text-shadow:0 1px 10px rgba(0,0,0,.5)}
.intro{margin:26px 0 0;font-size:17px;max-width:70ch}
.intro p{margin:0 0 12px}
.suche{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0 0}
.suche input{flex:1 1 260px;min-width:0;background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-radius:10px;padding:13px 15px;font-size:16px}
.suche select{flex:0 0 auto}
.knopf{display:inline-block;background:var(--accent);color:#fff;border:0;
  border-radius:10px;padding:13px 22px;font-size:16px;font-weight:600;
  cursor:pointer;text-decoration:none;white-space:nowrap}

.sportkarten{display:grid;gap:12px;margin:26px 0 0;
  grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.sportkarte{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:18px;text-decoration:none;color:var(--ink);display:block}
.sportkarte:hover{border-color:var(--accent)}
.sportkarte .ic{font-size:30px;line-height:1}
.sportkarte h3{margin:8px 0 2px;font-size:20px;letter-spacing:-.01em}
.sportkarte .zahl{font-size:26px;font-weight:800;letter-spacing:-.02em;
  color:var(--accent);margin:6px 0 0}
.sportkarte .klein{color:var(--muted);font-size:13px}
.sportkarte.leer{opacity:.62;border-style:dashed;cursor:default}

h2{margin:42px 0 4px;font-size:24px;letter-spacing:-.02em}
h2 + p.unter{margin:0 0 18px;color:var(--muted);font-size:15px}

.karten{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
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

.note{background:var(--panel);border:1px solid var(--line);
  border-left:3px solid #8a6100;border-radius:8px;padding:12px 14px;
  margin:16px 0;font-size:14px;color:var(--muted)}
.note summary{cursor:pointer;color:var(--ink);font-weight:600;list-style:none}
.note summary::-webkit-details-marker{display:none}
.note summary::before{content:"▸ ";color:var(--muted)}
.note[open] summary::before{content:"▾ "}
.note p{margin:8px 0 0}

/* --- Tabelle ------------------------------------------------------------ */
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 10px}
input[type=search],select{background:var(--panel);color:var(--ink);
  border:1px solid var(--line);border-radius:8px;padding:9px 11px;font-size:14px;
  max-width:100%;min-width:0}
select{text-overflow:ellipsis}
input[type=search]{flex:1 1 240px}
.tip{margin:0 0 10px;font-size:13px;color:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.legend span{font-size:11px;padding:3px 9px;border-radius:999px;
  border:1px solid currentColor;font-weight:600}
.count{margin:0 0 8px;font-size:12px;color:var(--muted)}
/* Bewusst KEIN overflow: ein Scroll-Container würde den fixierten
   Spaltenkopf aushebeln. Schmale Fenster blenden stattdessen Spalten aus. */
.tablewrap{background:var(--panel);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line);
  white-space:nowrap}
th{position:sticky;top:47px;z-index:3;background:var(--panel);font-size:11px;
  text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;
  box-shadow:inset 0 -1px 0 var(--line)}
th:nth-child(3),td:nth-child(3),th:nth-child(4),td:nth-child(4){text-align:left}
td.rank{font-weight:700;width:52px}
td.delta{width:56px;font-size:13px}
.club{display:flex;align-items:center;gap:9px;min-width:0}
.club img{width:20px;height:20px;object-fit:contain;flex:0 0 20px}
.club span{overflow:hidden;text-overflow:ellipsis;max-width:250px}
.tier{display:inline-block;padding:2px 7px;border-radius:999px;font-size:11px;
  font-weight:600;border:1px solid currentColor}
.league{color:var(--muted);font-size:13px;display:inline-block;max-width:205px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--muted)}
.empty{padding:28px;text-align:center;color:var(--muted)}
.laden{padding:40px;text-align:center;color:var(--muted)}
__TIER_CSS__
tbody tr:hover{background:var(--accent-soft)}
@media (max-width:1100px){
  th:nth-child(5),td:nth-child(5),th:nth-child(7),td:nth-child(7),
  th:nth-child(8),td:nth-child(8),th:nth-child(9),td:nth-child(9){display:none}
  .club span{max-width:130px}
  .league{max-width:150px}
}
@media (max-width:860px){
  th:nth-child(2),td:nth-child(2),th:nth-child(10),td:nth-child(10),
  th:nth-child(11),td:nth-child(11),th:nth-child(12),td:nth-child(12){display:none}
  th,td{padding:8px 6px;white-space:normal}
  .club span,.league{max-width:none;white-space:normal;overflow:visible;
    text-overflow:clip;display:inline;min-width:0}
  .club{align-items:flex-start}
  table{table-layout:fixed}
  th:nth-child(1),td:nth-child(1){width:11%}
  th:nth-child(3),td:nth-child(3){width:41%}
  th:nth-child(4),td:nth-child(4){width:25%}
  th:nth-child(6),td:nth-child(6){width:9%}
  th:nth-child(13),td:nth-child(13){width:14%}
  td:nth-child(3),td:nth-child(4){overflow-wrap:break-word;hyphens:auto}
  td.rank{width:11%}
  .league{font-size:11px}
}
footer{margin:40px 0 0;padding-top:20px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px;line-height:1.7}
footer a{color:var(--accent)}
</style>
</head>
<body>

<div class="topbar"><div class="inner">
  <a class="brand" href="#home">FCR <span>Deutschland</span></a>
  <nav id="nav"></nav>
</div></div>

<div class="wrap">

<!-- ============================ Startseite ============================ -->
<section id="view-home">
  <div class="hero">
    <!-- Headerbild: eine Datei docs/header.jpg ablegen, dann verschwindet
         der Platzhalter von selbst. Empfohlen 2000x700 px. -->
    <img src="header.jpg" alt=""
         onload="document.getElementById('platzhalter').remove()"
         onerror="this.remove()">
    <div class="schleier"></div>
    <div class="platzhalter" id="platzhalter"><em>Platzhalter für das Headerbild —
      Datei <code>docs/header.jpg</code> ablegen, empfohlen 2000 × 700 px</em></div>
    <div class="inhalt">
      <h1 class="marke">FCR <span>Deutschland</span></h1>
      <p class="claim">Dein Club-Ranking — wo steht dein Verein?</p>
    </div>
  </div>

  <div class="intro">
    <p><b>Jeder Verein des Landes in einer einzigen Rangfolge.</b> Nicht nur die
    Bundesliga, sondern die komplette Pyramide bis hinunter zur Kreisklasse —
    und das für mehrere Sportarten. Tag für Tag neu berechnet aus den
    Ergebnissen der laufenden Saison.</p>
    <p>Sortiert wird zuerst nach Ligastufe, innerhalb einer Stufe nach Punkten
    pro Spiel. Dadurch stehen parallele Staffeln nicht blockweise
    hintereinander, sondern verzahnen sich zu einer echten Rangfolge.</p>
  </div>

  <form class="suche" id="homeSuche">
    <input type="search" id="homeQuery" placeholder="Vereinsnamen eingeben …"
           autocomplete="off">
    <select id="homeSport"></select>
    <button class="knopf" type="submit">Verein finden</button>
  </form>

  <h2>Die Sportarten</h2>
  <p class="unter">Jede mit eigener Rangfolge, eigenen Bestenlisten und eigener Datenbasis.</p>
  <div class="sportkarten" id="sportkarten"></div>

  <footer>
    <p>Ein Projekt aus offen zugänglichen Ergebnisdaten. Die Datenquellen und die
    jeweilige Abdeckung stehen auf der Seite der Sportart.</p>
  </footer>
</section>

<!-- ========================= Ansicht Sportart ========================= -->
<section id="view-sport" hidden>
  <h2 id="sportTitel"></h2>
  <p class="unter" id="sportUnter"></p>
  <div id="sportInhalt"><div class="laden">Daten werden geladen …</div></div>
</section>

<template id="tpl-sport">
  <div class="sportkarten" id="statKacheln"></div>
  <div id="noteSlot"></div>

  <h2>Die Bestenlisten</h2>
  <p class="unter">Quer zur Tabelle gelesen — ohne Rücksicht darauf, in welcher Liga jemand spielt.</p>
  <div class="karten" id="karten"></div>

  <h2>Die komplette Tabelle</h2>
  <p class="unter" id="tabellenUnter"></p>
  <div class="controls">
    <input type="search" id="q" placeholder="Verein suchen …" autocomplete="off">
    <select id="verbandFilter"></select>
    <select id="tierFilter"></select>
    <select id="leagueFilter"></select>
  </div>
  <p class="tip" id="vergleichHinweis"></p>
  <div class="legend" id="legend"></div>
  <p class="count" id="zaehler"></p>
  <div class="tablewrap">
    <table>
      <thead><tr>
        <th>#</th><th title="Veränderung gegenüber der Vorwoche">± Wo.</th>
        <th>Verein</th><th>Liga</th><th title="Platz in der eigenen Staffel">Pl.</th>
        <th>Sp</th><th>S</th><th>U</th><th>N</th><th id="thTore">Tore</th>
        <th>Diff</th><th>Pkt</th>
        <th title="Punkte pro Spiel — Sortierkriterium innerhalb der Ligastufe">Pkt/Sp</th>
      </tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div class="empty" id="empty" hidden>Keine Treffer.</div>
  </div>
  <footer id="sportFuss"></footer>
</template>

</div>

<script>
const SPORTS = __SPORTS__;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tausend = n => Number(n).toLocaleString('de-DE');
const daten = {};                      // slug -> geladener Datensatz

// --- Kopfleiste und Startseite ----------------------------------------
document.getElementById('nav').innerHTML =
  '<a href="#home">Start</a>' + SPORTS.map(s =>
    `<a href="#${s.slug}" class="${s.ready ? '' : 'leer'}">${s.icon} ${esc(s.name)}</a>`
  ).join('');

document.getElementById('sportkarten').innerHTML = SPORTS.map(s => s.ready
  ? `<a class="sportkarte" href="#${s.slug}">
       <div class="ic">${s.icon}</div><h3>${esc(s.name)}</h3>
       <div class="zahl">${tausend(s.teams)}</div>
       <div class="klein">Mannschaften · ${tausend(s.leagues)} Staffeln ·
         ${s.tiers} Ligastufen</div></a>`
  : `<div class="sportkarte leer">
       <div class="ic">${s.icon}</div><h3>${esc(s.name)}</h3>
       <div class="klein" style="margin-top:8px">${esc(s.hinweis || 'in Arbeit')}</div></div>`
).join('');

document.getElementById('homeSport').innerHTML = SPORTS.filter(s => s.ready)
  .map(s => `<option value="${s.slug}">${s.icon} ${esc(s.name)}</option>`).join('');
document.getElementById('homeSuche').addEventListener('submit', e => {
  e.preventDefault();
  const slug = document.getElementById('homeSport').value;
  const q = document.getElementById('homeQuery').value.trim();
  location.hash = `#${slug}` + (q ? `?q=${encodeURIComponent(q)}` : '');
});

// --- Router -------------------------------------------------------------
function aktuelleRoute(){
  const roh = (location.hash || '#home').slice(1);
  const [slug, query] = roh.split('?');
  return {slug: slug || 'home', params: new URLSearchParams(query || '')};
}

async function route(){
  const {slug, params} = aktuelleRoute();
  document.querySelectorAll('#nav a').forEach(a =>
    a.toggleAttribute('aria-current', a.getAttribute('href') === '#' + slug));
  const sport = SPORTS.find(s => s.slug === slug);
  const home = document.getElementById('view-home');
  const view = document.getElementById('view-sport');
  if (!sport){ home.hidden = false; view.hidden = true; window.scrollTo(0,0); return; }
  home.hidden = true; view.hidden = false;
  document.getElementById('sportTitel').textContent = `${sport.icon} ${sport.name}`;
  document.getElementById('sportUnter').textContent = sport.ready
    ? `Saison ${sport.season} · Stand ${sport.generated}` : '';
  if (!sport.ready){
    document.getElementById('sportInhalt').innerHTML =
      `<div class="note"><p>${esc(sport.hinweis || 'Diese Sportart ist noch in Arbeit.')}</p></div>`;
    window.scrollTo(0,0); return;
  }
  document.getElementById('sportInhalt').innerHTML =
    '<div class="laden">Daten werden geladen …</div>';
  window.scrollTo(0,0);
  try {
    if (!daten[slug]) daten[slug] = await (await fetch(`data/${slug}.json`)).json();
  } catch (err) {
    document.getElementById('sportInhalt').innerHTML =
      '<div class="note"><p>Die Daten konnten nicht geladen werden.</p></div>';
    return;
  }
  zeigeSport(sport, daten[slug], params);
}
window.addEventListener('hashchange', route);

// --- Eine Sportart darstellen ------------------------------------------
function zeigeSport(sport, d, params){
  const ziel = document.getElementById('sportInhalt');
  ziel.innerHTML = '';
  ziel.appendChild(document.getElementById('tpl-sport').content.cloneNode(true));

  const RANKING = d.rows.map(a => ({
    rank: a[0], delta: a[1], name: a[2], icon: a[3], tier: a[4],
    league: d.leagues[a[5]], verband: d.verbaende[a[6]],
    leaguePos: a[7], played: a[8], won: a[9], drawn: a[10], lost: a[11],
    goalsFor: a[12], goalsAgainst: a[13], goalDiff: a[14], points: a[15], ppg: a[16],
  }));

  const $ = id => ziel.querySelector('#' + id);
  $('thTore').textContent = sport.torwort || 'Tore';
  $('tabellenUnter').textContent =
    `${tausend(RANKING.length)} Mannschaften, sortiert nach Ligastufe und Punkten pro Spiel.`;
  $('vergleichHinweis').innerHTML = sport.vergleichHinweis || '';

  $('statKacheln').innerHTML = [
    ['Mannschaften', tausend(RANKING.length)],
    ['Staffeln', tausend(d.meta.leagues)],
    ['Ligastufen', new Set(RANKING.map(r => r.tier)).size],
    ['Verbände', new Set(RANKING.map(r => r.verband).filter(Boolean)).size],
  ].map(([k, v]) => `<div class="sportkarte"><div class="zahl">${v}</div>
      <div class="klein">${k}</div></div>`).join('');

  if (d.meta.note) $('noteSlot').innerHTML =
    `<details class="note"><summary>${esc(d.meta.note_summary || 'Abdeckung')}</summary>
     <p>${d.meta.note}</p></details>`;

  $('karten').innerHTML = (d.kennzahlen || []).map(k => `
    <div class="karte">
      <div class="kopf"><i>${k.icon}</i>${esc(k.titel)}</div>
      <div class="verein">${esc(k.verein)}</div>
      <div class="wert">${esc(k.wert)}</div>
      <div class="liga">${esc(k.liga)} · Ligastufe ${k.stufe} · ${esc(k.verband)}
        · Rang ${tausend(k.rang)}</div>
      <div class="erklaerung">${esc(k.erklaerung)}</div>
    </div>`).join('');

  $('sportFuss').innerHTML = sport.fuss || '';

  // --- Filter befüllen --------------------------------------------------
  const q = $('q'), tierFilter = $('tierFilter'), leagueFilter = $('leagueFilter'),
        verbandFilter = $('verbandFilter'), rows = $('rows'), empty = $('empty'),
        zaehler = $('zaehler');
  const opt = (wert, text) => `<option value="${esc(wert)}">${esc(text)}</option>`;
  const stufen = [...new Set(RANKING.map(r => r.tier))].sort((a,b) => a-b);
  const verbaende = [...new Set(RANKING.map(r => r.verband).filter(Boolean))].sort();
  const staffeln = [...new Set(RANKING.map(r => r.league))].sort();
  verbandFilter.innerHTML = opt('', 'Alle Verbände') + verbaende.map(v => opt(v,v)).join('');
  tierFilter.innerHTML = opt('', 'Alle Ligastufen')
    + stufen.map(t => opt(t, `${t}. Ligastufe`)).join('');
  leagueFilter.innerHTML = opt('', 'Alle Staffeln') + staffeln.map(l => opt(l,l)).join('');
  $('legend').innerHTML = stufen.map(t =>
    `<span class="tier t${t}-fg">${t}. Stufe</span>`).join('');

  const deltaCell = v => v === null || v === undefined
    ? '<span class="flat">–</span>'
    : (v === 0 ? '<span class="flat">±0</span>'
       : (v > 0 ? `<span class="up">▲ ${v}</span>` : `<span class="down">▼ ${-v}</span>`));

  const STUECK = 400;
  let gefiltert = [], gezeigt = 0, letzteStufe = null;

  function zeile(r, step){
    const icon = r.icon ? `<img src="${esc(r.icon)}" alt="" loading="lazy"
      onerror="this.style.visibility='hidden'">` : '<img alt="" style="visibility:hidden">';
    return `<tr class="t${r.tier}${step ? ' step' : ''}">
      <td class="rank">${r.rank}</td>
      <td class="delta">${deltaCell(r.delta)}</td>
      <td><div class="club">${icon}<span title="${esc(r.name)}">${esc(r.name)}</span></div></td>
      <td><span class="tier t${r.tier}-fg">${r.tier}</span>
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
      rows.insertAdjacentHTML('beforeend', teil.map(r => {
        const step = r.tier !== letzteStufe; letzteStufe = r.tier; return zeile(r, step);
      }).join(''));
      gezeigt += teil.length;
    }
    zaehler.textContent = gezeigt < gefiltert.length
      ? `${tausend(gezeigt)} von ${tausend(gefiltert.length)} angezeigt — weiterscrollen lädt nach`
      : `${tausend(gefiltert.length)} Mannschaften`;
    if (gezeigt < gefiltert.length &&
        document.body.scrollHeight <= window.innerHeight + 200) nachladen();
  }

  function render(){
    const term = q.value.trim().toLowerCase();
    const tier = tierFilter.value, league = leagueFilter.value,
          verband = verbandFilter.value;
    gefiltert = RANKING.filter(r =>
      (!tier || String(r.tier) === tier) &&
      (!league || r.league === league) &&
      (!verband || r.verband === verband) &&
      (!term || r.name.toLowerCase().includes(term)));
    gezeigt = 0; letzteStufe = null; rows.innerHTML = '';
    empty.hidden = gefiltert.length > 0;
    nachladen();
  }

  if (params.get('q')) q.value = params.get('q');
  if (params.get('verband')) verbandFilter.value = params.get('verband');
  if (params.get('stufe')) tierFilter.value = params.get('stufe');
  [q, tierFilter, leagueFilter, verbandFilter].forEach(el =>
    el.addEventListener('input', render));
  if (!window.__scrollHandler){
    window.__scrollHandler = true;
    window.addEventListener('scroll', () => {
      const fn = window.__nachladen;
      if (fn) fn();
    }, {passive: true});
  }
  window.__nachladen = () => {
    if (gezeigt >= gefiltert.length) return;
    if (window.scrollY + window.innerHeight >= document.body.scrollHeight - 800) nachladen();
  };
  render();
}

route();
</script>
</body>
</html>
"""


def _tier_css(max_tier: int = 14) -> str:
    """Farbband je Ligastufe plus farbige Kante beim Stufenwechsel."""
    zeilen = []
    for t in range(1, max_tier + 1):
        zeilen.append(f".t{t}-fg{{color:var(--t{t})}}")
        zeilen.append(f"tbody tr.t{t}{{background:color-mix(in srgb,"
                      f"var(--t{t}) 7%, var(--panel))}}")
    zeilen.append("tbody tr.step > td{border-top:2px solid var(--line)}")
    for t in range(1, max_tier + 1):
        zeilen.append(f"tbody tr.step.t{t} > td{{border-top-color:var(--t{t})}}")
    return "\n".join(zeilen)


def write_shell(out_dir: Path, sports: list[dict]) -> None:
    """Schreibt index.html. Die Daten je Sportart liegen in data/<slug>.json."""
    html = TEMPLATE
    html = html.replace("__TIER_CSS__", _tier_css())
    html = html.replace("__SPORTS__", json.dumps(sports, ensure_ascii=False))
    (out_dir / "index.html").write_text(html, encoding="utf-8")
