"""
Degree Programs table.

One row per major, per catalog year -- e.g. "Mechanical Engineering B.Sc.",
catalog_year "2025-2026". `catalog_year` is provenance/audit data (when
these requirements were last scraped, and a basis for diffing year over
year), NOT a pin on which rules a given student follows: a student who
started in 2024 still follows whichever catalog_year row is CURRENT for
their program, never an older one frozen at their entry year. The
progress-calculation service always queries "the latest catalog_year row
for this program," full stop -- there is no per-student catalog-year
assignment anywhere in this schema.

`degree_program_includes` is what lets shared requirements (the
Preliminary Engineering Program, common to every engineering major) live
as ONE DegreeProgram row referenced by many, rather than being copy-pasted
into every major's requirement tree. A student who picks "Computer
Engineering" gets Computer Engineering's own requirement_groups PLUS
whatever DegreeProgram rows it includes (Preliminary Engineering) --
see app.services.degree_progress (or wherever the progress calculator
ends up living) for how included programs get walked recursively.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.requirement_group import RequirementGroup


class DegreeProgram(Base):
    __tablename__ = "degree_programs"
    __table_args__ = (
        UniqueConstraint("name", "catalog_year", name="uq_degree_programs_name_catalog_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # "Mechanical Engineering B.Sc."
    faculty: Mapped[str] = mapped_column(String(255), nullable=False)  # "Price Faculty of Engineering"
    catalog_year: Mapped[str] = mapped_column(String(9), nullable=False)  # "2025-2026"

    # Where this was scraped from -- useful for re-scraping and for
    # tracing a weird requirement back to its source page during debugging.
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    requirement_groups: Mapped[list["RequirementGroup"]] = relationship(
        back_populates="degree_program",
        cascade="all, delete-orphan",
        # Only top-level groups (no parent) -- nested sub-groups are
        # reached via RequirementGroup.child_groups, not duplicated here.
        primaryjoin=(
            "and_(DegreeProgram.id == RequirementGroup.degree_program_id, "
            "RequirementGroup.parent_group_id.is_(None))"
        ),
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<DegreeProgram id={self.id} {self.name!r} ({self.catalog_year})>"


class DegreeProgramInclude(Base):
    """
    "Mechanical Engineering includes Preliminary Engineering Program" --
    a many-to-many self-reference on DegreeProgram. Deliberately its own
    association table (not a plain SQLAlchemy secondary=) so it can carry
    a real surrogate id for debugging/inspection and stay simple to query
    directly (e.g. "what does Mechanical Engineering include?") without
    going through ORM relationship magic.
    """

    __tablename__ = "degree_program_includes"
    __table_args__ = (
        UniqueConstraint(
            "degree_program_id",
            "includes_program_id",
            name="uq_degree_program_includes_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # The program whose progress calculation should also pull in
    # includes_program_id's requirement_groups (e.g. Mechanical
    # Engineering -> Preliminary Engineering Program).
    degree_program_id: Mapped[int] = mapped_column(
        ForeignKey("degree_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    includes_program_id: Mapped[int] = mapped_column(
        ForeignKey("degree_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<DegreeProgramInclude program={self.degree_program_id} "
            f"includes={self.includes_program_id}>"
        )
