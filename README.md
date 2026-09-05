# FCR Deutschland — dein Club-Ranking

**→ [professororbach.github.io/deutschlandtabelle](https://professororbach.github.io/deutschlandtabelle/)**

Jeder Verein des Landes in einer einzigen Rangfolge — von der Bundesliga bis zur
Kreisklasse, für mehrere Sportarten.

| Sportart | Stand | Umfang |
|---|---|---|
| ⚽ Fußball | fertig | 26.825 Mannschaften, 1.951 Staffeln, 14 Ligastufen, 21 Landesverbände |
| 🤾 Handball | fertig | 1.911 Mannschaften, 175 Staffeln, 13 Ligastufen |
| 🏀 Basketball | offen | Datenquelle noch nicht erschlossen |

## Aufbau der Seite

Eine Seite, vier Ansichten über die Adresszeile:

```
#home        Marke, Beschreibung, Überblick über die Sportarten
#fussball    Bestenlisten und komplette Tabelle
#handball    dito
#basketball  Platzhalter, solange die Quelle fehlt
```

Warum eine einzige Seite: so lauten die Adressen wie gewünscht `…/#fussball`. Die
Daten liegen aber **nicht** in der Seite, sondern je Sportart in `docs/data/<sport>.json`
und werden erst beim Wechsel geladen — die Fußballtabelle allein wiegt 2,2 MB, alle
Sportarten eingebettet wären unbenutzbar. Dadurch ist `index.html` nur 25 KB groß.

Das Suchfeld auf der Startseite springt in die gefilterte Tabelle der gewählten
Sportart (`#fussball?q=…`); ebenso verstanden werden `?verband=` und `?stufe=`.

**Headerbild einsetzen:** eine Datei `docs/header.jpg` ablegen, empfohlen 2000 × 700 px.
Der gestrichelte Platzhalter verschwindet dann von selbst.

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

## Handball: handball.net

Der Spielbetrieb des DHB liegt hinter einer JSON-Schnittstelle, die ohne Anmeldung
antwortet — sie verlangt allerdings einen `Referer`-Header, sonst kommt HTTP 403:

```
/api/new/competitions?season_id=2627&per_page=100&page=<n>&has_phases=1&with_phases=1
/api/new/standings?phase_id=<id>
/api/new/federations/<id>
```

**Die Ligastufe ist hier einfacher als beim Fußball.** handball.net führt zu jedem
Wettbewerb eine `category`, deren Name bundesweit vereinheitlicht ist
(„Bezirksoberliga / Kreisoberliga / Regionsoberliga"). Elf Namen decken die ganze
Pyramide ab — statt 146 Spielklassen über 21 Verbandstabellen wie im Fußball.

Zwei Fallen, über die ich gestolpert bin und die im Code kommentiert sind:

* **Die Kategorie-*IDs* sind nicht die Ligastufe.** Sie wiederholen sich je
  Altersklasse und Geschlecht — id 3 und id 16 heißen beide „3. Liga". Maßgeblich
  ist der Name.
* **`standings` liefert eine Zeile je Mannschaft und geplantem Spieltag.** Eine
  16er-Staffel mit 30 Spieltagen ergibt 480 Zeilen, die derzeit alle denselben Stand
  tragen. Ungefiltert kam ich auf 40.416 Handballmannschaften. Es wird je Mannschaft
  die Zeile mit den meisten absolvierten Spielen genommen.

Ein struktureller Marker für Ligabetrieb fehlt: `competition_type_id` ist bei allen
897 Wettbewerben 0, und einem Freundschaftsspiel wird munter die Kategorie „Oberliga"
verpasst. Freundschafts-, Test- und Pokalrunden werden deshalb über den Namen
ausgeschlossen — unschöner, aber die Daten geben nichts anderes her.

### Die Bundesligen kommen von woanders

handball.net führt den Spielbetrieb erst ab der 3. Liga. Die 1. und 2. Bundesliga
laufen auf der HBL-Seite (opel-hbl.de), deren Tabellen-Widget von **Sportradar**
stammt:

```
https://embed-api.eui.connect.sportradar.com/v1/embed/<id>/standings?locale=de-DE
    248 = 1. Handball-Bundesliga
    254 = 2. Handball-Bundesliga
```

Der Endpunkt antwortet ohne jeden Header. Saison-Parameter ignoriert er — jede
Embed-ID ist fest auf einen Wettbewerb *und* dessen laufende Saison konfiguriert.
Die IDs stehen deshalb hart in `ranking/hbl.py`, und zur Sicherheit wird der
Wettbewerbsname gegengeprüft: **Embed 257 liefert ebenfalls 18 Mannschaften der
1. Bundesliga — aber die abgeschlossene Vorsaison.** Ohne diese Prüfung wäre so ein
Vertauscher unbemerkt geblieben.

Punkte stehen im deutschen Handball-Format „4:0" (Plus- zu Minuspunkten); gezählt
wird die Zahl vor dem Doppelpunkt. Das passt zum Zwei-Punkte-System, das auch
handball.net liefert.

**Bekannte Lücke:** Nicht jeder Landesverband wickelt seinen Spielbetrieb über
handball.net ab, die Abdeckung unterhalb der überregionalen Ligen ist daher nicht
flächendeckend. Das steht als Hinweis auf der Seite.

## Die Datendateien

Der Logikbaum **Verband → Ligastufe → Spielklasse → Gebiet → Staffel → Verein** ist der
inhaltliche Kern und liegt deshalb als zwei verknüpfbare Tabellen vor, nicht nur
implizit im Staffelnamen.

### `docs/<sport>-vereine.csv` — eine Zeile je Mannschaft

| Spalte | Bedeutung |
|---|---|
| `rang_bundesweit` | Platz in der Gesamtrangfolge, lückenlos 1..n |
| `verein` | Name laut Quelle |
| `verband` | Landesverband; leer bei den überregionalen Ligen (Stufe 1–4) |
| `gebiet` | Fußballkreis oder Verbandsebene; leer, wo die Quelle keinen führt |
| `ligastufe` | 1–14 |
| `spielklasse` | Kategorie in der Sprache des Verbands, z. B. „Kreisliga B", „Landesklasse" |
| `staffel` | die konkrete Staffel, in der gespielt wird |
| `staffel_id` | Schlüssel der Staffel bei der Quelle — verbindet mit `ligen.csv` |
| `platz_in_staffel` | klassischer Tabellenplatz, lückenlos 1..n je Staffel |
| `spiele` … `punkte` | Bilanz der laufenden Saison |
| `punkte_pro_spiel` | Sortierkriterium innerhalb einer Ligastufe |
| `rangaenderung_vorwoche` | leer, wo die Quelle keine Einzelspiele liefert |
| `quelle` | OpenLigaDB oder fussball.de |

**Spielklasse und Staffel sind nicht dasselbe.** Die Spielklasse ist die Kategorie des
Verbands und bestimmt die Ligastufe; die Staffel ist die konkrete Gruppe darunter. „Kreisliga B"
ist eine Spielklasse, „Kreisliga B Staffel 3 · Kreis Berg" eine von vielen Staffeln darin.

### `docs/<sport>-ligen.csv` — eine Zeile je Staffel

Der Baum ohne die Vereine: `staffel_id`, `verband`, `gebiet`, `ligastufe`, `spielklasse`,
`staffel`, dazu `mannschaften`, `spiele_gesamt`, `tore_gesamt`, `punkte_gesamt`,
`tabellenfuehrer` und `quelle`. Über `staffel_id` lässt sich die Vereinsdatei daran anfügen.

## Prüfen

```bash
python3 pruefen.py                     # Fußball
python3 pruefen.py --sport handball
```

Das Skript liest ausschließlich die beiden CSV-Dateien — es holt nichts nach und
vertraut keiner Zwischenstufe der Pipeline, das Ergebnis ist also unabhängig
nachvollziehbar. Geprüft wird in sechs Gruppen:

1. **Verknüpfung** — jede `staffel_id` aus `vereine.csv` existiert in `ligen.csv`, keine
   verwaiste Staffel, IDs eindeutig.
2. **Logikbaum** — Verband, Ligastufe, Spielklasse und Gebiet sind innerhalb einer
   Staffel einheitlich; beide Dateien beschreiben dieselbe Staffel gleich; eine
   Spielklasse liegt je Verband auf genau einer Ligastufe; die Stufen eines Verbands sind
   lückenlos.
3. **Bilanz je Mannschaft** — S+U+N = Spiele, Tordifferenz = Tore − Gegentore, Punkte pro
   Spiel stimmt.
4. **Geschlossenheit je Staffel** — die schärfste Prüfung: in einer Staffel spielen alle
   nur gegeneinander, also muss die **Summe der Tore der Summe der Gegentore entsprechen**.
   Dazu: gerade Spielsumme, lückenlose Tabellenplätze, nicht mehr Punkte vergeben als
   Partien erlauben.
5. **Rangfolge** — Ränge lückenlos, Sortierung nach Ligastufe und dann Punkten pro Spiel.
6. **Eckdaten** — 18/18/20 in den ersten drei Ligen, fünf Regionalligen auf Stufe 4.

Vier Befunde sind **Hinweise, keine Fehler** — sie beschreiben Eigenheiten des
Amateurfußballs und brechen nicht ab:

* **Punktabzüge** (rund 140 Mannschaften): Punkte weichen von 3×Siege + Unentschieden ab.
* **Ungleiche Torsummen** in 26 von 1.952 Staffeln, und in 10 davon eine ungerade
  Spielsumme. Ursache ist eine Wertung gegen eine zurückgezogene Mannschaft: sie erzeugt
  eine Niederlage ohne zugehörigen Sieg. In der Kreisliga A Aachen etwa stehen 7 Siege
  gegen 8 Niederlagen, und die Torlücke von genau 5 entspricht dem 0:5 auf dem letzten
  Platz. Ein *Parser*-Fehler sähe anders aus — er würde S+U+N, die Tordifferenz oder die
  Tabellenplätze zerlegen, und die sind hart geprüft.
* **Unterschiedlich weit gespielte Staffeln**: normal, weil Nachholspiele existieren.

Rückgabewert 0 bei bestandenen harten Prüfungen, sonst 1. Aktueller Stand:
**Fußball: 20 Prüfungen bestanden, 0 Fehler, 4 Hinweise.
Handball: 20 bestanden, 0 Fehler, 2 Hinweise.**

Beim Handball führt die Quelle drei Mannschaften doppelt in derselben Staffel
(„TV Bitburg" zweimal); sie werden zu einer zusammengefasst.

## Benutzung

```bash
python3 build.py --sport fussball    # rund eine Stunde beim Kaltstart
python3 build.py --sport handball    # wenige Minuten
python3 build.py --nur-huelle        # nur index.html neu, nichts abrufen
```

Keine Abhängigkeiten außer Python 3.12+. Ergebnis: `docs/index.html`, `docs/data/<sport>.json`,
`docs/<sport>-vereine.csv`, `docs/<sport>-ligen.csv`.

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
ranking/site.py       Seitengerüst mit den #-Routen
ranking/landing.py    die Bestenlisten
ranking/handballnet.py Adapter für handball.net (ab 3. Liga)
ranking/hbl.py        Adapter für die Handball-Bundesligen (Sportradar)
ranking/render.py     CSV und kompakte Fassung
pruefen.py            Prüfskript für die CSV-Dateien
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
