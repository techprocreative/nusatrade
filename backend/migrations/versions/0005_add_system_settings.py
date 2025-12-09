"""Add system_settings table for runtime configuration

Revision ID: 0005
Revises: 0004
Create Date: 2024-12-09 09:28:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004_add_2fa_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum(
            'AI_PROVIDER', 'REDIS', 'EMAIL', 'RATE_LIMITING', 'TRADING', 'STORAGE', 'GENERAL',
            name='settingcategory'
        ), nullable=False),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )
    
    # Create indexes
    op.create_index('ix_system_settings_key', 'system_settings', ['key'])
    op.create_index('ix_system_settings_category', 'system_settings', ['category'])
    op.create_index('ix_system_settings_is_active', 'system_settings', ['is_active'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_system_settings_is_active', table_name='system_settings')
    op.drop_index('ix_system_settings_category', table_name='system_settings')
    op.drop_index('ix_system_settings_key', table_name='system_settings')
    
    # Drop table
    op.drop_table('system_settings')
    
    # Drop enum type
    op.execute('DROP TYPE settingcategory')
