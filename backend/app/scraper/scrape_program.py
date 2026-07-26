"""
Scrape one program page end to end.

Splits cleanly along the "needs a human" line established in
parse_program_page's docstring:

- Course-block data (prerequisites_text, corequisites_text, Equiv To,
  Mutually Exclusive) is reliable enough to apply STRAIGHT TO THE DB,
  no review step -- see apply_course_blocks.
- Requirement-group data (course lists -> ALL/ONE_OF/N_OF) is NOT
  reliable enough to auto-classify -- see dump_requirement_groups,
  which writes raw groups to a JSON file for a human to fill in `kind`,
  `courses_required`, `credit_hours_required` before
  app.scraper.import_requirements reads it back in.

Course-code resolution (matching a scraped "MECH 2112" string to a real
courses.course_id) depends entirely on the Aurora importer having already
run -- a code that doesn't resolve isn't necessarily wrong, it may just be
a course the current Aurora scrape didn't have (a discontinued "the former
X" course, a high-school prerequisite code, or a course from a term not
yet imported). Unresolved codes are logged and skipped, never guessed at.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, CourseRelationship
from app.scraper.catalog_client import CatalogClient
from app.scraper.parse_program_page import parse_course_blocks, parse_course_list_tables

logger = logging.getLogger(__name__)


def _resolve_course_id(db: Session, code: str, _cache: dict[str, int | None]) -> int | None:
    if code in _cache:
        return _cache[code]
    subject, number = code.split(" ", 1)
    course = db.execute(
        select(Course).where(Course.subject == subject, Course.course_number == number)
    ).scalar_one_or_none()
    course_id = course.course_id if course else None
    _cache[code] = course_id
    if course_id is None:
        logger.warning("Could not resolve course code %r to any existing course_id -- skipping "
                        "any prerequisite/relationship data that depends on it.", code)
    return course_id


def apply_course_blocks(db: Session, soup, _resolve_cache: dict[str, int | None] | None = None) -> dict[str, int]:
    """Writes prerequisites_text/corequisites_text and CourseRelationship
    rows directly. Returns counts for a quick summary log line."""
    _resolve_cache = _resolve_cache if _resolve_cache is not None else {}
    stats = {"courses_updated": 0, "relationships_written": 0, "unresolved_codes": 0}

    for block in parse_course_blocks(soup):
        code = f"{block.subject} {block.course_number}"
        course_id = _resolve_course_id(db, code, _resolve_cache)
        if course_id is None:
            stats["unresolved_codes"] += 1
            continue

        course = db.get(Course, course_id)
        course.description = block.description or None
        course.prerequisites_text = block.prerequisites_text
        course.corequisites_text = block.corequisites_text
        stats["courses_updated"] += 1

        for other_code, rel_type in [
            *[(c, "EQUIVALENT") for c in block.equiv_to],
            *[(c, "MUTUALLY_EXCLUSIVE") for c in block.mutually_exclusive],
        ]:
            other_id = _resolve_course_id(db, other_code, _resolve_cache)
            if other_id is None:
                stats["unresolved_codes"] += 1
                continue
            # Store with the lower course_id first so (a,b) and (b,a)
            # scraped from either course's own page collapse to the same
            # row instead of creating a duplicate reverse pair.
            a, b = sorted((course_id, other_id))
            existing = db.execute(
                select(CourseRelationship).where(
                    CourseRelationship.course_id_a == a,
                    CourseRelationship.course_id_b == b,
                    CourseRelationship.relationship_type == rel_type,
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    CourseRelationship(course_id_a=a, course_id_b=b, relationship_type=rel_type)
                )
                stats["relationships_written"] += 1

    db.commit()
    return stats


def dump_requirement_groups(soup, program_label: str, source_url: str, output_dir: Path) -> Path:
    """Writes raw (unclassified) requirement groups to a JSON file for
    manual review. Does NOT touch the database -- see module docstring."""
    groups = parse_course_list_tables(soup)

    payload = {
        "program_label": program_label,
        "source_url": source_url,
        "groups": [
            {
                "label": g.label,
                "rows": [asdict(r) for r in g.rows],
                "footnotes": g.footnotes,
                # Left for a human to fill in -- see import_requirements.
                "kind": None,
                "courses_required": None,
                "credit_hours_required": None,
                # Rows with no course_code match (e.g. "Any 1000 level
                # HIST course") aren't auto-converted to a pattern -- add
                # entries here manually as {"subject": "HIST" or null,
                # "level_min": 1000, "level_max": 1999} if needed.
                "patterns": [],
            }
            for g in groups
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    slug = program_label.lower().replace(",", "").replace(" ", "-").replace(".", "")
    out_path = output_dir / f"{slug}.raw.json"
    out_path.write_text(json.dumps(payload, indent=2))
    logger.info("Wrote %d raw requirement group(s) for %r to %s", len(groups), program_label, out_path)
    return out_path


def scrape_program(
    db: Session,
    client: CatalogClient,
    program_label: str,
    url: str,
    output_dir: Path,
) -> None:
    soup = client.get_soup(url)

    stats = apply_course_blocks(db, soup)
    logger.info(
        "%s: updated %d course(s), wrote %d relationship(s), %d unresolved code(s)",
        program_label, stats["courses_updated"], stats["relationships_written"],
        stats["unresolved_codes"],
    )

    dump_requirement_groups(soup, program_label, url, output_dir)
