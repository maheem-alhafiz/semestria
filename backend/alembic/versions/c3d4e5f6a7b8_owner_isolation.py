"""add owner_id for anonymous per-visitor isolation

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-07-21

Adds cookie-derived owner_id to plans and academic_record so one
visitor's data is never visible to another -- see app.core.visitor for
the cookie mechanism and app.models.plan / app.models.academic_record
for why each table needs this. academic_record's uniqueness constraint
changes from (term_code, course_id) to (owner_id, term_code, course_id):
two different visitors independently taking the same course in the same
term is normal and must not collide.

Both tables were created earlier THIS SAME NIGHT (migration
b7c8d9e0f1a2) with no real data in them yet, so owner_id is added as
NOT NULL directly with no backfill step needed. If this is ever applied
against a database that already has real plans/academic_record rows,
this migration will fail on the NOT NULL constraint and needs a backfill
step added first.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("owner_id", sa.String(length=64), nullable=False))
    op.create_index(op.f("ix_plans_owner_id"), "plans", ["owner_id"], unique=False)

    op.add_column("academic_record", sa.Column("owner_id", sa.String(length=64), nullable=False))
    op.create_index(
        op.f("ix_academic_record_owner_id"), "academic_record", ["owner_id"], unique=False
    )

    op.drop_constraint(
        "uq_academic_record_term_course", "academic_record", type_="unique"
    )
    op.create_unique_constraint(
        "uq_academic_record_owner_term_course",
        "academic_record",
        ["owner_id", "term_code", "course_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_academic_record_owner_term_course", "academic_record", type_="unique"
    )
    op.create_unique_constraint(
        "uq_academic_record_term_course", "academic_record", ["term_code", "course_id"]
    )

    op.drop_index(op.f("ix_academic_record_owner_id"), table_name="academic_record")
    op.drop_column("academic_record", "owner_id")

    op.drop_index(op.f("ix_plans_owner_id"), table_name="plans")
    op.drop_column("plans", "owner_id")
