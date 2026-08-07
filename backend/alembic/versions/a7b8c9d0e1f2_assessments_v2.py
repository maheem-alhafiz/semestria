"""assessments tab v2: due_time, todos, grade scale cutoffs, topics as a log

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-06

- assessments.due_time -- see Assessment's docstring.
- weekly_topics: drops the old one-row-per-(owner,term,course,week) unique
  constraint. It's now an append-only log (see WeeklyTopic's docstring for
  why the old singleton-per-week shape had a real data-corruption bug).
- assessment_todos -- new table, see Todo's docstring.
- grade_scale_cutoffs -- new table, see GradeScaleCutoff's docstring.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("due_time", sa.Time(), nullable=True))

    op.drop_constraint(
        "uq_weekly_topics_owner_term_course_week", "weekly_topics", type_="unique"
    )

    op.create_table(
        "assessment_todos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["term_code"], ["terms.term_code"], name=op.f("fk_assessment_todos_term_code_terms"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_assessment_todos_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_todos")),
    )
    op.create_index(op.f("ix_assessment_todos_owner_id"), "assessment_todos", ["owner_id"], unique=False)
    op.create_index(op.f("ix_assessment_todos_term_code"), "assessment_todos", ["term_code"], unique=False)
    op.create_index(op.f("ix_assessment_todos_course_id"), "assessment_todos", ["course_id"], unique=False)

    op.create_table(
        "grade_scale_cutoffs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("letter_grade", sa.String(length=10), nullable=False),
        sa.Column("min_percent", sa.Numeric(5, 2), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grade_scale_cutoffs")),
        sa.UniqueConstraint("owner_id", "letter_grade", name="uq_grade_scale_cutoffs_owner_letter"),
    )
    op.create_index(op.f("ix_grade_scale_cutoffs_owner_id"), "grade_scale_cutoffs", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_grade_scale_cutoffs_owner_id"), table_name="grade_scale_cutoffs")
    op.drop_table("grade_scale_cutoffs")

    op.drop_index(op.f("ix_assessment_todos_course_id"), table_name="assessment_todos")
    op.drop_index(op.f("ix_assessment_todos_term_code"), table_name="assessment_todos")
    op.drop_index(op.f("ix_assessment_todos_owner_id"), table_name="assessment_todos")
    op.drop_table("assessment_todos")

    op.create_unique_constraint(
        "uq_weekly_topics_owner_term_course_week",
        "weekly_topics",
        ["owner_id", "term_code", "course_id", "week_start_date"],
    )

    op.drop_column("assessments", "due_time")
