"""initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2025-12-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), server_default="trader"),
        sa.Column("subscription_tier", sa.String(length=50), server_default="free"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active"),
        sa.Column("stripe_subscription_id", sa.String(length=255)),
        sa.Column("current_period_start", sa.DateTime()),
        sa.Column("current_period_end", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "broker_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("broker_name", sa.String(length=100), nullable=False),
        sa.Column("account_number", sa.String(length=50)),
        sa.Column("server", sa.String(length=100)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_connected_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "connector_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("broker_connections.id")),
        sa.Column("session_token", sa.String(length=255), unique=True),
        sa.Column("status", sa.String(length=50), server_default="online"),
        sa.Column("last_heartbeat", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("strategy_type", sa.String(length=50)),
        sa.Column("config", sa.JSON()),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "backtest_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id")),
        sa.Column("symbol", sa.String(length=20)),
        sa.Column("timeframe", sa.String(length=10)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("initial_balance", sa.Numeric(20, 2)),
        sa.Column("config", sa.JSON()),
        sa.Column("status", sa.String(length=50), server_default="running"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.String(length=255)),
        sa.Column("model_type", sa.String(length=50)),
        sa.Column("config", sa.JSON()),
        sa.Column("performance_metrics", sa.JSON()),
        sa.Column("file_path", sa.String(length=500)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "llm_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("context", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("broker_connections.id")),
        sa.Column("ticket", sa.BigInteger()),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("trade_type", sa.String(length=10), nullable=False),
        sa.Column("lot_size", sa.Numeric(10, 2)),
        sa.Column("open_price", sa.Numeric(20, 5)),
        sa.Column("close_price", sa.Numeric(20, 5)),
        sa.Column("stop_loss", sa.Numeric(20, 5)),
        sa.Column("take_profit", sa.Numeric(20, 5)),
        sa.Column("profit", sa.Numeric(20, 2)),
        sa.Column("commission", sa.Numeric(20, 2)),
        sa.Column("swap", sa.Numeric(20, 2)),
        sa.Column("open_time", sa.DateTime()),
        sa.Column("close_time", sa.DateTime()),
        sa.Column("magic_number", sa.Integer()),
        sa.Column("comment", sa.String()),
        sa.Column("source", sa.String(length=50)),
        sa.Column("ml_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("broker_connections.id")),
        sa.Column("ticket", sa.BigInteger()),
        sa.Column("symbol", sa.String(length=20)),
        sa.Column("trade_type", sa.String(length=10)),
        sa.Column("lot_size", sa.Numeric(10, 2)),
        sa.Column("open_price", sa.Numeric(20, 5)),
        sa.Column("current_price", sa.Numeric(20, 5)),
        sa.Column("stop_loss", sa.Numeric(20, 5)),
        sa.Column("take_profit", sa.Numeric(20, 5)),
        sa.Column("profit", sa.Numeric(20, 2)),
        sa.Column("open_time", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("ml_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_models.id"), nullable=True),
        sa.Column("symbol", sa.String(length=20)),
        sa.Column("direction", sa.String(length=10)),
        sa.Column("confidence", sa.Numeric(5, 2)),
        sa.Column("entry_price", sa.Numeric(20, 5)),
        sa.Column("stop_loss", sa.Numeric(20, 5)),
        sa.Column("take_profit", sa.Numeric(20, 5)),
        sa.Column("status", sa.String(length=50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_sessions.id")),
        sa.Column("net_profit", sa.Numeric(20, 2)),
        sa.Column("total_trades", sa.Integer()),
        sa.Column("winning_trades", sa.Integer()),
        sa.Column("losing_trades", sa.Integer()),
        sa.Column("win_rate", sa.Numeric(5, 2)),
        sa.Column("profit_factor", sa.Numeric(10, 2)),
        sa.Column("max_drawdown", sa.Numeric(10, 2)),
        sa.Column("max_drawdown_pct", sa.Numeric(5, 2)),
        sa.Column("sharpe_ratio", sa.Numeric(10, 2)),
        sa.Column("sortino_ratio", sa.Numeric(10, 2)),
        sa.Column("calmar_ratio", sa.Numeric(10, 2)),
        sa.Column("expectancy", sa.Numeric(20, 2)),
        sa.Column("avg_win", sa.Numeric(20, 2)),
        sa.Column("avg_loss", sa.Numeric(20, 2)),
        sa.Column("equity_curve", sa.JSON()),
        sa.Column("trades", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "historical_data",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(20, 5)),
        sa.Column("high", sa.Numeric(20, 5)),
        sa.Column("low", sa.Numeric(20, 5)),
        sa.Column("close", sa.Numeric(20, 5)),
        sa.Column("volume", sa.Numeric(20, 2)),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_historical_data"),
    )

    op.create_table(
        "ml_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ml_models.id")),
        sa.Column("symbol", sa.String(length=20)),
        sa.Column("prediction", sa.JSON()),
        sa.Column("actual_outcome", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "llm_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_conversations.id")),
        sa.Column("role", sa.String(length=20)),
        sa.Column("content", sa.String()),
        sa.Column("tokens_used", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "market_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(length=20)),
        sa.Column("timeframe", sa.String(length=10)),
        sa.Column("analysis_type", sa.String(length=50)),
        sa.Column("content", sa.String()),
        sa.Column("sentiment_score", sa.String()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index("idx_trades_user_id", "trades", ["user_id"])
    op.create_index("idx_trades_symbol", "trades", ["symbol"])
    op.create_index("idx_trades_open_time", "trades", ["open_time"])
    op.create_index("idx_positions_user_id", "positions", ["user_id"])
    op.create_index("idx_historical_data_lookup", "historical_data", ["symbol", "timeframe", "timestamp"])
    op.create_index("idx_signals_user_id", "signals", ["user_id"])
    op.create_index("idx_backtest_sessions_user_id", "backtest_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_backtest_sessions_user_id", table_name="backtest_sessions")
    op.drop_index("idx_signals_user_id", table_name="signals")
    op.drop_index("idx_historical_data_lookup", table_name="historical_data")
    op.drop_index("idx_positions_user_id", table_name="positions")
    op.drop_index("idx_trades_open_time", table_name="trades")
    op.drop_index("idx_trades_symbol", table_name="trades")
    op.drop_index("idx_trades_user_id", table_name="trades")
    op.drop_table("market_analysis")
    op.drop_table("llm_messages")
    op.drop_table("ml_predictions")
    op.drop_table("historical_data")
    op.drop_table("backtest_results")
    op.drop_table("signals")
    op.drop_table("positions")
    op.drop_table("trades")
    op.drop_table("llm_conversations")
    op.drop_table("ml_models")
    op.drop_table("backtest_sessions")
    op.drop_table("strategies")
    op.drop_table("connector_sessions")
    op.drop_table("broker_connections")
    op.drop_table("subscriptions")
    op.drop_table("users")
