"""Adapter für fussball.de -- Staffeln unterhalb der Regionalliga.

Hintergrund: OpenLigaDB endet faktisch bei Ligastufe 4. Der Ergebnisdienst von
oberberg-aktuell.de führt zwar die Ligen des Kreises Berg auf, enthält aber
selbst keine Daten -- er verlinkt ausschließlich auf fussball.de. Von dort
stammen die Zahlen hier.

RECHTLICHER HINWEIS: Die Nutzungsbedingungen von fussball.de untersagen das
automatisierte Auslesen. Dieser Adapter ist ein Entwurf und lässt sich mit
`python3 build.py --no-fussballde` bzw. ENABLED = False abschalten. Für den
produktiven Betrieb ist der saubere Weg die DFBnet-Datenschnittstelle oder ein
lizenzierter Anbieter -- siehe PLAN.md §3.

Technik: Die Staffel-IDs sind saisonspezifisch. Als Anker dienen die IDs der
Saison 2025/26 aus dem Oberberg-Ergebnisdienst; deren Seite verweist im
<link rel="canonical"> auf die Nachfolgestaffel der laufenden Saison. Dadurch
folgt der Adapter dem Saisonwechsel von selbst.

Geliefert werden fertige Tabellen, keine Einzelspiele: die Spielliste baut
fussball.de erst im Browser per JavaScript auf. Deshalb fehlt diesen Staffeln
die Vorwochen-Differenz -- ohne Spieldaten mit Datum lässt sie sich nicht
nachrechnen.
"""
from __future__ import annotations

import hashlib
import html
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENABLED = True

BASE = "https://www.fussball.de"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Ligapyramide des Fußball-Verbands Mittelrhein, Kreis Berg (Oberberg).
# (Anzeigename, Ligastufe, Anker-Staffel-ID aus Saison 2025/26)
OBERBERG = [
    ("Mittelrheinliga",        5,  "02TF9RU51O00000FVS5489BTVTLPPK10-G"),
    ("Landesliga Staffel 1",   6,  "02TF9TPSSC00000AVS5489BTVTLPPK10-G"),
    ("Bezirksliga Staffel 1",  7,  "02TF9TR5OG00000HVS5489BTVTLPPK10-G"),
    ("Kreisliga A",            8,  "02TM13G8H400000CVS5489BTVT4H6CF2-G"),
    ("Kreisliga B Staffel 2",  9,  "02TM14A96G00000BVS5489BTVT4H6CF2-G"),
    ("Kreisliga B Staffel 3",  9,  "02TM14A9E400000AVS5489BTVT4H6CF2-G"),
    ("Kreisliga C Staffel 4", 10,  "02TS3NSVBC000009VS5489BUVVJ8R9DS-G"),
    ("Kreisliga C Staffel 5", 10,  "02TS3NSVMG00000AVS5489BUVVJ8R9DS-G"),
    ("Kreisliga C Staffel 6", 10,  "02TS3NSVUO000009VS5489BUVVJ8R9DS-G"),
    ("Kreisliga D Staffel 7", 11,  "02TS5BSF5S000009VS5489BUVVJ8R9DS-G"),
    ("Kreisliga D Staffel 8", 11,  "02TS5BSFBK000009VS5489BUVVJ8R9DS-G"),
    ("Kreisliga D Staffel 9", 11,  "02TS5BSFGG000009VS5489BUVVJ8R9DS-G"),
]

VERBAND = "FVM / Kreis Berg"

# fussball.de setzt in Vereinsnamen unsichtbare Trennzeichen, etwa
# "SG Hämmern /<U+200B> Heide". Die müssen vor der Anzeige raus.
_INVISIBLE = re.compile(r"[​‌‍­﻿]")


def _clean(fragment: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    text = _INVISIBLE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


class FussballDe:
    def __init__(self, cache_dir: Path, min_interval: float = 1.2,
                 ttl: float = 3 * 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.ttl = ttl
        self._last = 0.0

    def _get(self, url: str) -> str:
        key = hashlib.sha1(url.encode()).hexdigest()[:20]
        blob = self.cache_dir / f"fde_{key}.html"
        if blob.exists() and (time.time() - blob.stat().st_mtime) < self.ttl:
            return blob.read_text(encoding="utf-8")
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", "ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            self._last = time.monotonic()
            return ""
        self._last = time.monotonic()
        # Leere Antworten nicht zwischenspeichern: fussball.de liefert HTTP 200
        # mit 0 Bytes für Staffeln, die noch nicht veröffentlicht sind. Sobald
        # sie starten, soll der nächste Lauf sie sofort sehen.
        if text.strip():
            blob.write_text(text, encoding="utf-8")
        return text

    def current_staffel(self, anchor_id: str) -> str | None:
        """Staffel-ID der laufenden Saison über den Canonical-Link auflösen."""
        page = self._get(f"{BASE}/spieltagsuebersicht/x/-/staffel/{anchor_id}")
        found = re.search(r'<link rel="canonical" href="([^"]+)"', page)
        if not found:
            return None
        sid = re.search(r"/staffel/([0-9A-Z]+-[GC])", found.group(1))
        return sid.group(1) if sid else None

    def table(self, staffel_id: str) -> list[dict]:
        """Tabelle einer Staffel: Platz, Mannschaft, Sp, G, U, V, Tore, Pkt."""
        page = self._get(f"{BASE}/ajax.table/-/staffel/{staffel_id}")
        body = re.search(r"<tbody>(.*?)</tbody>", page, re.S)
        if not body:
            return []
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1), re.S):
            cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            cells = [c for c in cells if c]
            # Spalten laut <thead>: Pl. | Mannschaft | Sp. | G | U | V |
            #                       Torverhältnis | Tordifferenz | Punkte
            # Davor steht eine leere Wappenzelle, die oben herausfällt.
            if len(cells) < 9 or not re.match(r"^\d+\.$", cells[0]):
                continue
            goals = re.match(r"^(\d+)\s*:\s*(\d+)$", cells[6])
            if not goals:
                continue
            try:
                rows.append({
                    "name": cells[1],
                    "played": int(cells[2]),
                    "won": int(cells[3]),
                    "drawn": int(cells[4]),
                    "lost": int(cells[5]),
                    "goals_for": int(goals.group(1)),
                    "goals_against": int(goals.group(2)),
                    # Punkte stehen immer ganz rechts, auch wenn fussball.de
                    # weitere Spalten ergänzt.
                    "points": int(cells[-1]),
                })
            except ValueError:
                continue
        return rows


def fetch(cache_dir: Path, verbose: bool = True) -> list[dict]:
    """Liefert je Staffel {name, tier, verband, rows}. Leere Staffeln entfallen."""
    if not ENABLED:
        return []
    client = FussballDe(cache_dir)
    out = []
    for name, tier, anchor in OBERBERG:
        sid = client.current_staffel(anchor)
        rows = client.table(sid) if sid else []
        if rows:
            out.append({"name": name, "tier": tier, "verband": VERBAND,
                        "staffel": sid, "rows": rows})
        if verbose:
            print(f"  {'ok ' if rows else '-- '}fussball.de  "
                  f"{name:24.24s} {len(rows):4d} Mannschaften", file=sys.stderr)
    return out
