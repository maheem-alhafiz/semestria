"""
Meeting Times table.

The core structural fix for Aurora's data quirk: a single section (CRN) can
have several distinct meeting blocks (e.g. MECH 2202 A01 = a MWF lecture
+ a Wednesday tutorial). Modeling this as its own table with a FK back to
`sections`, rather than flattening it onto the Section row, is what lets
the scheduler in Phase 4 treat "all meetings for this CRN" as one
unsplittable unit while still reasoning about each individual time block for
conflict detection.

`crn` alone is NOT enough to reference `sections`, for the same reason
`Section`'s own primary key is the composite `(crn, term_code)`: Banner
reuses CRN numbers across terms, so a bare `crn` FK would silently attach
this row to whichever term's section happens to share that CRN. `term_code`
is therefore stored here too, and the FK to `sections` is the composite
`(crn, term_code)` pair -- matching `Section`'s actual composite PK, not
just its `crn` column.

start_time/end_time are stored as SQL TIME (not the raw "HHMM" strings
Aurora returns) so the Phase 4 scheduler can compare times directly without
re-parsing strings on every check. The importer is responsible for the
"HHMM" -> time conversion. Both are nullable because online/async meeting
patterns have no clock time at all.
"""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKeyConstraint, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.section import Section


class MeetingTime(Base):
    __tablename__ = "meeting_times"
    __table_args__ = (
        ForeignKeyConstraint(
            ["crn", "term_code"],
            ["sections.crn", "sections.term_code"],
            name="fk_meeting_times_crn_term_code_sections",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crn: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    term_code: Mapped[str] = mapped_column(String(6), nullable=False, index=True)

    # e.g. "CLAS" (lecture), "TUT" (tutorial), "LAB", "EXAM"
    meeting_type: Mapped[str] = mapped_column(String(10), nullable=False)

    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    monday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    thursday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    friday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    saturday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sunday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    section: Mapped["Section"] = relationship(back_populates="meeting_times")

    def __repr__(self) -> str:
        return f"<MeetingTime crn={self.crn} {self.meeting_type} {self.start_time}-{self.end_time}>"
