"""add title to llm_conversations

Revision ID: 0002_llm_title
Revises: 0001_initial
Create Date: 2025-12-08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_llm_title"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add title column to llm_conversations
    op.add_column(
        "llm_conversations",
        sa.Column("title", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("llm_conversations", "title")
