"""Add 2FA/TOTP fields to users table

Revision ID: 0004_add_2fa_fields
Revises: 0003_audit_logs
Create Date: 2024-12-08
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_add_2fa_fields"
down_revision = "0003_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add TOTP secret column
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.String(32), nullable=True)
    )
    
    # Add TOTP enabled flag
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false")
    )
    
    # Create index on totp_enabled for faster queries
    op.create_index(
        "idx_users_totp_enabled",
        "users",
        ["totp_enabled"]
    )


def downgrade() -> None:
    op.drop_index("idx_users_totp_enabled", table_name="users")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
