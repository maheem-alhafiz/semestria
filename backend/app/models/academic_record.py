"""
Academic Record table.

The permanent record of courses actually taken (or planned-and-finalized),
independent of any single Plan -- this is what solves the overwrite problem:
"Mark as Final" on a Plan upserts that Plan's courses into THIS table
(insert new term/course rows, update matching ones), it never replaces the
table wholesale. Finalizing a later Plan (e.g. Fall 2027/Winter 2028) adds
rows here; it does not touch Fall 2026/Winter 2027's rows from an earlier
finalize. The Degree Tracker tab reads directly from this table and has its
own independent edit/delete controls, so a grade typo or an accidental
finalize is fixable here without needing to touch the source Plan at all.

`owner_id` ties every row to one anonymous visitor (see app.core.visitor)
-- every query against this table must filter by the requesting visitor's
owner_id. Unlike Plan, this table has no public/shared-link exception --
a transcript is never meant to be publicly viewable by URL.

Keyed by (owner_id, term_code, course_id) via a unique constraint (with a
surrogate `id` PK, matching LinkGroup's convention) rather than a
composite PK, specifically so a single stable `id` exists for direct
REST-style edit/delete endpoints (PATCH/DELETE /academic-record/{id})
independent of the Plan that may have originally created the row.
owner_id is part of the uniqueness check (not just an index) because two
different visitors independently taking the same course in the same term
is completely normal and must not collide.

`source_plan_id` is nullable and ON DELETE SET NULL: a row created by
"Mark as Final" remembers which Plan finalized it (useful for "where did
this come from?" display), but deleting that Plan later must NOT cascade
into deleting the permanent record -- the whole point of this table is
that it survives independently of any Plan.

`crn` is a plain nullable string, NOT a foreign key to `sections`: a
manually-entered past course (the existing "add past course" flow in
App.jsx, for courses taken before this system existed) has no real CRN at
all, and a CRN from a re-scraped older term could in principle no longer
exist in `sections` after a refresh. `credit_hours` and `title` are
snapshotted here (copied at insert time, not joined live from `courses`)
so a later catalog change (credit hours revised, title updated) doesn't
retroactively rewrite what a past semester's transcript said.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.plan import Plan
    from app.models.term import Term


class AcademicRecord(Base):
    __tablename__ = "academic_record"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "term_code", "course_id", name="uq_academic_record_owner_term_course"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Cookie-derived anonymous visitor id (see app.core.visitor). Part of
    # the uniqueness constraint, not just an index -- see module
    # docstring for why (two visitors taking the same course in the same
    # term is normal, not a collision).
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Not a FK -- see module docstring (manually-entered past courses have
    # no real CRN; a re-scraped term's CRN could later disappear).
    crn: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Snapshots, not live joins -- see module docstring.
    title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_hours_snapshot: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)

    # NULL = in progress / not yet graded (e.g. a just-finalized future
    # term). Populated later via the Degree Tracker's own edit control.
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    term: Mapped["Term"] = relationship()
    course: Mapped["Course"] = relationship()
    source_plan: Mapped["Plan | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<AcademicRecord id={self.id} term={self.term_code} course_id={self.course_id} "
            f"grade={self.grade!r}>"
        )
