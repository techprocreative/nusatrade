"""Enhance strategies table with AI generation fields

Revision ID: 0006_enhance_strategies
Revises: 0005_add_system_settings
Create Date: 2024-12-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_enhance_strategies"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to strategies table
    op.add_column(
        "strategies",
        sa.Column("code", sa.Text(), nullable=True)
    )
    op.add_column(
        "strategies",
        sa.Column("parameters", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "strategies",
        sa.Column("indicators", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "strategies",
        sa.Column("entry_rules", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "strategies",
        sa.Column("exit_rules", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "strategies",
        sa.Column("risk_management", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "strategies",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "strategies",
        sa.Column("backtest_results", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    
    # Create index on is_active for faster queries
    op.create_index(
        "idx_strategies_is_active",
        "strategies",
        ["is_active"]
    )
    
    # Create index on strategy_type
    op.create_index(
        "idx_strategies_type",
        "strategies",
        ["strategy_type"]
    )


def downgrade() -> None:
    op.drop_index("idx_strategies_type", table_name="strategies")
    op.drop_index("idx_strategies_is_active", table_name="strategies")
    op.drop_column("strategies", "backtest_results")
    op.drop_column("strategies", "is_active")
    op.drop_column("strategies", "risk_management")
    op.drop_column("strategies", "exit_rules")
    op.drop_column("strategies", "entry_rules")
    op.drop_column("strategies", "indicators")
    op.drop_column("strategies", "parameters")
    op.drop_column("strategies", "code")
