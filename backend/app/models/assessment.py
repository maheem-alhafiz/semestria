"""
Assessments tab tables.

Three tables back this tab, all scoped by `owner_id` the same way Plan and
AcademicRecord are (see those modules' docstrings for the anonymous-visitor
reasoning) -- every query here must filter by the requesting visitor.

`Assessment` is the actual due-dated items -- assignments, quizzes, exams,
labs -- one row per item, always scoped to one (owner, term, course). It is
deliberately per-term, not a reusable template: a repeated course next year
gets a blank slate here, since due dates/weights change every offering even
when the course itself doesn't. `due_date` is nullable -- a student may add
an item before its date is announced; the UI buckets those as "unscheduled"
rather than forcing a placeholder date.

`WeeklyTopic` is a separate, lighter concept: free-text notes on what a
course covered in a given week, independent of any due date. One row per
(owner, term, course, week_start_date) -- `week_start_date` is always the
Monday of that week, so it lines up with however the calendar UI buckets
weeks (see Term.start_date on app.models.term for how "week 1" is derived).

`TrackedCourse` exists only for the MANUAL side of "auto-pull from Plan, but
also let me add a course by hand" -- see app.api.assessments for the read
path, which unions this table with the distinct course_ids already present
in the owner's plan_items for that term. A course that's only ever been
manually added here (never in a Plan) needs this row to appear on the
calendar at all, even before it has any Assessment/WeeklyTopic rows yet.
There's no "auto" counterpart row in this table by design -- Plans remain
the single source of truth for the auto side, so this feature never has to
sync itself against Plan changes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.term import Term


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "assessment_type IN ('ASSIGNMENT', 'QUIZ', 'EXAM', 'LAB', 'PROJECT', 'OTHER')",
            name="ck_assessments_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Nullable -- see module docstring on "unscheduled" items.
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Percent of final grade, e.g. 15.00. Nullable -- not every item is
    # weighted (a practice quiz, an ungraded lab check-in).
    weight_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Percent grade received once marked, e.g. 87.50. Nullable until graded.
    grade_received: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    term: Mapped["Term"] = relationship()
    course: Mapped["Course"] = relationship()

    def __repr__(self) -> str:
        return f"<Assessment id={self.id} {self.title!r} due={self.due_date}>"


class WeeklyTopic(Base):
    __tablename__ = "weekly_topics"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "term_code",
            "course_id",
            "week_start_date",
            name="uq_weekly_topics_owner_term_course_week",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Always the Monday of the week this note covers -- see module docstring.
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    topic_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    term: Mapped["Term"] = relationship()
    course: Mapped["Course"] = relationship()

    def __repr__(self) -> str:
        return f"<WeeklyTopic id={self.id} course_id={self.course_id} week={self.week_start_date}>"


class TrackedCourse(Base):
    """Manually-added courses only -- see module docstring."""

    __tablename__ = "assessment_tracked_courses"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "term_code", "course_id", name="uq_assessment_tracked_courses_owner_term_course"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    term: Mapped["Term"] = relationship()
    course: Mapped["Course"] = relationship()

    def __repr__(self) -> str:
        return f"<TrackedCourse owner={self.owner_id} term={self.term_code} course_id={self.course_id}>"
