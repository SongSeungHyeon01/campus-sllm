"""Polite HTTP client for u1.ac.kr: fixed delay between requests, retries, raw HTML cache."""
import re
import time
from pathlib import Path

import requests

BASE_URL = "https://www.u1.ac.kr"
USER_AGENT = "AskCampusBot/0.1 (U1 University capstone project)"


def absolute(url: str) -> str:
    return url if url.startswith("http") else BASE_URL + url


class Fetcher:
    def __init__(self, delay: float = 1.0, timeout: float = 20, retries: int = 2,
                 raw_dir: Path | None = None):
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.raw_dir = raw_dir
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last = 0.0

    def get(self, url: str) -> str:
        url = absolute(url)
        for attempt in range(self.retries + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = self.session.get(url, timeout=self.timeout)
                self._last = time.monotonic()
                resp.raise_for_status()
                html = resp.content.decode("utf-8", errors="replace")
                self._save_raw(url, html)
                return html
            except requests.RequestException:
                self._last = time.monotonic()
                if attempt == self.retries:
                    raise
                time.sleep(2 ** attempt)
        raise AssertionError("unreachable")

    def _save_raw(self, url: str, html: str) -> None:
        if self.raw_dir is None:
            return
        name = re.sub(r"[^0-9A-Za-z._-]+", "_", url.removeprefix(BASE_URL)).strip("_")
        path = self.raw_dir / f"{name[:150]}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
