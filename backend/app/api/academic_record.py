from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import AcademicRecord, Course
from app.schemas.academic_record import (
    AcademicRecordCreate,
    AcademicRecordRead,
    AcademicRecordUpdate,
)

router = APIRouter(prefix="/academic-record", tags=["academic-record"])


@router.get("", response_model=list[AcademicRecordRead])
def list_academic_record(
    db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> list[AcademicRecord]:
    """Every row belonging to this visitor, oldest term first -- what the
    Degree Tracker groups by year/term to render."""
    stmt = (
        select(AcademicRecord)
        .where(AcademicRecord.owner_id == owner_id)
        .order_by(AcademicRecord.term_code)
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=AcademicRecordRead, status_code=201)
def add_past_course(
    payload: AcademicRecordCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> AcademicRecord:
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
    return record


@router.patch("/{record_id}", response_model=AcademicRecordRead)
def update_academic_record(
    record_id: int,
    payload: AcademicRecordUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> AcademicRecord:
    """
    The Degree Tracker's own inline edit -- fixing a grade typo or
    correcting an accidental finalize, independent of whatever Plan (if
    any) originally created this row via /plans/{id}/finalize.
    """
    record = db.execute(
        select(AcademicRecord).where(
            AcademicRecord.id == record_id, AcademicRecord.owner_id == owner_id
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Academic record {record_id} not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


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
