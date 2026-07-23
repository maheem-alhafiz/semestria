"""composite pk on sections (term_code, crn)

CRNs are only unique within a single Aurora term -- Banner reuses the
same CRN number for the same recurring section year over year (e.g.
MECH 2202 A01 is CRN 11543 in every Fall term). A bare `crn` primary key
on `sections` meant that importing more than one term into the same
table caused later terms to silently overwrite earlier terms' rows
whenever a CRN number repeated. This migration makes the primary key
(term_code, crn) instead, and updates meeting_times' FK to match.

Revision ID: a1b2c3d4e5f6
Revises: 75897d45469e
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "75897d45469e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # meeting_times needs its own term_code before it can FK against the
    # new composite key -- backfill it from sections via crn (the old FK
    # still exists at this point, so crn is still a reliable join key).
    op.add_column("meeting_times", sa.Column("term_code", sa.String(length=6), nullable=True))
    op.execute(
        "UPDATE meeting_times mt SET term_code = s.term_code "
        "FROM sections s WHERE mt.crn = s.crn"
    )
    op.alter_column("meeting_times", "term_code", nullable=False)

    op.drop_constraint("fk_meeting_times_crn_sections", "meeting_times", type_="foreignkey")
    op.drop_constraint("pk_sections", "sections", type_="primary")
    op.create_primary_key("pk_sections", "sections", ["term_code", "crn"])
    op.create_foreign_key(
        "fk_meeting_times_crn_sections",
        "meeting_times",
        "sections",
        ["crn", "term_code"],
        ["crn", "term_code"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_meeting_times_term_code"), "meeting_times", ["term_code"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_meeting_times_term_code"), table_name="meeting_times")
    op.drop_constraint("fk_meeting_times_crn_sections", "meeting_times", type_="foreignkey")
    op.drop_constraint("pk_sections", "sections", type_="primary")
    op.create_primary_key("pk_sections", "sections", ["crn"])
    op.create_foreign_key(
        "fk_meeting_times_crn_sections",
        "meeting_times",
        "sections",
        ["crn"],
        ["crn"],
        ondelete="CASCADE",
    )
    op.drop_column("meeting_times", "term_code")
