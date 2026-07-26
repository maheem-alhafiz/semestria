"""
CLI entrypoint for the catalog scraper.

Usage:
    python -m app.scraper.run_scrape --output-dir ./scraped_requirements
    python -m app.scraper.run_scrape --output-dir ./scraped_requirements --verbose

Discovers every engineering degree-program page from the catalog's own
nav sidebar (see app.scraper.discover_programs -- nothing here hardcodes
a program list, so a new major appearing in the catalog gets picked up
automatically on the next run), then for each one:

  - applies course-level data (prerequisites_text, corequisites_text,
    course_relationships) straight to the database, no review needed
  - writes that program's raw requirement groups to
    {output_dir}/{program-slug}.raw.json for manual classification

After reviewing/editing the JSON files (filling in `kind`,
`courses_required`, `credit_hours_required` per group -- see
app.scraper.parse_program_page's docstring for why this step isn't
automated), run app.scraper.import_requirements against each file to
actually create DegreeProgram/RequirementGroup rows.

Every write here is safe to re-run: apply_course_blocks checks for an
existing CourseRelationship row before inserting, and the JSON dump
simply overwrites the previous file for that program -- re-scraping
after the catalog updates for a new year doesn't create duplicates.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.scraper.catalog_client import CatalogClient
from app.scraper.discover_programs import discover_engineering_programs
from app.scraper.scrape_program import scrape_program


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape UManitoba engineering program requirements from the catalog."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("scraped_requirements"),
        help="Where to write raw (unclassified) requirement-group JSON files.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    client = CatalogClient()
    db = SessionLocal()
    try:
        programs = discover_engineering_programs(client)
        for program in programs:
            try:
                scrape_program(db, client, program.label, program.url, args.output_dir)
            except Exception:
                logger.exception("Failed to scrape %r (%s) -- continuing with the rest", program.label, program.url)
    finally:
        db.close()

    logger.info(
        "Done. Review the raw JSON files in %s, then run app.scraper.import_requirements "
        "against each reviewed file.",
        args.output_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
