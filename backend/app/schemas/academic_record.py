"""
Schemas for AcademicRecord -- the permanent transcript, independent of any
Plan. See app.models.academic_record's docstring for the full reasoning.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AcademicRecordCreate(BaseModel):
    """
    Manually adding a past course -- the existing "Add Past Course" flow,
    for courses taken before this system existed. Not plan-sourced, so
    `crn` is meaningful here (a single real section actually taken) in a
    way it isn't for plan-finalized rows -- see AcademicRecordRead's note.
    """

    term_code: str
    course_id: int
    crn: str | None = None
    grade: str | None = None


class AcademicRecordUpdate(BaseModel):
    """
    All fields optional. This is the Degree Tracker's own inline edit
    control -- fixing a grade typo or correcting an accidental finalize
    happens here, independent of whatever Plan originally created the row.
    """

    grade: str | None = None
    crn: str | None = None


class AcademicRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    course_id: int
    source_plan_id: int | None
    # NOTE: for rows created via Plan finalization, this is always NULL --
    # a course made up of multiple sections (lecture + lab) has no single
    # "the" CRN to display, and picking one arbitrarily would be
    # misleading. The full section breakdown for a plan-sourced row
    # remains queryable via source_plan_id -> plan_items ->
    # chosen_sections if ever needed. `crn` is populated only for rows
    # added through the manual "Add Past Course" flow, where there's
    # exactly one real CRN and no ambiguity.
    crn: str | None
    title_snapshot: str
    credit_hours_snapshot: float
    grade: str | None
    created_at: datetime
    updated_at: datetime
