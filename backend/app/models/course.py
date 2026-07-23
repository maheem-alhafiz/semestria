"""
Courses table.

Represents the catalog-level concept of a course (e.g. "MECH 2202 -
Thermodynamics") independent of any term. The same course recurs across many
terms and has many sections per term, so `course_id` is a surrogate integer
PK and (subject, course_number) is enforced unique — that pair is Aurora's
natural key for "what course is this", separate from CRN which identifies
"which specific section, in which specific term".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String, UniqueConstraint
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

    sections: Mapped[list["Section"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Course {self.subject} {self.course_number} {self.title!r}>"
