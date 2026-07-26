"""
Program discovery.

CourseLeaf renders the same left-nav sidebar (every faculty, every
department, every degree program under it) on EVERY page of the catalog.
However, CourseLeaf collapses every sibling branch's subtree from the DOM 
unless it is the active page. This script now detects 'isparent' branches 
and fetches their pages to force the DOM to render the child leaves.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from app.scraper.catalog_client import CatalogClient

logger = logging.getLogger(__name__)

ENTRY_POINT_URL = "/undergraduate-studies/engineering/preliminary-engineering-program/"
FACULTY_LINK_TEXT = "Price Faculty of Engineering"

@dataclass
class DiscoveredProgram:
    label: str
    url: str

def _find_faculty_nav_root(soup: BeautifulSoup) -> Tag | None:
    for a in soup.find_all("a"):
        if a.get_text(strip=True) == FACULTY_LINK_TEXT:
            parent_li = a.find_parent("li")
            if parent_li is not None:
                nested_ul = parent_li.find("ul")
                if nested_ul is not None:
                    return nested_ul
    return None

def _walk(client: CatalogClient, ul: Tag, out: list[DiscoveredProgram], seen_urls: set[str]) -> None:
    for li in ul.find_all("li", recursive=False):
        classes = li.get("class") or []
        a = li.find("a", recursive=False)
        nested_ul = li.find("ul", recursive=False)

        if nested_ul is not None:
            _walk(client, nested_ul, out, seen_urls)
            continue

        if a is None:
            continue

        href = a.get("href", "")
        label = a.get_text(strip=True)

        if "isparent" in classes:
            # Children exist but aren't expanded in THIS fetch -- only
            # rendered on that branch's own page. Follow it.
            if not href or href == "#" or href in seen_urls:
                continue
            seen_urls.add(href)
            child_soup = client.get_soup(href)
            child_root = _find_faculty_nav_root(child_soup)
            if child_root is None:
                logger.warning("Could not re-locate faculty nav after following %r (%s) -- "
                               "treating as a leaf.", label, href)
                out.append(DiscoveredProgram(label=label, url=href))
                continue
            for candidate_li in child_root.find_all("li"):
                candidate_a = candidate_li.find("a", recursive=False)
                if candidate_a and candidate_a.get_text(strip=True) == label:
                    candidate_ul = candidate_li.find("ul", recursive=False)
                    if candidate_ul is not None:
                        _walk(client, candidate_ul, out, seen_urls)
                        break
            else:
                logger.warning("Followed %r (%s) but couldn't find its expanded "
                               "nav entry -- treating as a leaf.", label, href)
                out.append(DiscoveredProgram(label=label, url=href))
        elif href and href != "#":
            out.append(DiscoveredProgram(label=label, url=href))

def discover_engineering_programs(client: CatalogClient) -> list[DiscoveredProgram]:
    soup = client.get_soup(ENTRY_POINT_URL)
    nav_root = _find_faculty_nav_root(soup)
    if nav_root is None:
        raise RuntimeError(
            f"Could not find '{FACULTY_LINK_TEXT}' in the left-nav sidebar. "
            "The nav markup may have changed -- inspect the page source around "
            "that link text and adjust _find_faculty_nav_root accordingly."
        )

    discovered: list[DiscoveredProgram] = []
    _walk(client, nav_root, discovered, seen_urls={ENTRY_POINT_URL})
    
    logger.info("Discovered %d engineering program page(s): %s", len(discovered), [d.label for d in discovered])
    return discovered