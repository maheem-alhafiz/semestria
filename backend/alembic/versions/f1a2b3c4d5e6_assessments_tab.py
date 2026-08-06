"""assessments tab: term date range + assessments/topics/tracked_courses

Revision ID: f1a2b3c4d5e6
Revises: 2d36cf284edb
Create Date: 2026-08-06

Adds:
- terms.start_date / terms.end_date -- derived (MIN/MAX over meeting_times),
  see app.models.term's docstring. Backfilled for existing terms in this
  migration's upgrade() so the Assessments tab's week nav works immediately
  for already-imported terms, not just future import runs.
- assessments -- due-dated items (assignments/quizzes/exams/labs) per
  (owner, term, course). See app.models.assessment.
- weekly_topics -- free-text per (owner, term, course, week) notes.
- assessment_tracked_courses -- manually-added courses only; the auto side
  is read live from plan_items, never duplicated into a table here.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "2d36cf284edb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("terms", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("terms", sa.Column("end_date", sa.Date(), nullable=True))

    # One-time backfill for terms already imported before this migration --
    # mirrors exactly what refresh_term_date_range() does going forward.
    op.execute(
        """
        UPDATE terms
        SET start_date = agg.min_start, end_date = agg.max_end
        FROM (
            SELECT term_code, MIN(start_date) AS min_start, MAX(end_date) AS max_end
            FROM meeting_times
            WHERE start_date IS NOT NULL AND end_date IS NOT NULL
            GROUP BY term_code
        ) AS agg
        WHERE terms.term_code = agg.term_code
        """
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("assessment_type", sa.String(length=20), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("weight_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("grade_received", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "assessment_type IN ('ASSIGNMENT', 'QUIZ', 'EXAM', 'LAB', 'PROJECT', 'OTHER')",
            name="ck_assessments_type",
        ),
        sa.ForeignKeyConstraint(
            ["term_code"], ["terms.term_code"], name=op.f("fk_assessments_term_code_terms"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_assessments_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
    )
    op.create_index(op.f("ix_assessments_owner_id"), "assessments", ["owner_id"], unique=False)
    op.create_index(op.f("ix_assessments_term_code"), "assessments", ["term_code"], unique=False)
    op.create_index(op.f("ix_assessments_course_id"), "assessments", ["course_id"], unique=False)

    op.create_table(
        "weekly_topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("week_start_date", sa.Date(), nullable=False),
        sa.Column("topic_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["term_code"], ["terms.term_code"], name=op.f("fk_weekly_topics_term_code_terms"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_weekly_topics_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_topics")),
        sa.UniqueConstraint(
            "owner_id",
            "term_code",
            "course_id",
            "week_start_date",
            name="uq_weekly_topics_owner_term_course_week",
        ),
    )
    op.create_index(op.f("ix_weekly_topics_owner_id"), "weekly_topics", ["owner_id"], unique=False)
    op.create_index(op.f("ix_weekly_topics_term_code"), "weekly_topics", ["term_code"], unique=False)
    op.create_index(op.f("ix_weekly_topics_course_id"), "weekly_topics", ["course_id"], unique=False)

    op.create_table(
        "assessment_tracked_courses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["term_code"],
            ["terms.term_code"],
            name=op.f("fk_assessment_tracked_courses_term_code_terms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_assessment_tracked_courses_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_tracked_courses")),
        sa.UniqueConstraint(
            "owner_id", "term_code", "course_id", name="uq_assessment_tracked_courses_owner_term_course"
        ),
    )
    op.create_index(
        op.f("ix_assessment_tracked_courses_owner_id"), "assessment_tracked_courses", ["owner_id"], unique=False
    )
    op.create_index(
        op.f("ix_assessment_tracked_courses_term_code"), "assessment_tracked_courses", ["term_code"], unique=False
    )
    op.create_index(
        op.f("ix_assessment_tracked_courses_course_id"), "assessment_tracked_courses", ["course_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_tracked_courses_course_id"), table_name="assessment_tracked_courses")
    op.drop_index(op.f("ix_assessment_tracked_courses_term_code"), table_name="assessment_tracked_courses")
    op.drop_index(op.f("ix_assessment_tracked_courses_owner_id"), table_name="assessment_tracked_courses")
    op.drop_table("assessment_tracked_courses")

    op.drop_index(op.f("ix_weekly_topics_course_id"), table_name="weekly_topics")
    op.drop_index(op.f("ix_weekly_topics_term_code"), table_name="weekly_topics")
    op.drop_index(op.f("ix_weekly_topics_owner_id"), table_name="weekly_topics")
    op.drop_table("weekly_topics")

    op.drop_index(op.f("ix_assessments_course_id"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_term_code"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_owner_id"), table_name="assessments")
    op.drop_table("assessments")

    op.drop_column("terms", "end_date")
    op.drop_column("terms", "start_date")
