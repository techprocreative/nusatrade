"""add training_status columns to ml_models

Revision ID: 0009_add_training_status
Revises: 0008_add_ml_model_strategy_link
Create Date: 2025-12-11
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009_add_training_status"
down_revision = "0008_add_ml_model_strategy_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add training_status column with default 'idle'
    op.add_column(
        "ml_models",
        sa.Column("training_status", sa.String(length=20), server_default="idle", nullable=True),
    )
    
    # Add training_error column for error messages
    op.add_column(
        "ml_models",
        sa.Column("training_error", sa.String(length=500), nullable=True),
    )
    
    # Add training timestamps
    op.add_column(
        "ml_models",
        sa.Column("training_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "ml_models",
        sa.Column("training_completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ml_models", "training_completed_at")
    op.drop_column("ml_models", "training_started_at")
    op.drop_column("ml_models", "training_error")
    op.drop_column("ml_models", "training_status")
