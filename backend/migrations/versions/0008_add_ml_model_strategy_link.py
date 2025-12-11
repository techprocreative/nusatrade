"""add strategy_id, symbol, timeframe to ml_models

Revision ID: 0008_add_ml_model_strategy_link
Revises: 0007_add_user_settings
Create Date: 2025-12-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0008_add_ml_model_strategy_link"
down_revision = "0007_add_user_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add strategy_id column with foreign key to strategies
    op.add_column(
        "ml_models",
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ml_models_strategy_id",
        "ml_models",
        "strategies",
        ["strategy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Add symbol column with default
    op.add_column(
        "ml_models",
        sa.Column("symbol", sa.String(length=20), server_default="EURUSD", nullable=True),
    )
    
    # Add timeframe column with default
    op.add_column(
        "ml_models",
        sa.Column("timeframe", sa.String(length=10), server_default="H1", nullable=True),
    )
    
    # Create index for faster lookups
    op.create_index("idx_ml_models_strategy_id", "ml_models", ["strategy_id"])
    op.create_index("idx_ml_models_symbol", "ml_models", ["symbol"])


def downgrade() -> None:
    op.drop_index("idx_ml_models_symbol", table_name="ml_models")
    op.drop_index("idx_ml_models_strategy_id", table_name="ml_models")
    op.drop_constraint("fk_ml_models_strategy_id", "ml_models", type_="foreignkey")
    op.drop_column("ml_models", "timeframe")
    op.drop_column("ml_models", "symbol")
    op.drop_column("ml_models", "strategy_id")
