"""per-course grade scales

Revision ID: d8e9f0a1b2c3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear existing global scales so we can safely add a non-nullable course_id
    op.execute("DELETE FROM grade_scale_cutoffs")

    op.add_column('grade_scale_cutoffs', sa.Column('course_id', sa.Integer(), nullable=False))
    
    op.create_index(op.f('ix_grade_scale_cutoffs_course_id'), 'grade_scale_cutoffs', ['course_id'], unique=False)
    
    op.drop_constraint('uq_grade_scale_cutoffs_owner_letter', 'grade_scale_cutoffs', type_='unique')
    op.create_unique_constraint('uq_grade_scale_cutoffs_owner_course_letter', 'grade_scale_cutoffs', ['owner_id', 'course_id', 'letter_grade'])
    
    op.create_foreign_key(op.f('fk_grade_scale_cutoffs_course_id_courses'), 'grade_scale_cutoffs', 'courses', ['course_id'], ['course_id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(op.f('fk_grade_scale_cutoffs_course_id_courses'), 'grade_scale_cutoffs', type_='foreignkey')
    op.drop_constraint('uq_grade_scale_cutoffs_owner_course_letter', 'grade_scale_cutoffs', type_='unique')
    
    op.create_unique_constraint('uq_grade_scale_cutoffs_owner_letter', 'grade_scale_cutoffs', ['owner_id', 'letter_grade'])
    
    op.drop_index(op.f('ix_grade_scale_cutoffs_course_id'), table_name='grade_scale_cutoffs')
    op.drop_column('grade_scale_cutoffs', 'course_id')