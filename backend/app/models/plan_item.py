"""
Plan Items and Plan Item Sections tables.

A `PlanItem` is "this course is included in this Plan, for this specific
term" -- one row per (plan_id, term_code, course_id). Deliberately keyed
by term_code (not just plan_id + course_id): selecting the same course
into BOTH Fall 2026 and Winter 2027 within one Plan (the exact "messy
planning" scenario called out for the Planner UI) is two separate
PlanItem rows, not a conflict -- the duplicate-term-selection warning is
a UI-level notice, not a database constraint, since it's a legal state
the user explicitly wants to allow.

A `PlanItemSection` records which specific CRN was chosen to satisfy one
link_slot of that course (e.g. one row for the chosen lecture CRN, one
for the chosen lab CRN -- however many link_slot values that course's
LinkGroup has; the model doesn't assume exactly two). It FKs to
`sections` via the composite (term_code, crn) pair -- matching Section's
actual composite primary key -- rather than crn alone, for the same
cross-term-CRN-reuse reason documented on Section and MeetingTime.
`term_code` is stored redundantly here (rather than only inferred via
plan_item_id -> PlanItem.term_code) specifically so this composite FK to
`sections` can be declared directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.plan import Plan
    from app.models.section import Section
    from app.models.term import Term


class PlanItem(Base):
    __tablename__ = "plan_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "term_code", "course_id", name="uq_plan_items_plan_term_course"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    plan: Mapped["Plan"] = relationship(back_populates="items")
    term: Mapped["Term"] = relationship()
    course: Mapped["Course"] = relationship()
    chosen_sections: Mapped[list["PlanItemSection"]] = relationship(
        back_populates="plan_item",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PlanItem id={self.id} plan_id={self.plan_id} term={self.term_code} course_id={self.course_id}>"


class PlanItemSection(Base):
    __tablename__ = "plan_item_sections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["term_code", "crn"],
            ["sections.term_code", "sections.crn"],
            name="fk_plan_item_sections_term_code_crn_sections",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "plan_item_id", "term_code", "crn", name="uq_plan_item_sections_item_term_crn"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    plan_item_id: Mapped[int] = mapped_column(
        ForeignKey("plan_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Both required for the composite FK to sections -- see module
    # docstring. term_code will always match the parent PlanItem's
    # term_code; it's duplicated here (not just reachable via
    # plan_item_id -> PlanItem.term_code) because a FK constraint can only
    # reference columns that exist directly on this table.
    term_code: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    crn: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Snapshot of Section.link_slot at the time this choice was made,
    # purely for display/debugging (e.g. "which slot does this CRN fill?"
    # without an extra join) -- never used to enforce one-choice-per-slot;
    # that's application-level, same as link_slot itself is opaque
    # everywhere outside the importer/scheduler.
    link_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)

    plan_item: Mapped["PlanItem"] = relationship(back_populates="chosen_sections")
    section: Mapped["Section"] = relationship()

    def __repr__(self) -> str:
        return f"<PlanItemSection plan_item_id={self.plan_item_id} crn={self.crn} term={self.term_code}>"
