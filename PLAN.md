# Deutschlandweites Ranking aller Fußballvereine — Umsetzungsplan

Stand: 2026-08-31 · Saison 2026/27 (1. Spieltag BL gespielt am 28.08.2026)

## 1. Zielbild

Eine täglich aktualisierte, deutschlandweite Rangliste **aller** Herren-Mannschaften
von der Bundesliga bis zur Kreisklasse — eine einzige, durchnummerierte Tabelle
(Platz 1 … Platz N), gespeist aus Spieltagsergebnissen.

## 2. Das eigentliche Problem

Ab Ligastufe 4 laufen mehrere Staffeln parallel (5× Regionalliga, ~14× Oberliga,
~35× Landes-/Verbandsliga, ab Bezirks-/Kreisebene mehrere hundert). Tabellenplätze
sind dort **nicht vergleichbar**: „Platz 1 Regionalliga Bayern" ≠ „Platz 1
Regionalliga Nord". Ein reines Zusammenkleben von Ligatabellen ist willkürlich.

Gleichzeitig ist die Pyramide über Ergebnisse **verbunden**:

| Verbindungskante | verbindet |
|---|---|
| Auf-/Abstieg (Saisonwechsel, Rating wandert mit) | alle Stufen, stärkster Kanal |
| DFB-Pokal 1. Runde | Stufe 1–2 gegen Stufe 4–7 |
| 21 Landes-/Verbandspokale | Oberliga bis Kreisliga innerhalb eines Verbands |
| Kreispokale | untere Stufen untereinander |
| Aufstiegsrelegation / Staffel-Playoffs | benachbarte Stufen & Staffeln |

→ Ein **Elo-artiges Rating über den gesamten Spielgraphen** löst das Vergleichsproblem
sauber; die Ligatabelle allein kann es nicht.

## 3. Datenquellen — Rechercheergebnis

| Quelle | Abdeckung | Zugang | Bewertung |
|---|---|---|---|
| **OpenLigaDB** `api.openligadb.de` | BL, 2. BL, 3. Liga, DFB-Pokal zuverlässig; Regionalliga/Oberliga punktuell (rlno, rln, regio-bayern, NOFV-OL Nord, Thüringenliga für 2026) | frei, kein Key, JSON | ✅ **verifiziert**: 828 Ligen, `getbltable/bl1/2026`, `getmatchdata/bl1/2026` (306 Spiele) liefern live. Basis für Stufe 1–3. Community-gepflegt → unterhalb Stufe 3 lückenhaft. |
| **fussball.de** (DFBnet/DFB) | **vollständig**, bis Kreisklasse — die einzige Quelle mit echter Totalabdeckung | erreichbar (HTTP 200, serverseitig gerendert), aber **keine offene API**; geratene AJAX-Endpunkte liefern nur die SPA-Hülle. Nutzungsbedingungen untersagen automatisiertes Auslesen. | ⚠️ **Schlüsselquelle und zugleich Hauptrisiko** — Zugangsweg muss entschieden werden (siehe §7) |
| **api-fussball.de** | fussball.de-Daten als REST-JSON (`/api/team/table/{id}`, `next_games`, `prev_games`) | `x-auth-token`, 30 req/min, „kostenlose Nutzung" beworben | 🔍 kommerzieller Mittelsmann; Abdeckung/Preis vor Phase 3 zu prüfen |
| **DFBnet-Datenschnittstelle** | vollständig, offiziell | kostenpflichtiger Vertrag mit DFB Medien | 💶 der saubere, teure Weg |
| kicker.de | 1.–3. Liga, Regionalliga | **HTTP 403 für Bots** | ❌ nicht nutzbar |
| football-data.org / API-Football | nur Profiligen | Key, Free-Tier | Backup/Gegenprobe |

**Fazit:** Es gibt keine einzelne freie API für die ganze Pyramide. Stufe 1–3 sind
sofort verfügbar; alles ab Stufe 4 hängt an einer Zugangsentscheidung zu fussball.de.

## 4. Ranking-Methodik

### 4.1 Kern: Elo über alle Pflichtspiele

```
E_A     = 1 / (1 + 10^((R_B + HFA - R_A)/400))
R_A' = R_A + K · M(diff) · (S_A − E_A)
```

* `HFA` Heimvorteil ≈ +65 Elo (empirisch nachkalibrieren)
* `M(diff)` Torverhältnis-Multiplikator (1.00 / 1.50 / 1.75 / 1.75+(d−3)/8)
* `K` nach Wettbewerbsgewicht: Liga 20 · Pokal 24 · Relegation 28 · Freundschaftsspiel 0–6
* **Saisonübergang:** Rating wandert mit dem Verein mit (Auf-/Abstieg = wertvollste
  Information), plus 12 % Regression zum Mittel der neuen Ligastufe (Kaderfluktuation)
* **Cold Start:** Seed nach Stufe — Stufe 1 ≈ 1750, je Stufe −110 Elo, innerhalb der
  Stufe nach Vorsaisonplatzierung gespreizt

### 4.2 Zwei Rankings, bewusst getrennt

**A. Sportliches Gesamtranking** (Standardansicht — das, was man intuitiv erwartet)
Ligastufe dominiert; ein Kreisligist kann nie vor einem Bundesligisten stehen.

```
Score = 100000 − (Stufe−1)·5000 + 5000·(1 − p)

p = Perzentil des Teams innerhalb seiner Ligastufe bundesweit, aus
    z = w·z_Elo + (1−w)·z_PPG(Staffel-normiert)
    w = 0.8 → 0.4 im Saisonverlauf (früh zählt das Vorwissen, später die Punkte)
```
Die Staffelstärke muss nicht geraten werden — sie steckt bereits im Elo-Mittelwert
der Staffel.

**B. Reines Elo-Ranking** (zweiter Tab) — Spielstärke ohne Ligastufen-Korsett,
lässt Überraschungen zu (aufstrebender Oberligist vor Drittligist).

### 4.3 Qualitätssicherung
Backtest über 10+ Saisons: Log-Loss / Brier-Score der Ergebnisprognose gegen zwei
Baselines (Heimsieg-immer, Tabellenplatz-Differenz). Kalibrierung von `K`, `HFA`,
Regression per Grid-Search auf Trainingssaisons, Validierung auf Holdout.

## 5. Architektur

```
adapters/            openligadb.py · fussballde.py · apifussball.py
  └─ liefern normalisierte Match- & Tabellen-Records
core/
  identity.py        Vereins-/Team-Identität, Alias-Auflösung
  pyramid.py         Liga → (Stufe, Staffel, Landesverband)
  elo.py             Rating-Engine, inkrementell + Full-Replay
  ranking.py         Score-Berechnung, Tagesschnappschuss
storage/             SQLite (MVP) → PostgreSQL (ab Stufe 6)
   club · team · league · season · match · rating_history · ranking_snapshot
jobs/daily.py        03:00 Uhr: Delta-Fetch → Elo → Snapshot → Publish
web/                 FastAPI + Jinja (oder statischer Export)
```

**Härtester Engineering-Teil: Entity Resolution.** „1. FC Köln" / „1.FC Köln" /
„FC Köln", „Borussia Dortmund II" vs. „BVB II", gleichnamige Dorfvereine,
Spielgemeinschaften („SG …"), Fusionen mitten in der Saison.
Lösung: fussball.de-Vereins-ID als kanonischer Schlüssel (es ist die DFB-Stammnummer),
darüber Fuzzy-Matching + gepflegte Alias-Tabelle für die ~500 bekanntesten Vereine.

**Tech:** Python 3.12, httpx (async, Rate-Limit + Backoff), Pydantic, polars,
SQLite/Postgres, cron bzw. launchd.

## 6. Phasen

| # | Inhalt | Umfang | Aufwand |
|---|---|---|---|
| **1 — MVP** | OpenLigaDB-Adapter, Elo-Engine, Ranking Stufe 1–3 + verfügbare Regionalligen, CSV/CLI-Ausgabe | ~56 + ~40 Vereine | 0,5–1 Tag → **das initiale Ranking** |
| **2 — Kalibrierung** | 10–15 Saisons Historie laden, Elo einlaufen lassen, Backtest, Parameter-Fit | — | 1–2 Tage |
| **3 — Stufe 4–5** | Zugangsweg fussball.de/api-fussball, Liga-Registry (5 RL + ~14 OL), Adapter | ~320 Vereine | 2–4 Tage |
| **4 — Stufe 6–11** | Flächendeckung, Crawl-Budget & Inkrementalität, Entity Resolution im Maßstab | **~24.000 Vereine, ~2.200 Ligen** | Wochen, nicht Tage |
| **5 — Produkt** | Web-Frontend, Suche, Filter (Bundesland/Stufe/Verband), Vereinsprofil mit Elo-Verlauf, täglicher Cron, Monitoring | — | 2–4 Tage |

## 7. Offene Entscheidungen (blockieren Phase 3+, nicht Phase 1)

1. **Zieltiefe:** Stufe 1–5 (~450 Vereine, in Tagen machbar) oder wirklich bis
   Kreisklasse (~24.000 Vereine, Wochen)?
2. **Zugangsweg fussball.de:** eigenes Crawling gegen die Nutzungsbedingungen /
   api-fussball.de lizenzieren / offizielle DFBnet-Schnittstelle / nur frei
   verfügbare Quellen (dann Deckel bei Stufe 3–4).
3. **Reservemannschaften:** zählen „Bayern München II", „BVB II" als eigene
   Einträge oder wird pro Verein nur die erste Mannschaft gewertet?
4. **Frauen-/Jugendligen:** vorerst außen vor (Annahme) oder mitziehen?

## 8. Ehrliche Einschätzung

Die Ranking-Mathematik ist der kleinere Teil. Das Projekt steht und fällt mit dem
Datenzugang unterhalb der 3. Liga — dort gibt es keine freie API, und fussball.de
ist die einzige vollständige Quelle. Phase 1 und 2 liefern trotzdem sofort ein
belastbares, methodisch sauberes Ranking, auf das sich Stufe 4 ff. später
verlustfrei aufsetzen lässt.
