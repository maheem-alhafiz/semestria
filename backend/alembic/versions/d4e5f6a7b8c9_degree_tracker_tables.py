"""add degree tracker tables and course prerequisite text

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-21

Adds the Degree Tracker's requirement schema:
- degree_programs: one row per major per catalog_year (see
  app.models.degree_program for why catalog_year is provenance, not a
  per-student pin)
- degree_program_includes: lets a shared requirement set (Preliminary
  Engineering Program) be referenced by many majors instead of duplicated
- requirement_groups: the nestable requirement tree (ALL / ONE_OF / N_OF)
- requirement_group_courses / requirement_group_patterns: the two
  independent ways a course can satisfy a group (explicit course_id, or
  a subject+level-range pattern)
- course_relationships: generic pairwise EQUIVALENT / MUTUALLY_EXCLUSIVE /
  SUBSTITUTE_FOR relationships (covers the catalog's "Equiv To,"
  "Mutually Exclusive," and "X in lieu of Y" footnotes in one table)
- manual_requirement_fulfillments: the escape hatch for genuinely
  faculty-wide/prose-only rules a student links directly against their
  own transcript row, rather than the matcher trying to encode every
  exception (see app.models.manual_fulfillment)

Also adds prerequisites_text / corequisites_text to courses -- raw
scraped prose, always shown as-is; NOT parsed into structured logic here
(see app.models.course's docstring on why that's a deliberately separate,
lower-confidence problem).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("prerequisites_text", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("corequisites_text", sa.Text(), nullable=True))

    op.create_table(
        "degree_programs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("faculty", sa.String(length=255), nullable=False),
        sa.Column("catalog_year", sa.String(length=9), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degree_programs")),
        sa.UniqueConstraint(
            "name", "catalog_year", name="uq_degree_programs_name_catalog_year"
        ),
    )

    op.create_table(
        "degree_program_includes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("degree_program_id", sa.Integer(), nullable=False),
        sa.Column("includes_program_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["degree_program_id"],
            ["degree_programs.id"],
            name=op.f("fk_degree_program_includes_degree_program_id_degree_programs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["includes_program_id"],
            ["degree_programs.id"],
            name=op.f("fk_degree_program_includes_includes_program_id_degree_programs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degree_program_includes")),
        sa.UniqueConstraint(
            "degree_program_id", "includes_program_id", name="uq_degree_program_includes_pair"
        ),
    )
    op.create_index(
        op.f("ix_degree_program_includes_degree_program_id"),
        "degree_program_includes",
        ["degree_program_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_degree_program_includes_includes_program_id"),
        "degree_program_includes",
        ["includes_program_id"],
        unique=False,
    )

    op.create_table(
        "requirement_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("degree_program_id", sa.Integer(), nullable=False),
        sa.Column("parent_group_id", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("courses_required", sa.Integer(), nullable=True),
        sa.Column("credit_hours_required", sa.Numeric(5, 2), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "kind IN ('ALL', 'ONE_OF', 'N_OF')", name="ck_requirement_groups_kind"
        ),
        sa.ForeignKeyConstraint(
            ["degree_program_id"],
            ["degree_programs.id"],
            name=op.f("fk_requirement_groups_degree_program_id_degree_programs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_group_id"],
            ["requirement_groups.id"],
            name=op.f("fk_requirement_groups_parent_group_id_requirement_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirement_groups")),
    )
    op.create_index(
        op.f("ix_requirement_groups_degree_program_id"),
        "requirement_groups",
        ["degree_program_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requirement_groups_parent_group_id"),
        "requirement_groups",
        ["parent_group_id"],
        unique=False,
    )

    op.create_table(
        "requirement_group_courses",
        sa.Column("requirement_group_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["requirement_group_id"],
            ["requirement_groups.id"],
            name=op.f("fk_requirement_group_courses_requirement_group_id_requirement_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.course_id"],
            name=op.f("fk_requirement_group_courses_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "requirement_group_id", "course_id", name=op.f("pk_requirement_group_courses")
        ),
    )

    op.create_table(
        "requirement_group_patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_group_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=10), nullable=True),
        sa.Column("level_min", sa.Integer(), nullable=False),
        sa.Column("level_max", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["requirement_group_id"],
            ["requirement_groups.id"],
            name=op.f("fk_requirement_group_patterns_requirement_group_id_requirement_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirement_group_patterns")),
    )
    op.create_index(
        op.f("ix_requirement_group_patterns_requirement_group_id"),
        "requirement_group_patterns",
        ["requirement_group_id"],
        unique=False,
    )

    op.create_table(
        "course_relationships",
        sa.Column("course_id_a", sa.Integer(), nullable=False),
        sa.Column("course_id_b", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "relationship_type IN ('EQUIVALENT', 'MUTUALLY_EXCLUSIVE', 'SUBSTITUTE_FOR')",
            name="ck_course_relationships_type",
        ),
        sa.ForeignKeyConstraint(
            ["course_id_a"],
            ["courses.course_id"],
            name=op.f("fk_course_relationships_course_id_a_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id_b"],
            ["courses.course_id"],
            name=op.f("fk_course_relationships_course_id_b_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "course_id_a",
            "course_id_b",
            "relationship_type",
            name=op.f("pk_course_relationships"),
        ),
    )

    op.create_table(
        "manual_requirement_fulfillments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("requirement_group_id", sa.Integer(), nullable=False),
        sa.Column("academic_record_id", sa.Integer(), nullable=False),
        sa.Column("credit_hours_applied", sa.Numeric(4, 2), nullable=True),
        sa.ForeignKeyConstraint(
            ["requirement_group_id"],
            ["requirement_groups.id"],
            name=op.f(
                "fk_manual_requirement_fulfillments_requirement_group_id_requirement_groups"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_record_id"],
            ["academic_record.id"],
            name=op.f("fk_manual_requirement_fulfillments_academic_record_id_academic_record"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manual_requirement_fulfillments")),
        sa.UniqueConstraint(
            "owner_id",
            "requirement_group_id",
            "academic_record_id",
            name="uq_manual_fulfillment_owner_group_record",
        ),
    )
    op.create_index(
        op.f("ix_manual_requirement_fulfillments_owner_id"),
        "manual_requirement_fulfillments",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_manual_requirement_fulfillments_requirement_group_id"),
        "manual_requirement_fulfillments",
        ["requirement_group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_manual_requirement_fulfillments_academic_record_id"),
        "manual_requirement_fulfillments",
        ["academic_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_manual_requirement_fulfillments_academic_record_id"),
        table_name="manual_requirement_fulfillments",
    )
    op.drop_index(
        op.f("ix_manual_requirement_fulfillments_requirement_group_id"),
        table_name="manual_requirement_fulfillments",
    )
    op.drop_index(
        op.f("ix_manual_requirement_fulfillments_owner_id"),
        table_name="manual_requirement_fulfillments",
    )
    op.drop_table("manual_requirement_fulfillments")

    op.drop_table("course_relationships")

    op.drop_index(
        op.f("ix_requirement_group_patterns_requirement_group_id"),
        table_name="requirement_group_patterns",
    )
    op.drop_table("requirement_group_patterns")

    op.drop_table("requirement_group_courses")

    op.drop_index(
        op.f("ix_requirement_groups_parent_group_id"), table_name="requirement_groups"
    )
    op.drop_index(
        op.f("ix_requirement_groups_degree_program_id"), table_name="requirement_groups"
    )
    op.drop_table("requirement_groups")

    op.drop_index(
        op.f("ix_degree_program_includes_includes_program_id"),
        table_name="degree_program_includes",
    )
    op.drop_index(
        op.f("ix_degree_program_includes_degree_program_id"),
        table_name="degree_program_includes",
    )
    op.drop_table("degree_program_includes")

    op.drop_table("degree_programs")

    op.drop_column("courses", "corequisites_text")
    op.drop_column("courses", "prerequisites_text")
