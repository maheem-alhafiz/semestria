"""
Assessments tab tables.

Six tables back this tab, all scoped by `owner_id` the same way Plan and
AcademicRecord are -- every query here must filter by the requesting
visitor. See app.api.assessments for the read paths.

`Assessment` is the actual due-dated items -- assignments, quizzes, exams,
labs -- one row per item, always scoped to one (owner, term, course). It is
deliberately per-term, not a reusable template: a repeated course next year
gets a blank slate here, since due dates/weights change every offering even
when the course itself doesn't. `due_date` is nullable -- a student may add
an item before its date is announced; the UI buckets those as "unscheduled"
rather than forcing a placeholder date. `due_time` is separately nullable
-- a date can be known before a specific time is (e.g. "due sometime
Friday" becomes "due 11:59 PM Friday" once the syllabus is more specific).

`WeeklyTopic` is a log entry, NOT a singleton per week: what a course
covered, tagged with the Monday of the week it happened. Originally this
was one upsertable row per (owner, term, course, week) with an editable
textbox per week visible on the calendar -- that shape had two real
problems: the frontend input didn't reset when the viewed week changed
(a stale value from one week could silently overwrite a different week's
saved note on blur), and more fundamentally it forced entries to be
written one week at a time by navigating the calendar, when a student
copying an entire syllabus's weekly topic list wants to log everything in
one sitting. So this is now an append-only log: multiple entries per
(owner, term, course, week) are allowed, added/edited/deleted individually
like Assessment rows, with `week_start_date` derived (snapped to that
week's Monday) from whatever date the student enters -- see
app.api.assessments's topic endpoints for the snapping logic.

`TrackedCourse` exists only for the MANUAL side of "auto-pull from my
finalized schedule, but also let me add a course by hand." The auto side
reads from `AcademicRecord` (the Degree Tracker's finalized transcript
table, populated only by "Mark as Final" -- NOT from Plan/plan_items,
which are sandboxed what-ifs and would otherwise clog this tab with every
throwaway plan a student experiments with). A course only ever added here
manually (never finalized) needs this row to appear on the calendar at
all, even before it has any Assessment/WeeklyTopic rows yet.

`Todo` is a personal task list, deliberately separate from Assessment:
no weight, no grade, nothing graded about it -- just a note like "finish
last page of chapter 5." `course_id` is nullable because a todo doesn't
have to be about any one course (general term to-dos are just as valid).
`term_code` IS required though, matching the rest of this tab being a
per-term view.

`GradeScaleCutoff` is scoped per-course (owner, course_id, letter_grade).
This exists because the University of Manitoba does not publish a universal
percentage cutoff table (grading weight/scale is set per instructor -- see 
the Registrar's "Methods of evaluation" section). The GPA POINT value per
letter (A+ = 4.5 ... Fail = 0.0) IS standardized and fixed in code -- 
only the percent-to-letter cutoff is student-editable per course.
"""

from __future__ import annotations

from datetime import date, datetime, time
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
    Time,
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

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    weight_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

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


class Todo(Base):
    __tablename__ = "assessment_todos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    term_code: Mapped[str] = mapped_column(
        ForeignKey("terms.term_code", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=True, index=True
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    term: Mapped["Term"] = relationship()
    course: Mapped["Course | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Todo id={self.id} owner={self.owner_id} done={self.is_done}>"


class GradeScaleCutoff(Base):
    __tablename__ = "grade_scale_cutoffs"
    __table_args__ = (
        UniqueConstraint("owner_id", "course_id", "letter_grade", name="uq_grade_scale_cutoffs_owner_course_letter"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True
    )

    letter_grade: Mapped[str] = mapped_column(String(10), nullable=False)
    min_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    course: Mapped["Course"] = relationship()

    def __repr__(self) -> str:
        return f"<GradeScaleCutoff owner={self.owner_id} course={self.course_id} {self.letter_grade}={self.min_percent}>"