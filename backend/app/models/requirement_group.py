"""
Requirement Groups table, and its two membership mechanisms.

A RequirementGroup is one node in a degree program's requirement tree --
"Preliminary Engineering Program" (kind=ALL, 13 courses), "Written
English Requirement" (kind=ONE_OF, courses_required=1, membership mostly
via patterns like "any 1000-level HIST course"), "Technical Electives"
(kind=N_OF, courses_required=5, credit_hours_required=20 -- BOTH set at
once, since one specific TE being worth 6 credit hours instead of 4
means a pure course-count check isn't sufficient on its own).

`parent_group_id` makes groups nestable -- "Technical Electives" can
contain "Stream A" / "Stream B" sub-groups. A student's actual course
gets checked against LEAF groups (the ones with real
requirement_group_courses/requirement_group_patterns rows); the
progress-calculation service rolls satisfaction up from leaves to their
parent the same way it walks the tree down.

Two independent, non-exclusive ways a course can count toward a group:
- RequirementGroupCourse: explicit "this specific course_id counts here."
- RequirementGroupPattern: "any course matching subject+level range
  counts here" (e.g. "Any 1000 level HIST course" -- subject=HIST,
  level_min=1000, level_max=1999). subject NULL means any subject, for
  rules like "any course from Arts or Management at the 1000 level or
  above" (see PHIL 1290's note) -- though genuinely faculty-scoped
  patterns like that one are exactly the case flagged as not worth
  auto-modeling; ManualRequirementFulfillment exists for those instead
  of stretching this table to cover every possible scope.

A course satisfies a group if it matches EITHER mechanism -- checking
both, unioned, is the progress-calculation service's job; this schema
doesn't try to express "OR" as a stored relationship type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.degree_program import DegreeProgram


class RequirementGroup(Base):
    __tablename__ = "requirement_groups"
    __table_args__ = (
        CheckConstraint("kind IN ('ALL', 'ONE_OF', 'N_OF')", name="ck_requirement_groups_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    degree_program_id: Mapped[int] = mapped_column(
        ForeignKey("degree_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("requirement_groups.id", ondelete="CASCADE"), nullable=True, index=True
    )

    label: Mapped[str] = mapped_column(String(255), nullable=False)  # "Technical Electives"

    # 'ALL'    -- every course in this group is required (Preliminary's
    #             13-course list).
    # 'ONE_OF' -- exactly one of the group's courses/pattern-matches is
    #             required (courses_required is implicitly 1; ENG 2030 or
    #             ENG 2040; the Written English requirement).
    # 'N_OF'   -- courses_required (and/or credit_hours_required) of the
    #             group's members are required (Technical Electives: 5
    #             courses AND >=20 credit hours, both checked).
    kind: Mapped[str] = mapped_column(String(20), nullable=False)

    courses_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credit_hours_required: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # No back_populates here on purpose: DegreeProgram.requirement_groups
    # is a filtered (top-level-only) viewonly relationship, and pairing a
    # normal writable many-to-one against a filtered viewonly collection
    # confuses SQLAlchemy's unit-of-work about which side owns writes.
    # This side stays a plain, independent many-to-one.
    degree_program: Mapped["DegreeProgram"] = relationship()
    parent_group: Mapped["RequirementGroup | None"] = relationship(
        remote_side="RequirementGroup.id", back_populates="child_groups"
    )
    child_groups: Mapped[list["RequirementGroup"]] = relationship(
        back_populates="parent_group",
        cascade="all, delete-orphan",
    )
    explicit_courses: Mapped[list["RequirementGroupCourse"]] = relationship(
        back_populates="requirement_group",
        cascade="all, delete-orphan",
    )
    patterns: Mapped[list["RequirementGroupPattern"]] = relationship(
        back_populates="requirement_group",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RequirementGroup id={self.id} {self.label!r} kind={self.kind}>"


class RequirementGroupCourse(Base):
    """Explicit membership: "this course_id counts toward this group."""

    __tablename__ = "requirement_group_courses"

    requirement_group_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_groups.id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), primary_key=True
    )

    requirement_group: Mapped["RequirementGroup"] = relationship(back_populates="explicit_courses")
    course: Mapped["Course"] = relationship()

    def __repr__(self) -> str:
        return f"<RequirementGroupCourse group={self.requirement_group_id} course={self.course_id}>"


class RequirementGroupPattern(Base):
    """
    Pattern-based membership: "any course matching subject+level range
    counts toward this group" -- e.g. subject='HIST', level_min=1000,
    level_max=1999 for "Any 1000 level HIST course." subject=NULL means
    any subject (used sparingly -- see module docstring on why
    faculty-wide scopes like PHIL 1290's note are better served by
    ManualRequirementFulfillment than a maximally-broad pattern row here).
    """

    __tablename__ = "requirement_group_patterns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    requirement_group_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )

    subject: Mapped[str | None] = mapped_column(String(10), nullable=True)
    level_min: Mapped[int] = mapped_column(Integer, nullable=False)
    level_max: Mapped[int] = mapped_column(Integer, nullable=False)

    requirement_group: Mapped["RequirementGroup"] = relationship(back_populates="patterns")

    def __repr__(self) -> str:
        subj = self.subject or "ANY"
        return f"<RequirementGroupPattern group={self.requirement_group_id} {subj} {self.level_min}-{self.level_max}>"
