"""add pretrained fields to ml_models

Revision ID: 0012_add_pretrained_fields
Revises: 0011_add_default_ml_models
Create Date: 2025-12-13 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0012_add_pretrained_fields'
down_revision = '0011_add_default_ml_models'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_pretrained column to ml_models
    op.add_column('ml_models', sa.Column('is_pretrained', sa.Boolean(), nullable=True, server_default='false'))

    # Add default_model_id foreign key to ml_models
    op.add_column('ml_models', sa.Column('default_model_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_ml_models_default_model', 'ml_models', 'default_ml_models', ['default_model_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_ml_models_default_model', 'ml_models', type_='foreignkey')
    op.drop_column('ml_models', 'default_model_id')
    op.drop_column('ml_models', 'is_pretrained')
