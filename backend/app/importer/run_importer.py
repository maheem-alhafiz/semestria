"""
CLI entrypoint for the Aurora importer.

Usage:
    python -m app.importer.run_importer --terms 202690 202710
    python -m app.importer.run_importer --terms 202690 --verbose
    python -m app.importer.run_importer --all-terms

Intended to be invoked by a scheduled job (cron, systemd timer, etc.) on
whatever cadence seat counts need refreshing -- e.g. hourly during
registration weeks, daily otherwise. Every write is an idempotent upsert,
so running it twice in a row (or overlapping runs for different terms) is
always safe.

`--all-terms` discovers every term currently listed on Aurora's own
"Select a Term" dropdown (see AuroraClient.fetch_available_terms) and
imports all of them -- convenient for a scheduled job that shouldn't need
its command line updated every time a new term opens for registration.
`--terms` remains available as an explicit, manual fallback -- useful for
backfilling a specific historical term, or if the scraper ever needs to be
bypassed because Aurora's dropdown markup changed.
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.importer.aurora_client import AuroraTermScrapeError
from app.importer.importer import run_import


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import course data from Aurora into the planner database."
    )
    term_source = parser.add_mutually_exclusive_group(required=True)
    term_source.add_argument(
        "--terms",
        nargs="+",
        metavar="TERM_CODE",
        help="One or more Aurora term codes to import, e.g. --terms 202690 202710",
    )
    term_source.add_argument(
        "--all-terms",
        action="store_true",
        help="Discover and import every term currently listed on Aurora's term-selection dropdown.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging, including per-page fetch progress.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    try:
        run_import(None if args.all_terms else args.terms)
    except AuroraTermScrapeError as exc:
        # A discovery failure means we don't know what to import at all --
        # distinct from a single term failing mid-import (which run_import
        # already logs and continues past), so this is a hard stop with a
        # clear message rather than a generic traceback.
        logging.getLogger(__name__).error("Term discovery failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
