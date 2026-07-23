"""
Sections table.

One row per (term_code, CRN) — Aurora's Course Reference Number is only
unique *within* a single term; Banner reuses the same CRN number for the
same recurring section year over year (e.g. MECH 2202 A01 is CRN 11543 in
every Fall term). The primary key is therefore the composite
(term_code, crn), not crn alone -- a bare `crn` PK meant importing more
than one term into this table silently overwrote earlier terms' rows
whenever a CRN number repeated across terms.

A single CRN can bundle multiple native meeting times (e.g. a MWF lecture +
a Wednesday tutorial, as in MECH 2202 A01); those live in the separate
MeetingTime table as a 1-to-many.

`link_identifier` + `is_linked` are Aurora's own raw fields, kept exactly as
originally specified for storage/display/debugging. They are intentionally
NOT what the scheduler uses to decide which sections must be registered
together -- UManitoba's `linkIdentifier` values don't reliably follow any
parseable convention (e.g. a lecture is not guaranteed to pair only with
similarly-numbered labs), so slicing that string would be guessing.

`link_group_id` + `link_slot` are the normalized, already-resolved
relationship: the importer (Phase 3) figures out which sections truly
belong together and writes the result here. The scheduler (Phase 4) only
ever groups by equality on these two columns -- it never interprets
Aurora's string format itself. See app.models.link_group.LinkGroup and
app.importer.link_resolver for how these get populated.

A few fields beyond the strict constraint list (max_enrollment, enrollment,
instructor) are included because they're already present in Aurora's
payload and are needed to render a useful section card in the UI — they
don't change the required PK/FK shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.link_group import LinkGroup
    from app.models.meeting_time import MeetingTime
    from app.models.term import Term


class Section(Base):
    __tablename__ = "sections"

    # Composite primary key: crn is only unique within a term (see module
    # docstring), so term_code must be part of the PK too. Marking both
    # columns primary_key=True is what tells SQLAlchemy's declarative
    # mapping to build a composite key -- this must match the DB-level
    # PRIMARY KEY constraint set by the corresponding Alembic migration,
    # or ORM-level identity tracking (session.get, relationship joins,
    # etc.) will disagree with what Postgres actually enforces.
    crn: Mapped[str] = mapped_column(String(10), primary_key=True)
    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    section_number: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "A01"

    # Raw Aurora fields -- opaque, storage/display/debug only. Never parsed.
    link_identifier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_linked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Normalized linking data, resolved by the importer. NULL means this
    # section is standalone (either never linked, or linked data was
    # malformed and the importer couldn't safely resolve it).
    link_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("link_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Opaque "required component" key within link_group_id -- e.g. two
    # sections sharing the same link_group_id AND link_slot are
    # interchangeable alternatives; different link_slot values within the
    # same group are separate components that must each be satisfied.
    # The scheduler groups on this by equality only; it never inspects
    # what the string actually represents.
    link_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)

    seats_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instructor: Mapped[str | None] = mapped_column(String(255), nullable=True)

    course: Mapped[Course] = relationship(back_populates="sections")
    term: Mapped[Term] = relationship(back_populates="sections")
    link_group: Mapped[LinkGroup | None] = relationship(back_populates="sections")
    meeting_times: Mapped[list[MeetingTime]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Section crn={self.crn} term={self.term_code} "
            f"{self.section_number} link_group_id={self.link_group_id}>"
        )
