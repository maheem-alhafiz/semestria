"""
Upsert layer: takes normalized data from mapper.py and writes it into
Postgres idempotently. Uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE`
so re-running the importer (e.g. from a nightly cron job) safely refreshes
seat counts / enrollment / meeting times on existing CRNs instead of
raising unique-constraint violations.
"""

from __future__ import annotations

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.importer.mapper import SectionData, decode_term_description
from app.models import MeetingTime, Section, Term


def upsert_term(session: Session, term_code: str) -> None:
    stmt = pg_insert(Term).values(
        term_code=term_code,
        description=decode_term_description(term_code),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["term_code"],
        set_={"description": stmt.excluded.description},
    )
    session.execute(stmt)


_UPSERT_COURSE_SQL = text(
    """
    INSERT INTO courses (subject, course_number, title, credit_hours)
    VALUES (
        :subject,
        :course_number,
        COALESCE(:title, :fallback_title),
        COALESCE(:credit_hours, 0)
    )
    ON CONFLICT (subject, course_number) DO UPDATE
    SET title = COALESCE(:title, courses.title),
        credit_hours = COALESCE(:credit_hours, courses.credit_hours)
    RETURNING course_id
    """
)


def upsert_course(session: Session, section: SectionData) -> int:
    """
    Upsert the catalog-level Course row and return its course_id.

    Not every Aurora record for the same course carries a title or credit
    hours (a lab section's record, for example, often has neither) -- we
    must not let a blank record clobber a good value a lecture record
    already established for that course.

    A plain `ON CONFLICT ... DO UPDATE SET x = COALESCE(excluded.x, table.x)`
    can't express this: Postgres's `excluded` pseudo-row reflects the value
    that *would* be written on a genuine insert (after any DB-side
    defaults), so by the time it's visible to COALESCE the "this was
    missing" signal is already gone. Instead we reference the *same* raw,
    possibly-NULL bind parameter twice: once coalesced against a fallback
    (used only if this is a brand-new course with nothing else known
    about it yet), and once coalesced against the table's current stored
    value (used on every subsequent update).
    """
    fallback_title = f"{section.subject} {section.course_number}"
    result = session.execute(
        _UPSERT_COURSE_SQL,
        {
            "subject": section.subject,
            "course_number": section.course_number,
            "title": section.course_title,
            "fallback_title": fallback_title,
            "credit_hours": section.credit_hours,
        },
    )
    return result.scalar_one()


def upsert_section(session: Session, section: SectionData, course_id: int) -> None:
    stmt = pg_insert(Section).values(
        crn=section.crn,
        course_id=course_id,
        term_code=section.term_code,
        section_number=section.section_number,
        link_identifier=section.link_identifier,
        is_linked=section.is_linked,
        seats_available=section.seats_available,
        max_enrollment=section.max_enrollment,
        enrollment=section.enrollment,
        instructor=section.instructor,
    )
    # Conflict target MUST be the composite (crn, term_code) key, matching
    # Section's actual primary key -- Banner reuses CRN numbers across
    # terms (see Section's docstring), so conflicting on crn alone would
    # silently overwrite a DIFFERENT term's row whenever its CRN recurred
    # (and previously also rewrote term_code itself via excluded.term_code,
    # which is exactly how that overwrite happened). term_code is part of
    # the conflict key now, so it can no longer appear in the update SET.
    stmt = stmt.on_conflict_do_update(
        index_elements=["crn", "term_code"],
        set_={
            "course_id": stmt.excluded.course_id,
            "section_number": stmt.excluded.section_number,
            "link_identifier": stmt.excluded.link_identifier,
            "is_linked": stmt.excluded.is_linked,
            "seats_available": stmt.excluded.seats_available,
            "max_enrollment": stmt.excluded.max_enrollment,
            "enrollment": stmt.excluded.enrollment,
            "instructor": stmt.excluded.instructor,
        },
    )
    session.execute(stmt)


def replace_meeting_times(session: Session, section: SectionData) -> None:
    """
    Meeting times have no stable natural key across import runs (Aurora
    gives us nothing to upsert on -- `id` is our own surrogate key). The
    safe idempotent strategy is delete-then-reinsert: wipe every existing
    MeetingTime row for this (crn, term_code), then bulk-insert the current
    set fresh. This correctly handles meetings being added, removed, or
    time-shifted between runs without ever accumulating duplicates.

    Filtering the delete by term_code as well as crn matters for the same
    reason Section's PK is composite: a bare `crn` filter would also wipe
    out a DIFFERENT term's meeting times whenever its CRN recurred.
    """
    session.execute(
        delete(MeetingTime).where(
            MeetingTime.crn == section.crn,
            MeetingTime.term_code == section.term_code,
        )
    )

    for mt in section.meeting_times:
        session.add(
            MeetingTime(
                crn=section.crn,
                term_code=section.term_code,
                meeting_type=mt.meeting_type,
                start_time=mt.start_time,
                end_time=mt.end_time,
                monday=mt.monday,
                tuesday=mt.tuesday,
                wednesday=mt.wednesday,
                thursday=mt.thursday,
                friday=mt.friday,
                saturday=mt.saturday,
                sunday=mt.sunday,
            )
        )
