"""
Import reviewed requirement groups into the database.

Usage:
    python -m app.scraper.import_requirements scraped_requirements/mechanical-engineering-bsc.raw.json \\
        --name "Mechanical Engineering B.Sc." \\
        --faculty "Price Faculty of Engineering" \\
        --catalog-year "2025-2026"

Expects the JSON file to have already been reviewed by hand: every group
must have `kind` set to one of ALL/ONE_OF/N_OF (see
app.scraper.parse_program_page's docstring for why this classification is
a manual step, not something the scraper decides on its own). A group
with `kind` still null is treated as not-yet-reviewed and skipped with a
warning, rather than guessed at or defaulted to something plausible.

Safe to re-run against the same catalog_year: matches the existing
DegreeProgram by (name, catalog_year) if present instead of creating a
duplicate, and replaces its requirement_groups wholesale (delete +
recreate) rather than trying to diff old vs new -- simplest correct way
to handle "the department changed a few things this year" without
hand-reconciling every group.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    Course,
    DegreeProgram,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupPattern,
)

logger = logging.getLogger(__name__)

_VALID_KINDS = {"ALL", "ONE_OF", "N_OF"}


def _get_or_create_program(
    db: Session, name: str, faculty: str, catalog_year: str, source_url: str
) -> DegreeProgram:
    existing = db.execute(
        select(DegreeProgram).where(
            DegreeProgram.name == name, DegreeProgram.catalog_year == catalog_year
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Wholesale replace -- see module docstring.
        for group in list(existing.requirement_groups):
            db.delete(group)
        db.flush()
        existing.source_url = source_url
        return existing

    program = DegreeProgram(
        name=name, faculty=faculty, catalog_year=catalog_year, source_url=source_url
    )
    db.add(program)
    db.flush()
    return program


def _resolve_course_id(db: Session, code: str, cache: dict[str, int | None]) -> int | None:
    if code in cache:
        return cache[code]
    subject, number = code.split(" ", 1)
    course = db.execute(
        select(Course).where(Course.subject == subject, Course.course_number == number)
    ).scalar_one_or_none()
    cache[code] = course.course_id if course else None
    return cache[code]


def import_reviewed_file(
    db: Session, path: Path, program_name: str, faculty: str, catalog_year: str
) -> None:
    payload = json.loads(path.read_text())
    source_url = payload.get("source_url", "")

    program = _get_or_create_program(db, program_name, faculty, catalog_year, source_url)

    course_id_cache: dict[str, int | None] = {}
    skipped_groups = 0
    created_groups = 0
    unresolved_courses: set[str] = set()

    for order, group_data in enumerate(payload["groups"]):
        kind = group_data.get("kind")
        if kind not in _VALID_KINDS:
            logger.warning(
                "Group %r has no valid `kind` set (got %r) -- skipping. "
                "Review the JSON file and set kind to one of %s before re-running.",
                group_data["label"], kind, sorted(_VALID_KINDS),
            )
            skipped_groups += 1
            continue

        group = RequirementGroup(
            degree_program_id=program.id,
            label=group_data["label"],
            kind=kind,
            courses_required=group_data.get("courses_required"),
            credit_hours_required=group_data.get("credit_hours_required"),
            sort_order=order,
        )
        db.add(group)
        db.flush()
        created_groups += 1

        for row in group_data["rows"]:
            code = row.get("course_code")
            if not code:
                continue  # unmatched text row -- only patterns can cover this, not a course row
            course_id = _resolve_course_id(db, code, course_id_cache)
            if course_id is None:
                unresolved_courses.add(code)
                continue
            db.add(RequirementGroupCourse(requirement_group_id=group.id, course_id=course_id))

        for pattern in group_data.get("patterns", []):
            db.add(
                RequirementGroupPattern(
                    requirement_group_id=group.id,
                    subject=pattern.get("subject"),
                    level_min=pattern["level_min"],
                    level_max=pattern["level_max"],
                )
            )

    db.commit()

    logger.info(
        "%s (%s): created %d group(s), skipped %d unreviewed group(s), %d unresolved course code(s)%s",
        program_name, catalog_year, created_groups, skipped_groups, len(unresolved_courses),
        f" -- {sorted(unresolved_courses)}" if unresolved_courses else "",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a reviewed requirement-group JSON file into the database."
    )
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--name", required=True, help='e.g. "Mechanical Engineering B.Sc."')
    parser.add_argument("--faculty", required=True, help='e.g. "Price Faculty of Engineering"')
    parser.add_argument("--catalog-year", required=True, help='e.g. "2025-2026"')
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    db = SessionLocal()
    try:
        import_reviewed_file(db, args.json_file, args.name, args.faculty, args.catalog_year)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
