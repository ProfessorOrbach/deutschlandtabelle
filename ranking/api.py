"""OpenLigaDB-Client mit Plattencache, Rate-Limit und 429-Backoff.

Die API drosselt aggressiv (HTTP 429), sobald mehrere Anfragen parallel oder
dicht hintereinander laufen. Deshalb: strikt sequentiell, Mindestabstand
zwischen Requests, exponentielles Backoff und ein Cache auf der Platte.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.openligadb.de"
USER_AGENT = "vereinsranking/0.1 (+https://github.com/openligadb)"


class OpenLigaDB:
    def __init__(self, cache_dir: Path, min_interval: float = 0.45,
                 fresh_ttl: float = 3 * 3600, archive_ttl: float = 30 * 86400):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.fresh_ttl = fresh_ttl
        self.archive_ttl = archive_ttl
        self._last_call = 0.0

    # -- HTTP -------------------------------------------------------------
    def _fetch(self, path: str):
        url = BASE + path
        delay = 2.0
        for attempt in range(5):
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(
                url, headers={"Accept": "application/json", "User-Agent": USER_AGENT}
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    self._last_call = time.monotonic()
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                self._last_call = time.monotonic()
                if exc.code == 429 and attempt < 4:
                    time.sleep(delay)
                    delay *= 2
                    continue
                if exc.code == 404:
                    return []
                raise
            except (urllib.error.URLError, TimeoutError):
                self._last_call = time.monotonic()
                if attempt < 4:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        return []

    # -- Cache ------------------------------------------------------------
    def _cached(self, path: str, ttl: float):
        key = hashlib.sha1(path.encode()).hexdigest()[:20]
        blob = self.cache_dir / f"{key}.json"
        if blob.exists() and (time.time() - blob.stat().st_mtime) < ttl:
            try:
                return json.loads(blob.read_text())
            except json.JSONDecodeError:
                pass
        data = self._fetch(path)
        blob.write_text(json.dumps(data))
        return data

    # -- Endpunkte --------------------------------------------------------
    def available_leagues(self):
        return self._cached("/getavailableleagues", self.fresh_ttl)

    def matches(self, shortcut: str, season: int, is_current: bool):
        path = f"/getmatchdata/{urllib.parse.quote(str(shortcut), safe='')}/{season}"
        data = self._cached(path, self.fresh_ttl if is_current else self.archive_ttl)
        return data if isinstance(data, list) else []
