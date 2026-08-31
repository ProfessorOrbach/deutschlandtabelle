# Deutschlandtabelle

**→ [professororbach.github.io/deutschlandtabelle](https://professororbach.github.io/deutschlandtabelle/)**

Eine einzige, tagesaktuelle Rangfolge aller erfassten deutschen Fußballmannschaften —
ligaübergreifend, von der Bundesliga abwärts, ausschließlich aus den Spielen der
laufenden Saison. Ausgabe ist eine statische Seite für GitHub Pages.

→ Ursprünglicher Umsetzungsplan und Datenquellen-Recherche: [PLAN.md](PLAN.md)

## Das Problem

Ab der 4. Ligastufe laufen mehrere Staffeln parallel. Tabellenplätze sind dort nicht
vergleichbar: „Platz 1 Regionalliga Nord" ist nicht dasselbe wie „Platz 1 Regionalliga
Nordost". Ligatabellen einfach aneinanderzuhängen wäre willkürlich.

## Wie sortiert wird

1. **Ligastufe** — ein Regionalligist steht nie vor einem Drittligisten.
2. Innerhalb der Stufe: **Punkte pro Spiel**, dann Tordifferenz pro Spiel, dann Tore
   pro Spiel, dann Name.

Punkte *pro Spiel* statt absoluter Punkte, weil parallele Staffeln derselben Stufe
unterschiedlich weit sind: die Regionalligen starten Wochen vor der Bundesliga und
haben bereits mehr Spieltage absolviert. Dadurch verzahnen sich Regionalliga Nord und
Nordost in einer gemeinsamen Rangfolge, statt blockweise hintereinanderzustehen.

Die Spalte **± Wo.** zeigt die Veränderung des Rankingplatzes gegenüber dem Stand vor
sieben Tagen. Dafür sind keine gespeicherten Momentaufnahmen nötig — die Rangliste von
vor einer Woche wird aus denselben Spieldaten nachgerechnet, indem alle späteren Spiele
ausgeblendet werden. Beide Ranglisten umfassen dabei zwingend *alle* Mannschaften, auch
solche ohne Spiel; sonst würde eine später startende Liga sämtliche Plätze darunter
verschieben und lauter falsche Veränderungen erzeugen. Mannschaften, die vor einer
Woche noch kein Spiel hatten, zeigen „–" statt eines erfundenen Werts.

## Datenquellen und Abdeckung

| Stufe | Umfang | Quelle |
|---|---|---|
| 1–3 | bundesweit | OpenLigaDB |
| 4 (Regionalliga) | alle fünf Staffeln — Nord und Nordost mit Einzelspielen aus OpenLigaDB, West, Südwest und Bayern von fussball.de | beide |
| 5–14 | **alle 21 Landesverbände**, von der Oberliga bis zur Kreisklasse | fussball.de |

**26.836 Mannschaften in 1.952 Staffeln über 14 Ligastufen.** Bayern stellt mit 5.063
Mannschaften den größten Verband, Bremen mit 125 den kleinsten. Stufe 14 gibt es nur in
Hessen (2. Kreisklasse, 14 Mannschaften).

### Die Ligastufen-Zuordnung

145 Spielklassen auf Ligastufen abzubilden klang nach Einzelfallarbeit, ist aber
weitgehend ableitbar: **die WAM-Datei listet die Spielklassen je Verband in
Pyramidenreihenfolge.** Belegt durch Schleswig-Holstein, wo Landesliga (ID 78) vor
Verbandsliga (ID 77) steht — die Reihenfolge ist also inhaltlich und nicht numerisch.
Deshalb genügen je Verband die Startstufe und die Reihenfolge:

* **Startstufe 5**, wo der Verband seine Oberliga selbst betreibt — Westfalen,
  Niederrhein, Mittelrhein, Niedersachsen, Hessen, Schleswig-Holstein, Hamburg, Bremen,
  Württemberg.
* **Startstufe 6**, wo die Oberliga einem Regionalverband gehört — die Ostverbände
  (NOFV), Rheinland/Saarland/Südwest (Oberliga Rheinland-Pfalz/Saar) und
  Baden/Südbaden (Oberliga Baden-Württemberg).
* **Startstufe 4** nur bei Bayern, das seine Regionalliga selbst führt.

Die drei Oberligen ohne eigenen Landesverband — Rheinland-Pfalz/Saar und die beiden
NOFV-Oberligen — liefert der Mandant „Deutschland" unter Spielklasse 6.

Zwei Sonderfälle: Rheinlands „Reserveklasse" ist Parallelbetrieb und keine Pyramidenstufe,
deshalb ausgeschlossen. Bei Sachsen sind „1./2./3. Kreisliga" und „1./2. Kreisklasse" der
Reihenfolge nach auf die Stufen 9–13 gelegt; das folgt der WAM-Reihenfolge, ist aber die
unsicherste Zuordnung im ganzen Satz.

### Vergleichbarkeit

Innerhalb eines Verbands ist die Rangfolge belastbar, weil dort alle Staffeln über Auf-
und Abstieg zusammenhängen. **Zwischen Verbänden gilt das unterhalb der Regionalliga
nicht** — ein Kreisligist aus Oberberg und einer aus Sachsen begegnen sich nie, auch
nicht über eine Aufstiegskette. Die bundesweite Liste ordnet dort nur nach Ligastufe und
Punkten pro Spiel. Die Seite sagt das im Hinweiskasten und in einer Zeile über der
Tabelle, die zum Verbandsfilter führt.

### Zu fussball.de

`ranking/fussballde.py` ist ein **Entwurf mit Vorbehalt**. Die Nutzungsbedingungen von
fussball.de untersagen automatisiertes Auslesen, und bundesweit sind das rund 3.500
Abrufe je Kaltstart. Abschalten:

```bash
python3 build.py --no-fussballde
```

oder dauerhaft `ENABLED = False` in `ranking/fussballde.py`. Für den Dauerbetrieb ist die
DFBnet-Datenschnittstelle oder ein lizenzierter Anbieter der saubere Weg, siehe
[PLAN.md §3](PLAN.md).

**Staffel-Discovery über die WAM-Schnittstelle.** Der Matchkalender von fussball.de füllt
seine Auswahllisten aus statischen JSON-Dateien:

```
wam_base.json                                  → alle Mandanten (Verbände)
wam_kinds_<mandant>_<saison>_<typ>.json        → Mannschaftsart → Spielklasse → Gebiet
wam_competitions_<mandant>_<saison>_<typ>_<art>_<klasse>_<gebiet>.json
                                               → {Staffel-URL: Name}
```

Keine Staffel-ID ist von Hand gepflegt; der Adapter folgt Saisonwechseln und neuen
Staffeln von selbst. Kaltstart rund eine Stunde, danach greift der Plattencache.

**Einen Verband anpassen:** `VERBAENDE` in `ranking/fussballde.py`. Ein Eintrag ist
Mandanten-ID, Name, Startstufe und die Spielklassen-IDs in Pyramidenreihenfolge.

**Es gibt nur fertige Tabellen, keine Einzelspiele** — die Spielliste baut fussball.de
erst im Browser per JavaScript auf. Diesen Staffeln fehlt deshalb die Vorwochen-Differenz;
sie zeigen dauerhaft „–".

## Benutzung

```bash
python3 build.py              # baut docs/ (nutzt den Plattencache)
python3 build.py --no-cache   # alles frisch laden
```

Keine Abhängigkeiten außer Python 3.12+. Ergebnis: `docs/index.html`,
`docs/ranking.json`, `docs/ranking.csv`.

## Veröffentlichung

Die Seite liegt auf GitHub Pages und wird derzeit direkt aus dem Ordner `docs/`
des `main`-Branch ausgeliefert. Ein `python3 build.py` gefolgt von Commit und Push
aktualisiert sie.

**Tägliche Aktualisierung aktivieren.** `.github/workflows/daily.yml` baut das Ranking
täglich um 03:15 UTC neu. Zum Hochladen braucht der GitHub-Token einmalig den
`workflow`-Scope:

```bash
gh auth refresh -s workflow
git add .github/workflows/daily.yml && git commit -m "Täglicher Build" && git push
```

Danach in *Settings → Pages → Source* von „Deploy from a branch" auf
**GitHub Actions** umstellen.

## Aufbau

```
build.py              Einstiegspunkt
ranking/api.py        OpenLigaDB-Client (Cache, Rate-Limit, 429-Backoff)
ranking/leagues.py    Registry: Kürzel -> Ligastufe, Staffel, Verband
ranking/model.py      Datenmodell, Vereinsidentität, Ergebnis-Extraktion
ranking/load.py       Ligen laden, Spiele und Mannschaften bilden
ranking/fussballde.py Adapter für Stufe 5-11 (Entwurf, abschaltbar)
ranking/rank.py       Tabelle, Rangfolge, Vorwochenvergleich
ranking/render.py     HTML, JSON, CSV
```

## Anmerkungen

* Reservemannschaften („Borussia Dortmund II") sind bewusst eigene Einträge, da sie
  eigene Ligen bespielen.
* Vereinsnamen werden über eine normalisierte Form zusammengeführt, weil OpenLigaDB in
  community-gepflegten Ligen abweichende Schreibweisen führt („Werder Bremen" /
  „SV Werder Bremen"). Die Reserve-Kennung bleibt dabei erhalten.
* **Negative Punktzahlen sind echt.** Im Amateurbereich gibt es Punktabzüge, meist −3
  oder −6. Derzeit betrifft das 143 der 26.836 Mannschaften; die Zahlen stammen so von
  fussball.de und sind kein Parser-Fehler.
* **Nur die Kopfzeile der Tabelle bleibt stehen.** Titel, Kennzahlen und Filter scrollen
  weg, die Spaltenüberschriften kleben am Fensterrand. Der Haken dabei: ein
  `position:sticky` am `<th>` klebt am oberen Rand seines *Scroll-Containers*. Ein
  `overflow-x:auto` um die Tabelle — der übliche Griff für breite Tabellen — macht genau
  so einen Container auf und setzt das Kleben außer Kraft. Deshalb hat die Tabelle hier
  keinen eigenen Scrollbereich; sie passt sich stattdessen über zwei Umbruchpunkte an:

  | Fensterbreite | Spalten | Tabellenbreite |
  |---|---|---|
  | ab 1100 px | alle 13 | 1054 px |
  | 860–1100 px | 9 (ohne Pl., S, U, N) | 762 px |
  | unter 860 px | 5 (#, Verein, Liga, Sp, Pkt/Sp) | feste Spaltenbreiten, Silbentrennung |

  Die Schwellen stammen aus gemessenen Tabellenbreiten, nicht aus Gerätegrößen.
  Unterhalb von 860 px greift außerdem `table-layout:fixed` — die automatische
  Tabellenbreite hält sich sonst nicht an den Container und schiebt die Verein-Spalte
  auf Maximalbreite.
* **Die Tabelle lädt stückweise nach.** 26.836 Zeilen auf einmal wären rund 350.000
  DOM-Knoten. Gerendert werden 400 Zeilen, beim Scrollen kommen weitere dazu; gefiltert
  und sortiert wird weiterhin über den vollen Datensatz. Ergebnis: 10.471 statt 350.000
  Knoten, 200 ms Ladezeit, 74 ms je Filterwechsel — genauso schnell wie vorher mit 5.350
  Mannschaften.
* **Die Seite trägt ihre Daten kompakt.** Zeilen stecken als Arrays statt als Objekte in
  der Seite, Staffel- und Verbandsnamen nur einmal in einer Nachschlagetabelle. Das drückt
  `index.html` auf etwa ein Viertel.
* **Gleichnamige Vereine bleiben getrennt.** 64 Vereinsnamen sind mehrfach vergeben,
  „SG Werratal" und „SV Bernried" sogar dreifach. Sie werden nicht verschmolzen, sind in
  der Liste aber nur an der Liga-Spalte auseinanderzuhalten.
* **`docs/` wiegt rund 12 MB.** Solange GitHub Pages direkt aus dem `main`-Branch
  ausliefert, landet das bei jedem Build als neuer Commit im Repo. Sobald der
  Actions-Workflow aktiv ist (siehe unten), wird `docs/` gebaut und deployt, ohne
  committet zu werden — dann entfällt das Wachstum.
* Innerhalb einer Ligastufe werden parallele Staffeln ohne Stärkekorrektur verglichen:
  2,4 Punkte pro Spiel in der Regionalliga Nord zählen genauso viel wie 2,4 in der
  Nordost-Staffel, und dasselbe gilt für Kreisliga B Staffel 2 gegen Staffel 3 oder
  die Kreisliga-A-Staffeln der 42 Kreise untereinander. Bewusst einfach und für
  jeden nachvollziehbar.
