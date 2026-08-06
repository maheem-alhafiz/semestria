"""
Schemas for the Assessments tab. Mirrors app.models.assessment exactly;
see that module's docstring for the reasoning behind the three-table shape
(Assessment vs WeeklyTopic vs TrackedCourse, and why the auto/manual course
list is unioned live rather than synced into one table).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssessmentType = Literal["ASSIGNMENT", "QUIZ", "EXAM", "LAB", "PROJECT", "OTHER"]


class AssessmentCreate(BaseModel):
    term_code: str
    course_id: int
    title: str
    assessment_type: AssessmentType
    due_date: date | None = None
    weight_percent: float | None = None
    notes: str | None = None


class AssessmentUpdate(BaseModel):
    """All fields optional -- this backs the tab's inline edit (title,
    date, weight, done checkbox, grade) as one PATCH endpoint rather than
    a separate route per field."""

    title: str | None = None
    assessment_type: AssessmentType | None = None
    due_date: date | None = None
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
    weight_percent: float | None
    is_done: bool
    grade_received: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class WeeklyTopicUpsert(BaseModel):
    term_code: str
    course_id: int
    week_start_date: date
    topic_text: str


class WeeklyTopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    course_id: int
    week_start_date: date
    topic_text: str


class AssessmentCourseRead(BaseModel):
    """
    One course shown on the Assessments tab for a given term -- either
    auto-pulled from a Plan or manually added via TrackedCourse (see
    app.models.assessment's docstring). `source` tells the frontend
    whether to offer a "remove" action: a plan-sourced course can't be
    removed here (it'd just reappear from the Plan), only manually-added
    ones can.
    """

    course_id: int
    subject: str
    course_number: str
    title: str
    source: Literal["plan", "manual"]


class TrackedCourseCreate(BaseModel):
    term_code: str
    course_id: int
