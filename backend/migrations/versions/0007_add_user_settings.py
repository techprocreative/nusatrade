"""add user settings column

Revision ID: 0007_add_user_settings
Revises: 0006_enhance_strategies
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_add_user_settings'
down_revision = '0006_enhance_strategies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add settings column to users table
    op.add_column(
        'users',
        sa.Column('settings', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'settings')
