"""
Terms table.

Aurora identifies each academic term with a 6-digit code such as "202690"
(Fall 2026) or "202710" (Winter 2027). We use that code directly as our
primary key rather than inventing a surrogate one, since it's already a
stable, unique, externally-defined identifier and every downstream table
(sections) needs to reference it directly.

`start_date` / `end_date` are DERIVED, not scraped directly from Aurora --
Aurora has no single "term starts on X" field, only per-section meeting-time
date ranges (see MeetingTime's docstring on why those are per-meeting, not
per-term -- e.g. CHEM 1126 lists sparse individual lab dates instead of a
recurring weekly range). `app.importer.upsert.refresh_term_date_range`
computes these as MIN(start_date)/MAX(end_date) across every MeetingTime in
the term at the end of each import run and caches the result here, so
consumers (the Assessments tab's week navigation) don't re-aggregate on
every request. Both nullable: a term with no imported sections yet (or
whose sections are all-TBA with no dates) has nothing to derive from.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.section import Section


class Term(Base):
    __tablename__ = "terms"

    term_code: Mapped[str] = mapped_column(String(6), primary_key=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    sections: Mapped[list["Section"]] = relationship(
        back_populates="term",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Term {self.term_code} {self.description!r}>"
