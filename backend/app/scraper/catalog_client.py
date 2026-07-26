"""
Catalog HTTP client.

The academic calendar at catalog.umanitoba.ca runs on CourseLeaf (Leepfrog
Technologies) -- identifiable by its anchor-tab page structure
("index.html#degreerequirementstext" etc.) and its standard
`sc_courselist` table / `courseblock` div markup, both targeted directly
in app.scraper.parse_program_page.

Unlike Aurora (app.importer.aurora_client), this is a public, unauthenticated
static-HTML site with no session/CSRF dance required -- a plain GET with a
real User-Agent is enough. Rate-limited to one request every REQUEST_DELAY
seconds regardless of how many pages need scraping, since this is someone
else's public site and there's no reason to hit it any harder than a
human clicking through it would.
"""

from __future__ import annotations

import logging
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://catalog.umanitoba.ca"
REQUEST_DELAY_SECONDS = 1.5

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


class CatalogClient:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        self._last_request_time: float = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)

    def get_soup(self, url: str) -> BeautifulSoup:
        """Fetch a page and return it parsed. url may be absolute or a
        path relative to BASE_URL."""
        if not url.startswith("http"):
            url = BASE_URL.rstrip("/") + "/" + url.lstrip("/")

        self._throttle()
        logger.info("GET %s", url)
        response = self._session.get(url, timeout=30)
        self._last_request_time = time.monotonic()
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
