"""
Courses table.

Represents the catalog-level concept of a course (e.g. "MECH 2202 -
Thermodynamics") independent of any term. The same course recurs across many
terms and has many sections per term, so `course_id` is a surrogate integer
PK and (subject, course_number) is enforced unique -- that pair is Aurora's
natural key for "what course is this", separate from CRN which identifies
"which specific section, in which specific term".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.section import Section


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("subject", "course_number", name="uq_courses_subject_course_number"),
    )

    course_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    course_number: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Numeric, not Integer/Float: Aurora has fractional/variable credit courses
    # (e.g. 1.5, 3.0, 6.0), and Numeric avoids floating-point rounding surprises.
    credit_hours: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)

    # Raw prose exactly as scraped from the catalog's course description
    # page, e.g. "Pre-Calculus Mathematics 40S (60%) (or one of MATH 0401,
    # ... ) and Physics 40S (60%) (or ...)". This is the reliable tier --
    # always shown to students as-is, never re-derived. It routinely
    # mixes real Aurora courses with high-school course codes, grade
    # thresholds, and "the former X" references that don't correspond to
    # any current course_id, which is exactly why this is free text and
    # not exclusively a set of course_id FKs. See CoursePrerequisite for
    # the separate, best-effort STRUCTURED tier (only populated for the
    # subset of cases confidently parseable into real course references).
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisites_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    corequisites_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    sections: Mapped[list["Section"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Course {self.subject} {self.course_number} {self.title!r}>"
