"""
Schemas for the Degree Tracker's requirements view.

`RequirementGroupRead` carries both the static shape (label, kind,
courses, patterns -- straight from the DB) and computed per-owner
progress fields (completed_course_ids, completed_count,
completed_credit_hours, is_satisfied). Progress is computed fresh on
every request in app.api.degree_programs -- nothing here is cached or
stored, since it depends on the requesting visitor's own AcademicRecord,
which changes far more often than the requirement structure itself.

Groups are returned as a FLAT list (each carrying its own
`parent_group_id`), not a nested tree. For Mechanical Engineering's
current MVP import every group is top-level (no nesting), so a flat
list is simplest for the frontend to render directly; `parent_group_id`
is still included so a future nested-stream import (Aerospace/Materials/
etc. sub-groups) doesn't require an API shape change -- the frontend can
build a tree from the flat list via parent_group_id whenever that data
actually shows up.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.course import CourseRead


class RequirementGroupPatternRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject: str | None
    level_min: int
    level_max: int


class RequirementGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_group_id: int | None
    label: str
    kind: str  # "ALL" | "ONE_OF" | "N_OF"
    courses_required: int | None
    credit_hours_required: float | None
    sort_order: int

    courses: list[CourseRead]
    patterns: list[RequirementGroupPatternRead]

    # Computed against the requesting visitor's AcademicRecord -- see
    # module docstring. NOT stored; recomputed every request.
    completed_course_ids: list[int]
    completed_count: int
    completed_credit_hours: float
    is_satisfied: bool


class DegreeProgramSummary(BaseModel):
    """Lightweight -- for the initial 'pick your degree' selector."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    faculty: str
    catalog_year: str


class DegreeProgramProgressRead(BaseModel):
    """Full detail with computed progress -- what the Degree Tracker tab
    actually renders."""

    id: int
    name: str
    faculty: str
    catalog_year: str
    groups: list[RequirementGroupRead]
