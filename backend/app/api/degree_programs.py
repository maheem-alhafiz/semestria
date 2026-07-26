"""
Degree Programs API.

Two routes:
- GET /degree-programs                    -- list, for the "pick your degree" selector
- GET /degree-programs/{id}/progress      -- one program's requirement groups,
                                              each annotated with the requesting
                                              visitor's completion progress

Progress computation (see _compute_progress) is deliberately done here in
Python on every request, not as a stored/cached value: it depends on the
requesting visitor's AcademicRecord, which changes far more often (every
grade entry, every finalized Plan) than the requirement structure itself,
and the dataset size here (one program's groups x one visitor's
transcript) is small enough that there's no real cost to recomputing it
fresh every time.

A course counts toward a group if EITHER:
  - it's in that group's explicit RequirementGroupCourse list, or
  - it matches one of the group's RequirementGroupPatterns (subject +
    level range), or
  - the visitor has a ManualRequirementFulfillment row linking one of
    their AcademicRecord rows directly to that group -- the escape hatch
    for prose-only rules (PHIL 1290's Arts/Management exception, Written
    English credit spillover) that automatic matching can't and
    shouldn't try to encode. See app.models.manual_fulfillment.

Every AcademicRecord row for the visitor counts as "completed" here
regardless of grade -- including NULL (in-progress/just-finalized,
ungraded) -- matching how AcademicRecord already works elsewhere in this
app (Plan finalization inserts rows with grade=NULL by design). This
means the Degree Tracker will show a course as satisfying a requirement
before it's actually been passed. That's a deliberate simplification for
this vertical slice, not an oversight -- excluding failing grades (or
distinguishing "planned" from "actually completed") is a real follow-up
worth doing once there's a UI reason to show that distinction, not
something to guess at the shape of before it's needed.
"""

from __future__ import annotations

import re
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import (
    AcademicRecord,
    Course,
    DegreeProgram,
    ManualRequirementFulfillment,
    RequirementGroup,
)
from app.schemas.degree_program import (
    DegreeProgramProgressRead,
    DegreeProgramSummary,
    RequirementGroupRead,
)

router = APIRouter(prefix="/degree-programs", tags=["degree-programs"])

_LEADING_DIGITS_RE = re.compile(r"\d+")


@router.get("", response_model=list[DegreeProgramSummary])
def list_degree_programs(db: Session = Depends(get_db)) -> list[DegreeProgram]:
    """Every scraped/imported program -- the 'pick your degree' selector
    reads this. No owner_id needed: this is shared reference data, not
    per-visitor data."""
    stmt = select(DegreeProgram).order_by(DegreeProgram.name)
    return db.execute(stmt).scalars().all()


def _course_level(course_number: str) -> int | None:
    match = _LEADING_DIGITS_RE.match(course_number)
    return int(match.group()) if match else None


def _course_matches_pattern(course: Course, subject: str | None, level_min: int, level_max: int) -> bool:
    if subject is not None and course.subject != subject:
        return False
    level = _course_level(course.course_number)
    return level is not None and level_min <= level <= level_max


def _compute_progress(
    groups: list[RequirementGroup],
    academic_records: list[AcademicRecord],
    manual_fulfillments: list[ManualRequirementFulfillment],
) -> list[RequirementGroupRead]:
    # group_id -> {academic_record_id -> credit_hours override}
    manual_by_group: dict[int, dict[int, float | None]] = defaultdict(dict)
    for mf in manual_fulfillments:
        manual_by_group[mf.requirement_group_id][mf.academic_record_id] = mf.credit_hours_applied

    results: list[RequirementGroupRead] = []
    for group in groups:
        explicit_course_ids = {rgc.course_id for rgc in group.explicit_courses}
        patterns = [(p.subject, p.level_min, p.level_max) for p in group.patterns]
        manual_records_for_group = manual_by_group.get(group.id, {})

        matched_course_ids: set[int] = set()
        matched_credit_hours = 0.0

        for record in academic_records:
            is_explicit = record.course_id in explicit_course_ids
            is_pattern_match = any(
                _course_matches_pattern(record.course, subj, lo, hi) for subj, lo, hi in patterns
            )
            is_manual = record.id in manual_records_for_group

            if is_explicit or is_pattern_match or is_manual:
                matched_course_ids.add(record.course_id)
                override = manual_records_for_group.get(record.id)
                matched_credit_hours += (
                    float(override) if override is not None else float(record.credit_hours_snapshot)
                )

        if group.kind == "ALL":
            is_satisfied = explicit_course_ids.issubset(matched_course_ids)
        elif group.kind == "ONE_OF":
            is_satisfied = len(matched_course_ids) >= 1
        else:  # "N_OF"
            count_ok = group.courses_required is None or len(matched_course_ids) >= group.courses_required
            hours_ok = (
                group.credit_hours_required is None
                or matched_credit_hours >= float(group.credit_hours_required)
            )
            is_satisfied = count_ok and hours_ok

        results.append(
            RequirementGroupRead(
                id=group.id,
                parent_group_id=group.parent_group_id,
                label=group.label,
                kind=group.kind,
                courses_required=group.courses_required,
                credit_hours_required=(
                    float(group.credit_hours_required) if group.credit_hours_required is not None else None
                ),
                sort_order=group.sort_order,
                courses=[rgc.course for rgc in group.explicit_courses],
                patterns=[
                    {"subject": p.subject, "level_min": p.level_min, "level_max": p.level_max}
                    for p in group.patterns
                ],
                completed_course_ids=sorted(matched_course_ids),
                completed_count=len(matched_course_ids),
                completed_credit_hours=matched_credit_hours,
                is_satisfied=is_satisfied,
            )
        )

    return results


@router.get("/{program_id}/progress", response_model=DegreeProgramProgressRead)
def get_degree_program_progress(
    program_id: int,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> dict:
    program = db.get(DegreeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail=f"Degree program {program_id} not found")

    groups = (
        db.execute(
            select(RequirementGroup)
            .where(RequirementGroup.degree_program_id == program_id)
            .options(
                selectinload(RequirementGroup.explicit_courses),
                selectinload(RequirementGroup.patterns),
            )
            .order_by(RequirementGroup.sort_order)
        )
        .scalars()
        .all()
    )

    academic_records = (
        db.execute(
            select(AcademicRecord)
            .where(AcademicRecord.owner_id == owner_id)
            .options(selectinload(AcademicRecord.course))
        )
        .scalars()
        .all()
    )

    manual_fulfillments = (
        db.execute(
            select(ManualRequirementFulfillment).where(
                ManualRequirementFulfillment.owner_id == owner_id
            )
        )
        .scalars()
        .all()
    )

    return {
        "id": program.id,
        "name": program.name,
        "faculty": program.faculty,
        "catalog_year": program.catalog_year,
        "groups": _compute_progress(groups, academic_records, manual_fulfillments),
    }
