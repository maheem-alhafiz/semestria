from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import AcademicRecord, Course
from app.schemas.academic_record import (
    AcademicRecordCreate,
    AcademicRecordRead,
    AcademicRecordUpdate,
)

router = APIRouter(prefix="/academic-record", tags=["academic-record"])


def _to_read(record: AcademicRecord) -> AcademicRecordRead:
    """
    Builds the response schema explicitly rather than relying on
    from_attributes' auto-conversion -- subject/course_number live on
    record.course, not as flat columns on AcademicRecord itself, so a
    plain ORM-to-schema pass can't pick them up on its own. Assumes
    record.course is already loaded (selectinload in every query below)
    -- accessing an unloaded relationship here would trigger a surprise
    lazy-load per row.
    """
    return AcademicRecordRead(
        id=record.id,
        term_code=record.term_code,
        course_id=record.course_id,
        subject=record.course.subject,
        course_number=record.course.course_number,
        source_plan_id=record.source_plan_id,
        crn=record.crn,
        title_snapshot=record.title_snapshot,
        credit_hours_snapshot=float(record.credit_hours_snapshot),
        grade=record.grade,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=list[AcademicRecordRead])
def list_academic_record(
    db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> list[AcademicRecordRead]:
    """Every row belonging to this visitor, oldest term first -- what the
    Degree Tracker groups by year/term to render."""
    stmt = (
        select(AcademicRecord)
        .where(AcademicRecord.owner_id == owner_id)
        .options(selectinload(AcademicRecord.course))
        .order_by(AcademicRecord.term_code)
    )
    records = db.execute(stmt).scalars().all()
    return [_to_read(r) for r in records]


@router.post("", response_model=AcademicRecordRead, status_code=201)
def add_past_course(
    payload: AcademicRecordCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> AcademicRecordRead:
    """
    Manually add a past course -- for courses taken before this system
    existed (the existing "Add Past Course" flow). NOT plan-sourced:
    source_plan_id stays NULL, and unlike a plan-finalized row, `crn` is
    meaningful here since there's exactly one real section being recorded.
    """
    course = db.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Course {payload.course_id} not found")

    existing = db.execute(
        select(AcademicRecord).where(
            AcademicRecord.owner_id == owner_id,
            AcademicRecord.term_code == payload.term_code,
            AcademicRecord.course_id == payload.course_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{course.subject} {course.course_number} already has a record for term "
                f"{payload.term_code} (id={existing.id}) -- edit that entry instead of "
                "creating a duplicate."
            ),
        )

    record = AcademicRecord(
        owner_id=owner_id,
        term_code=payload.term_code,
        course_id=payload.course_id,
        crn=payload.crn,
        grade=payload.grade,
        title_snapshot=course.title,
        credit_hours_snapshot=course.credit_hours,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record.course = course  # already have it in hand, skip a re-fetch/lazy-load
    return _to_read(record)


@router.patch("/{record_id}", response_model=AcademicRecordRead)
def update_academic_record(
    record_id: int,
    payload: AcademicRecordUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> AcademicRecordRead:
    """
    The Degree Tracker's own inline edit -- fixing a grade typo or
    correcting an accidental finalize, independent of whatever Plan (if
    any) originally created this row via /plans/{id}/finalize.
    """
    record = db.execute(
        select(AcademicRecord)
        .where(AcademicRecord.id == record_id, AcademicRecord.owner_id == owner_id)
        .options(selectinload(AcademicRecord.course))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Academic record {record_id} not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return _to_read(record)


@router.delete("/{record_id}", status_code=204, response_model=None)
def delete_academic_record(
    record_id: int, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> None:
    """
    Directly removes one row -- e.g. a plan finalized by mistake. This is
    exactly the "no way to delete entries" gap flagged for the old
    Semestria design; AcademicRecord's own id (independent of any Plan)
    is what makes this endpoint possible at all.
    """
    record = db.execute(
        select(AcademicRecord).where(
            AcademicRecord.id == record_id, AcademicRecord.owner_id == owner_id
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Academic record {record_id} not found")
    db.delete(record)
    db.commit()
