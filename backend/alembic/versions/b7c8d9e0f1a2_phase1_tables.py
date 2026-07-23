"""add plans, plan_items, plan_item_sections, academic_record

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-21

Adds the Phase 1 planning/tracking tables:
- plans: a saveable, named "what if I took these courses" sandbox
- plan_items: one course selected into a plan, for one specific term
  (the same course in Fall AND Winter within one plan is two rows, by
  design -- see app.models.plan_item)
- plan_item_sections: which specific CRN was chosen per link_slot for a
  plan_item, FK'd to sections via the composite (term_code, crn) pair
- academic_record: the permanent transcript, independent of any Plan --
  "Mark as Final" upserts into this table rather than ever replacing it
  wholesale, which is what solves the "finalizing a later plan wipes out
  an earlier one" problem. See app.models.academic_record for the full
  reasoning.

All FKs to sections use (term_code, crn) as a pair, matching sections'
actual composite primary key from the a1b2c3d4e5f6 migration -- never crn
alone, for the same cross-term CRN reuse reason documented throughout
this codebase (see app.models.section).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("top_term_code", sa.String(length=6), nullable=True),
        sa.Column("bottom_term_code", sa.String(length=6), nullable=True),
        sa.Column("share_token", sa.String(length=43), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["top_term_code"],
            ["terms.term_code"],
            name=op.f("fk_plans_top_term_code_terms"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["bottom_term_code"],
            ["terms.term_code"],
            name=op.f("fk_plans_bottom_term_code_terms"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
    )
    op.create_index(op.f("ix_plans_share_token"), "plans", ["share_token"], unique=True)

    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.id"],
            name=op.f("fk_plan_items_plan_id_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_code"],
            ["terms.term_code"],
            name=op.f("fk_plan_items_term_code_terms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_plan_items_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_items")),
        sa.UniqueConstraint(
            "plan_id", "term_code", "course_id", name="uq_plan_items_plan_term_course"
        ),
    )
    op.create_index(op.f("ix_plan_items_plan_id"), "plan_items", ["plan_id"], unique=False)
    op.create_index(op.f("ix_plan_items_term_code"), "plan_items", ["term_code"], unique=False)
    op.create_index(op.f("ix_plan_items_course_id"), "plan_items", ["course_id"], unique=False)

    op.create_table(
        "plan_item_sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_item_id", sa.Integer(), nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("crn", sa.String(length=10), nullable=False),
        sa.Column("link_slot", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["plan_item_id"],
            ["plan_items.id"],
            name=op.f("fk_plan_item_sections_plan_item_id_plan_items"),
            ondelete="CASCADE",
        ),
        # Composite FK to sections(term_code, crn) -- matches sections'
        # actual composite PK as a column SET; the order listed here
        # doesn't need to match the order sections' PK was declared in
        # (confirmed safe by meeting_times' equivalent FK working
        # correctly against a differently-ordered PK earlier tonight).
        sa.ForeignKeyConstraint(
            ["term_code", "crn"],
            ["sections.term_code", "sections.crn"],
            name="fk_plan_item_sections_term_code_crn_sections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_item_sections")),
        sa.UniqueConstraint(
            "plan_item_id", "term_code", "crn", name="uq_plan_item_sections_item_term_crn"
        ),
    )
    op.create_index(
        op.f("ix_plan_item_sections_plan_item_id"), "plan_item_sections", ["plan_item_id"], unique=False
    )
    op.create_index(
        op.f("ix_plan_item_sections_term_code"), "plan_item_sections", ["term_code"], unique=False
    )
    op.create_index(op.f("ix_plan_item_sections_crn"), "plan_item_sections", ["crn"], unique=False)

    op.create_table(
        "academic_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("term_code", sa.String(length=6), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("source_plan_id", sa.Integer(), nullable=True),
        sa.Column("crn", sa.String(length=10), nullable=True),
        sa.Column("title_snapshot", sa.String(length=255), nullable=False),
        sa.Column("credit_hours_snapshot", sa.Numeric(4, 2), nullable=False),
        sa.Column("grade", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["term_code"],
            ["terms.term_code"],
            name=op.f("fk_academic_record_term_code_terms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_academic_record_course_id_courses"),
            ondelete="CASCADE",
        ),
        # SET NULL, not CASCADE -- deleting the Plan that originally
        # finalized this row must never delete the permanent record
        # itself. See app.models.academic_record's docstring.
        sa.ForeignKeyConstraint(
            ["source_plan_id"],
            ["plans.id"],
            name=op.f("fk_academic_record_source_plan_id_plans"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_record")),
        sa.UniqueConstraint("term_code", "course_id", name="uq_academic_record_term_course"),
    )
    op.create_index(
        op.f("ix_academic_record_term_code"), "academic_record", ["term_code"], unique=False
    )
    op.create_index(
        op.f("ix_academic_record_course_id"), "academic_record", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_academic_record_source_plan_id"), "academic_record", ["source_plan_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_academic_record_source_plan_id"), table_name="academic_record")
    op.drop_index(op.f("ix_academic_record_course_id"), table_name="academic_record")
    op.drop_index(op.f("ix_academic_record_term_code"), table_name="academic_record")
    op.drop_table("academic_record")

    op.drop_index(op.f("ix_plan_item_sections_crn"), table_name="plan_item_sections")
    op.drop_index(op.f("ix_plan_item_sections_term_code"), table_name="plan_item_sections")
    op.drop_index(op.f("ix_plan_item_sections_plan_item_id"), table_name="plan_item_sections")
    op.drop_table("plan_item_sections")

    op.drop_index(op.f("ix_plan_items_course_id"), table_name="plan_items")
    op.drop_index(op.f("ix_plan_items_term_code"), table_name="plan_items")
    op.drop_index(op.f("ix_plan_items_plan_id"), table_name="plan_items")
    op.drop_table("plan_items")

    op.drop_index(op.f("ix_plans_share_token"), table_name="plans")
    op.drop_table("plans")
