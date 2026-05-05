"""add backtest time-series columns

Revision ID: 7788177f86a8
Revises: 75e8b9fafa7b
Create Date: 2026-05-05 20:25:38.529462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7788177f86a8'
down_revision: Union[str, Sequence[str], None] = '75e8b9fafa7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('backtest_results', sa.Column('equity_curve', sa.JSON(), nullable=True))
    op.add_column('backtest_results', sa.Column('drawdown_curve', sa.JSON(), nullable=True))
    op.add_column('backtest_results', sa.Column('benchmark_curve', sa.JSON(), nullable=True))
    op.add_column('backtest_results', sa.Column('yearly_returns', sa.JSON(), nullable=True))
    op.add_column('backtest_results', sa.Column('monthly_returns', sa.JSON(), nullable=True))
    op.add_column('backtest_results', sa.Column('trades', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('backtest_results', 'trades')
    op.drop_column('backtest_results', 'monthly_returns')
    op.drop_column('backtest_results', 'yearly_returns')
    op.drop_column('backtest_results', 'benchmark_curve')
    op.drop_column('backtest_results', 'drawdown_curve')
    op.drop_column('backtest_results', 'equity_curve')
