"""
Import orchestration: wires the Aurora HTTP client, the pure mapper, and
the upsert layer together into one full per-term import run. This is what
the CLI entrypoint (run_importer.py) and any future scheduled task call.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.importer.aurora_client import AuroraClient
from app.importer.link_resolver import resolve_link_groups
from app.importer.mapper import SectionData, map_section
from app.importer.upsert import replace_meeting_times, upsert_course, upsert_section, upsert_term

logger = logging.getLogger(__name__)


def import_term(session: Session, term_code: str, client: AuroraClient) -> int:
    """
    Import every section Aurora has for one term.

    Sections are buffered per (subject, course_number) before writing,
    because link-group resolution needs to see every section of a course
    at once to group them correctly -- it can't be decided one CRN at a
    time the way seat counts can.

    Commits once per term (not once per section) so a mid-run failure
    can't leave a term half-imported with an open transaction -- the
    recovery path is simply re-running the whole term, which is cheap and
    safe since every write here is an idempotent upsert.
    """
    upsert_term(session, term_code)

    sections_by_course_key: dict[tuple[str, str], list[SectionData]] = defaultdict(list)
    for raw in client.fetch_all_sections(term_code):
        section = map_section(raw)
        sections_by_course_key[(section.subject, section.course_number)].append(section)

    count = 0
    for course_sections in sections_by_course_key.values():
        course_id: int | None = None
        for section in course_sections:
            course_id = upsert_course(session, section)
            upsert_section(session, section, course_id)
            replace_meeting_times(session, section)
            count += 1

        assert course_id is not None  # course_sections is never empty here
        resolve_link_groups(session, course_id, term_code, course_sections)

    session.commit()
    logger.info("Term %s: imported %d sections", term_code, count)
    return count


def run_import(term_codes: list[str] | None = None) -> None:
    """
    Import several terms, sharing one DB session and one HTTP client across
    all of them.

    If `term_codes` is None, every term currently listed on Aurora's term
    dropdown is discovered via `AuroraClient.fetch_available_terms()` and
    imported -- this is what `--all-terms` uses. Passing an explicit list
    (the `--terms` flag) skips discovery entirely.
    """
    from app.core.database import (
        SessionLocal,  # local import: avoids a DB connection at module import time
    )

    with AuroraClient() as client, SessionLocal() as session:
        if term_codes is None:
            term_codes = [code for code, _description in client.fetch_available_terms()]

        for term_code in term_codes:
            try:
                import_term(session, term_code, client)
            except Exception:
                session.rollback()
                logger.exception(
                    "Failed to import term %s -- rolled back, continuing with remaining terms",
                    term_code,
                )
