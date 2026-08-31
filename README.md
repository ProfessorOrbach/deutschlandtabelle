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
| 1–3 | bundesweit vollständig | OpenLigaDB |
| 4 (Regionalliga) | **alle fünf Staffeln** — Nord und Nordost mit Einzelspielen aus OpenLigaDB, West, Südwest und Bayern von fussball.de | beide |
| 5–12 | **ganz Nordrhein-Westfalen** — die Verbände Mittelrhein, Niederrhein und Westfalen, rund 42 Fußballkreise, von der Oberliga bis zur Kreisliga D | fussball.de |

Aktuell **5.350 Mannschaften in 360 Staffeln über 12 Ligastufen**.

Auf Stufe 4 bleiben Nord und Nordost bewusst bei OpenLigaDB: nur diese Quelle liefert
Einzelspiele mit Datum, und nur damit funktioniert für sie die Vorwochen-Spalte. Die drei
fehlenden Staffeln kommen über fussball.de dazu — vier davon führt der Mandant
„Deutschland", die Regionalliga Bayern läuft beim BFV und hat deshalb einen eigenen
Eintrag in `VERBAENDE`. Die Stufen 5–12 sind
kein bundesweiter Schnitt, sondern ein regional vollständiger: innerhalb von NRW ist die
Pyramide lückenlos, ein bayerischer Kreisligist fehlt. Das steht so auch auf der Seite.

Warum ausgerechnet diese drei: sie hängen über die Regionalliga West zusammen, die ohnehin
erfasst ist. Das Ranking bleibt dadurch sportlich begründet und ist nicht nur groß.

**Die Pyramide ist nicht überall gleich.** Westfalen schiebt zwischen Oberliga und
Landesliga noch die Verbandsliga (Westfalenliga) ein und reicht deshalb bis Stufe 12,
Mittelrhein und Niederrhein enden bei 11. Jeder Verband braucht daher in
`ranking/fussballde.py` seine eigene `tiers`-Tabelle — eine Heuristik über die
Spielklassen-Namen wäre schlicht falsch. Auch die Mannschaftsart „Herren" hat je Verband
eine andere ID (95 / 343 / 41); die wird zur Laufzeit ermittelt.

### Zu fussball.de

`ranking/fussballde.py` ist ein **Entwurf mit Vorbehalt**. Der Ergebnisdienst von
oberberg-aktuell.de, der ursprünglich als Quelle vorgeschlagen war, enthält selbst keine
Daten — er verlinkt ausschließlich auf fussball.de. Deren Nutzungsbedingungen untersagen
automatisiertes Auslesen. Abschalten:

```bash
python3 build.py --no-fussballde
```

oder dauerhaft `ENABLED = False` in `ranking/fussballde.py`. Der saubere Weg für den
Dauerbetrieb ist die DFBnet-Datenschnittstelle oder ein lizenzierter Anbieter, siehe
[PLAN.md §3](PLAN.md).

**Staffel-Discovery über die WAM-Schnittstelle.** Der Matchkalender von fussball.de füllt
seine Auswahllisten aus statischen JSON-Dateien. Damit lässt sich der Wettbewerbsbaum
vollständig ablaufen, ohne eine einzige Staffel-ID von Hand zu pflegen:

```
wam_kinds_<mandant>_<saison>_<typ>.json
    → Mannschaftsart → Spielklasse → Gebiet (die Fußballkreise)

wam_competitions_<mandant>_<saison>_<typ>_<art>_<klasse>_<gebiet>.json
    → {Staffel-URL: Name}, die URL enthält die Staffel-ID der laufenden Saison
```

Der Adapter folgt damit dem Saisonwechsel und neu eingerichteten Staffeln von selbst.
Ein Kaltstart über die drei Verbände sind rund 180 Discovery-Abrufe plus einer je
Staffel, zusammen etwa zehn Minuten. Danach greift der Plattencache.

**Einen weiteren Verband aufnehmen:** einen `Verband(...)`-Eintrag in `VERBAENDE`
ergänzen. Die Mandanten-ID steht in `wam_base.json` (`21` = Westfalen, `31` = Bayern,
`34` = Hessen …), die Spielklassen-IDs in `wam_kinds_<mandant>_<saison>_1.json`.

**Es gibt nur fertige Tabellen, keine Einzelspiele** — die Spielliste baut fussball.de
erst im Browser per JavaScript auf. Diesen Staffeln fehlt deshalb die Vorwochen-Differenz;
sie zeigen dauerhaft „–". Wer sie braucht, müsste Tagesschnappschüsse speichern statt sie
nachzurechnen.

`ranking/leagues.py` probiert für die oberen Stufen mehrere bekannte OpenLigaDB-Kürzel
pro Staffel durch. Sobald jemand dort eine fehlende Staffel einstellt, taucht sie beim
nächsten Lauf von selbst im Ranking auf.

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
  oder −6. Derzeit betrifft das rund 100 der 5.350 Mannschaften; die Zahlen stammen so von
  fussball.de und sind kein Parser-Fehler.
* **Die Seite scrollt nicht, die Tabelle schon.** Damit der Spaltenkopf beim Blättern
  stehen bleibt, ist die Seite ein Layout in Fensterhöhe, in dem nur der Tabellenbereich
  scrollt. Ein `position:sticky` am `<th>` allein reicht nicht: es klebt am oberen Rand
  seines Scroll-Containers, und der darf dafür nicht selbst aus dem Bild wandern.
  Abdeckungshinweis und Methodik sind deshalb einklappbar. Unter 560 px Fensterhöhe
  fällt die Seite auf normales Scrollen zurück.
* **Die Seite trägt ihre Daten kompakt.** Zeilen stecken als Arrays statt als Objekte in
  der Seite, Staffel- und Verbandsnamen nur einmal in einer Nachschlagetabelle. Das drückt
  `index.html` von 1,7 MB auf gut 430 KB; ein Filterwechsel über alle Zeilen dauert
  rund 75 ms.
* **Gleichnamige Vereine bleiben getrennt.** „TuS Brake" gibt es in Bielefeld und in
  Lemgo — zwei verschiedene Vereine. Sie werden nicht verschmolzen, sind in der Liste
  aber nur an der Liga-Spalte auseinanderzuhalten.
* Innerhalb einer Ligastufe werden parallele Staffeln ohne Stärkekorrektur verglichen:
  2,4 Punkte pro Spiel in der Regionalliga Nord zählen genauso viel wie 2,4 in der
  Nordost-Staffel, und dasselbe gilt für Kreisliga B Staffel 2 gegen Staffel 3 oder
  die Kreisliga-A-Staffeln der 42 Kreise untereinander. Bewusst einfach und für
  jeden nachvollziehbar.
