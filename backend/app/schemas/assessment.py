"""
Schemas for the Assessments tab. Mirrors app.models.assessment; see that
module's docstring for the reasoning behind each table's shape.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict

AssessmentType = Literal["ASSIGNMENT", "QUIZ", "EXAM", "LAB", "PROJECT", "OTHER"]

# Fixed, standardized -- see GradeScaleCutoff's docstring on why only the
# percent-to-letter CUTOFF is student-editable, not this point value.
LETTER_GRADES = ("A+", "A", "B+", "B", "C+", "C", "D", "Fail")


class AssessmentCreate(BaseModel):
    term_code: str
    course_id: int
    title: str
    assessment_type: AssessmentType
    due_date: date | None = None
    due_time: time | None = None
    weight_percent: float | None = None
    notes: str | None = None


class AssessmentUpdate(BaseModel):
    """All fields optional -- backs the tab's inline edit as one PATCH
    rather than a route per field."""

    title: str | None = None
    assessment_type: AssessmentType | None = None
    due_date: date | None = None
    due_time: time | None = None
    weight_percent: float | None = None
    is_done: bool | None = None
    grade_received: float | None = None
    notes: str | None = None


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    course_id: int
    title: str
    assessment_type: AssessmentType
    due_date: date | None
    due_time: time | None
    weight_percent: float | None
    is_done: bool
    grade_received: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TopicEntryCreate(BaseModel):
    term_code: str
    course_id: int
    # Any date -- the backend snaps this to that week's Monday when
    # storing (see app.api.assessments). Lets the student enter "this
    # topic was Oct 14" without needing to compute a week number.
    entry_date: date
    topic_text: str


class TopicEntryUpdate(BaseModel):
    entry_date: date | None = None
    topic_text: str | None = None


class TopicEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    course_id: int
    week_start_date: date
    topic_text: str
    created_at: datetime
    updated_at: datetime


class TodoCreate(BaseModel):
    term_code: str
    course_id: int | None = None
    text: str
    due_date: date | None = None


class TodoUpdate(BaseModel):
    text: str | None = None
    is_done: bool | None = None
    due_date: date | None = None
    course_id: int | None = None


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    course_id: int | None
    text: str
    is_done: bool
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class GradeScaleCutoffItem(BaseModel):
    letter_grade: Literal["A+", "A", "B+", "B", "C+", "C", "D", "Fail"]
    min_percent: float


class GradeScaleUpdate(BaseModel):
    cutoffs: list[GradeScaleCutoffItem]


class AssessmentCourseRead(BaseModel):
    """
    One course shown on the Assessments tab for a given term -- either
    auto-pulled from AcademicRecord (a FINALIZED plan -- see
    app.models.assessment's docstring on why this deliberately does not
    read raw Plan/plan_items) or manually added via TrackedCourse.
    `source` tells the frontend whether to offer a "remove" action: a
    finalized course can't be removed here (it'd just reappear from
    AcademicRecord), only manually-added ones can. `credit_hours` is
    included for the term GPA estimate (see app.api.assessments).
    """

    course_id: int
    subject: str
    course_number: str
    title: str
    credit_hours: float
    source: Literal["finalized", "manual"]


class TrackedCourseCreate(BaseModel):
    term_code: str
    course_id: int
