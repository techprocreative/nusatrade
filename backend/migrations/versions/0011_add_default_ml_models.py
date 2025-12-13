"""Add default ML models tables

Revision ID: 0011_add_default_ml_models
Revises: 0010_add_trade_status
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers
revision = '0011_add_default_ml_models'
down_revision = '0010_add_trade_status'
branch_labels = None
depends_on = None


def upgrade():
    # Create default_ml_models table (system-wide defaults)
    op.create_table(
        'default_ml_models',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('symbol', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('model_path', sa.String(500), nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('is_system_default', sa.Boolean, default=True),

        # Performance metrics (cached)
        sa.Column('win_rate', sa.Float, nullable=True),
        sa.Column('profit_factor', sa.Float, nullable=True),
        sa.Column('accuracy', sa.Float, nullable=True),
        sa.Column('total_trades', sa.Integer, nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Create user_default_models table (user-specific overrides)
    op.create_table(
        'user_default_models',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('model_path', sa.String(500), nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),

        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create unique constraint and index for user_default_models
    op.create_unique_constraint('uq_user_symbol', 'user_default_models', ['user_id', 'symbol'])
    op.create_index('idx_user_symbol', 'user_default_models', ['user_id', 'symbol'])

    # Insert system defaults for XAUUSD and EURUSD
    op.execute("""
        INSERT INTO default_ml_models (id, symbol, model_path, model_id, win_rate, profit_factor, accuracy, total_trades, is_system_default)
        VALUES
        (
            gen_random_uuid(),
            'XAUUSD',
            'model_xgboost_20251212_235414.pkl',
            'model_xgboost_20251212_235414',
            75.0,
            2.02,
            NULL,
            NULL,
            TRUE
        ),
        (
            gen_random_uuid(),
            'EURUSD',
            'eurusd/forex-optimized/model_forex_xgboost_20251213_112218.pkl',
            'model_forex_xgboost_20251213_112218',
            79.1,
            3.77,
            60.3,
            4675,
            TRUE
        )
    """)


def downgrade():
    op.drop_index('idx_user_symbol', 'user_default_models')
    op.drop_constraint('uq_user_symbol', 'user_default_models', type_='unique')
    op.drop_table('user_default_models')
    op.drop_table('default_ml_models')
