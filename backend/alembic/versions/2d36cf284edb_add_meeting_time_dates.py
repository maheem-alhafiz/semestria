"""add_meeting_time_dates

Revision ID: 2d36cf284edb
Revises: 14a4a805abd2
Create Date: 2026-07-27 16:46:28.315670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d36cf284edb'
down_revision: Union[str, None] = '14a4a805abd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meeting_times", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("meeting_times", sa.Column("end_date", sa.Date(), nullable=True))

def downgrade() -> None:
    op.drop_column("meeting_times", "end_date")
    op.drop_column("meeting_times", "start_date")