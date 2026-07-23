"""
Terms table.

Aurora identifies each academic term with a 6-digit code such as "202690"
(Fall 2026) or "202710" (Winter 2027). We use that code directly as our
primary key rather than inventing a surrogate one, since it's already a
stable, unique, externally-defined identifier and every downstream table
(sections) needs to reference it directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.section import Section


class Term(Base):
    __tablename__ = "terms"

    term_code: Mapped[str] = mapped_column(String(6), primary_key=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False)

    sections: Mapped[list["Section"]] = relationship(
        back_populates="term",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Term {self.term_code} {self.description!r}>"
