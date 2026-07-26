"""
Manual Requirement Fulfillments table.

An escape hatch, by design: rather than trying to encode genuinely
faculty-wide, prose-only rules -- "any course from Arts or Management at
the 1000 level or above, except ARTS 1110" (PHIL 1290's note), or a
6-credit-hour Written English course's extra 3 credits spilling over into
a *different* requirement -- as ever-more-special-cased schema, a student
just links one of their own AcademicRecord rows directly to the
RequirementGroup it satisfies. This is always additional to (never
required to override) automatic matching via
RequirementGroupCourse/RequirementGroupPattern: the progress-calculation
service treats a group as satisfied by EITHER an automatic match OR a
manual fulfillment claim, whichever applies. Automatic matching doesn't
need to be taught about every exception for this to work correctly.

`credit_hours_applied` is nullable and, when set, can be LESS than the
course's full credit_hours -- this is what the Written English spillover
case needs (a 6-credit course applying 3 credits here and the remaining 3
elsewhere via a second ManualRequirementFulfillment row against a
different requirement_group_id, both pointing at the same
academic_record_id). NULL means "the whole course counts here," which
covers the ordinary case (PHIL 1290 exception, etc.) without requiring
the student to do arithmetic for the common case.

owner_id isolates rows per-visitor, same as Plan/AcademicRecord (see
app.core.visitor) -- redundant with academic_record_id's own owner_id in
principle, but kept here directly (not just inferred via a join) so this
table's own uniqueness constraint and row-level queries don't require
joining back to academic_record first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.academic_record import AcademicRecord
    from app.models.requirement_group import RequirementGroup


class ManualRequirementFulfillment(Base):
    __tablename__ = "manual_requirement_fulfillments"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "requirement_group_id",
            "academic_record_id",
            name="uq_manual_fulfillment_owner_group_record",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    requirement_group_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_record_id: Mapped[int] = mapped_column(
        ForeignKey("academic_record.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # If a student manually assigns a course to REPLACE a specific mandatory course
    # (e.g., taking FIN 1010 instead of PHIL 1290), this stores the ID of the course 
    # being replaced. NULL means it's just a general addition to the group.
    replaced_course_id: Mapped[int | None] = mapped_column(nullable=True)

    # NULL = the whole course counts toward this group. Set explicitly
    # only for split-credit cases (see module docstring).
    credit_hours_applied: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)

    requirement_group: Mapped["RequirementGroup"] = relationship()
    academic_record: Mapped["AcademicRecord"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<ManualRequirementFulfillment owner={self.owner_id[:8]}... "
            f"group={self.requirement_group_id} record={self.academic_record_id}>"
        )
