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
| 4 (Regionalliga) | Nord und Nordost; West, Südwest, Bayern fehlen | OpenLigaDB |
| 5–11 (Mittelrheinliga bis Kreisliga D) | **kompletter Fußball-Verband Mittelrhein**, alle 9 Kreise: Aachen, Berg, Bonn, Düren, Euskirchen, Heinsberg, Köln, Rhein-Erft, Sieg | fussball.de |

Aktuell rund **1.280 Mannschaften in 85 Staffeln über 11 Ligastufen**. Die Stufen 5–11
sind damit kein bundesweiter Schnitt, sondern ein regional vollständiger: innerhalb des
Mittelrheins ist die Pyramide lückenlos, ein Kreisligist aus Bayern fehlt. Das steht so
auch als Hinweis auf der Seite.

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
Ein kompletter Kaltstart sind rund 36 Discovery-Abrufe plus ein Tabellenabruf je
Staffel, zusammen etwa zwei Minuten.

**Auf einen anderen Landesverband umstellen:** `MANDANT` in `ranking/fussballde.py`
ändern (`23` = Mittelrhein, `21` = Westfalen, `31` = Bayern …) und `TIER_BY_LEAGUE`
anpassen — die Pyramide ist nicht überall gleich, Bayern hat unterhalb der Kreisliga
noch Kreisklasse und A-Klasse.

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
  oder −6. Derzeit betrifft das 20 der rund 1.280 Mannschaften; die Zahlen stammen so
  von fussball.de und sind kein Parser-Fehler.
* Innerhalb einer Ligastufe werden parallele Staffeln ohne Stärkekorrektur verglichen:
  2,4 Punkte pro Spiel in der Regionalliga Nord zählen genauso viel wie 2,4 in der
  Nordost-Staffel, und dasselbe gilt für Kreisliga B Staffel 2 gegen Staffel 3 oder
  die neun Kreisliga-A-Staffeln der verschiedenen Kreise untereinander. Bewusst
  einfach und für jeden nachvollziehbar.
