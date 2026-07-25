"""
Course Relationships table.

Generic pairwise relationship between two courses, covering three
distinct things the catalog expresses inline as prose/footnotes:

- EQUIVALENT       -- catalog's "Equiv To" (e.g. ENG 4800 Equiv To BIOE
                      2000, CIVL 2900, ECE 4720, MECH 2050 -- cross-listed
                      or interchangeable courses).
- MUTUALLY_EXCLUSIVE -- catalog's "Mutually Exclusive" / "may not be held
                      with" (e.g. ENG 2022 Mutually Exclusive with MECH
                      2112 -- credit for one disqualifies credit for the
                      other).
- SUBSTITUTE_FOR   -- footnote-style "X may be used in lieu of Y" (e.g.
                      MATH 1500/1230 in lieu of MATH 1510).

One table instead of three separate ones since all three are the same
shape (an unordered-in-practice pair of courses plus a type tag) and the
progress-calculation service needs to query "what's related to this
course, and how" the same way regardless of which type it's checking for.

course_id_a / course_id_b are stored in whatever order they were scraped
in -- callers checking a specific course must query both directions
(WHERE course_id_a = :x OR course_id_b = :x), since the relationship is
symmetric for all three types here (nothing in this schema currently
needs a directional relationship).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course


class CourseRelationship(Base):
    __tablename__ = "course_relationships"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('EQUIVALENT', 'MUTUALLY_EXCLUSIVE', 'SUBSTITUTE_FOR')",
            name="ck_course_relationships_type",
        ),
    )

    course_id_a: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), primary_key=True
    )
    course_id_b: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), primary_key=True
    )
    relationship_type: Mapped[str] = mapped_column(String(20), primary_key=True)

    course_a: Mapped["Course"] = relationship(foreign_keys=[course_id_a])
    course_b: Mapped["Course"] = relationship(foreign_keys=[course_id_b])

    def __repr__(self) -> str:
        return (
            f"<CourseRelationship {self.course_id_a} {self.relationship_type} "
            f"{self.course_id_b}>"
        )
