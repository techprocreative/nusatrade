"""add symbol and timeframe to strategies

Revision ID: 0013_symbol_timeframe
Revises: 0012_add_pretrained_fields
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0013_symbol_timeframe"
down_revision = "0012_add_pretrained_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add symbol column to strategies table
    op.add_column(
        "strategies",
        sa.Column("symbol", sa.String(length=20), nullable=True),
    )

    # Add timeframe column to strategies table
    op.add_column(
        "strategies",
        sa.Column("timeframe", sa.String(length=10), nullable=True),
    )

    # Create indexes for faster lookups
    op.create_index("idx_strategies_symbol", "strategies", ["symbol"])
    op.create_index("idx_strategies_symbol_active", "strategies", ["symbol", "is_active"])


def downgrade() -> None:
    op.drop_index("idx_strategies_symbol_active", table_name="strategies")
    op.drop_index("idx_strategies_symbol", table_name="strategies")
    op.drop_column("strategies", "timeframe")
    op.drop_column("strategies", "symbol")
