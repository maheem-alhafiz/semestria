"""
Link Groups table.

A link group is one cluster of sections (within a single course+term) that
Aurora's registration system requires be considered together -- e.g. one
lecture plus its compatible lab options. This table exists so the
scheduler never has to interpret Aurora's `linkIdentifier` string itself:
the importer resolves the real grouping during ingestion (Phase 3) and
writes it here; the scheduler (Phase 4) only ever reads `Section.link_group_id`
/ `Section.link_slot` and groups by equality.

`external_code` stores the raw Aurora `linkIdentifier` value purely for
traceability and debugging (e.g. showing "why are these grouped?" in an
admin view). It must never be parsed, sliced, or otherwise interpreted
outside the importer -- treat it as an opaque string everywhere else.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.section import Section
    from app.models.term import Term


class LinkGroup(Base):
    __tablename__ = "link_groups"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "term_code", "external_code", name="uq_link_groups_course_term_code"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )
    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )

    # Raw Aurora linkIdentifier value, kept only for traceability/debugging.
    external_code: Mapped[str] = mapped_column(String(50), nullable=False)

    course: Mapped[Course] = relationship()
    term: Mapped[Term] = relationship()
    sections: Mapped[list[Section]] = relationship(back_populates="link_group")

    def __repr__(self) -> str:
        return f"<LinkGroup id={self.id} course_id={self.course_id} code={self.external_code!r}>"
