"""add backtest task_id column

Revision ID: a1b2c3d4e5f6
Revises: 7788177f86a8
Create Date: 2026-05-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7788177f86a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtest_results', sa.Column('task_id', sa.String(length=32), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('backtest_results', 'task_id')
