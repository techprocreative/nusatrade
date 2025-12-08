"""Add audit logs table

Revision ID: 0003_audit_logs
Revises: 0002_llm_title
Create Date: 2024-12-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_audit_logs"
down_revision = "0002_llm_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )

    # Add foreign key to users table
    op.create_foreign_key(
        "fk_audit_logs_user_id",
        "audit_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_audit_logs_user_id", "audit_logs", type_="foreignkey")
    op.drop_table("audit_logs")
