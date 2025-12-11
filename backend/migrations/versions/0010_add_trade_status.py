"""Add status field to trades table

Revision ID: 0010_add_trade_status
Revises: 0009_add_training_status
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0010_add_trade_status'
down_revision = '0009_add_training_status'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column to trades table with default value
    op.add_column('trades', sa.Column('status', sa.String(20), server_default='open'))


def downgrade():
    op.drop_column('trades', 'status')
