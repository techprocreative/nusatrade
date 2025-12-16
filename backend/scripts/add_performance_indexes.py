"""
Database Performance Indexes Migration

Adds indexes for frequently queried columns to improve performance
of auto-trading, strategy lookups, and analytics queries.
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres.nhmihfusyxdjvlisdjvt:TFh7eUP0SFRLGlGn@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

# Performance indexes to create
INDEXES = [
    # ML Models - Auto-trading queries
    {
        "name": "idx_ml_models_active_strategy",
        "table": "ml_models",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_ml_models_active_strategy
            ON ml_models(user_id, is_active, strategy_id)
            WHERE is_active = true;
        """,
        "description": "Speed up active model queries with strategy filtering"
    },
    {
        "name": "idx_ml_models_symbol",
        "table": "ml_models",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_ml_models_symbol
            ON ml_models(symbol, is_active);
        """,
        "description": "Speed up symbol-based model lookups"
    },

    # Strategies - Selector queries
    {
        "name": "idx_strategies_symbol_active",
        "table": "strategies",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_strategies_symbol_active
            ON strategies(symbol, is_active, is_public)
            WHERE is_active = true;
        """,
        "description": "Speed up strategy selector queries"
    },
    {
        "name": "idx_strategies_type_public",
        "table": "strategies",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_strategies_type_public
            ON strategies(strategy_type, is_public)
            WHERE is_public = true;
        """,
        "description": "Speed up template strategy lookups"
    },

    # ML Predictions - Analytics queries
    {
        "name": "idx_predictions_model_date",
        "table": "ml_predictions",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_predictions_model_date
            ON ml_predictions(model_id, created_at DESC);
        """,
        "description": "Speed up prediction history queries"
    },

    # Trades - Performance analytics
    {
        "name": "idx_trades_user_date",
        "table": "trades",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_trades_user_date
            ON trades(user_id, created_at DESC);
        """,
        "description": "Speed up trade history and analytics"
    },
    {
        "name": "idx_trades_status",
        "table": "trades",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_trades_status
            ON trades(user_id, status)
            WHERE status = 'closed';
        """,
        "description": "Speed up daily P/L calculations"
    },

    # Positions - Real-time queries
    {
        "name": "idx_positions_user_open",
        "table": "positions",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_positions_user_open
            ON positions(user_id, status)
            WHERE status = 'open';
        """,
        "description": "Speed up open positions queries"
    },

    # Broker Connections - Active connection lookups
    {
        "name": "idx_connections_user_active",
        "table": "broker_connections",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_connections_user_active
            ON broker_connections(user_id, is_active)
            WHERE is_active = true;
        """,
        "description": "Speed up active connection lookups"
    },
]


def create_indexes():
    """Create all performance indexes."""
    engine = create_engine(DATABASE_URL)

    print("=" * 80)
    print("CREATING PERFORMANCE INDEXES")
    print("=" * 80)

    with engine.connect() as conn:
        created_count = 0
        skipped_count = 0

        for idx in INDEXES:
            print(f"\nCreating {idx['name']}...")
            print(f"  Table: {idx['table']}")
            print(f"  Purpose: {idx['description']}")

            try:
                conn.execute(text(idx['sql']))
                conn.commit()
                print(f"  ✅ Created successfully")
                created_count += 1
            except Exception as e:
                if "already exists" in str(e):
                    print(f"  ⏭️  Already exists, skipping")
                    skipped_count += 1
                else:
                    print(f"  ❌ Error: {e}")

    print("\n" + "=" * 80)
    print(f"✅ INDEXES MIGRATION COMPLETED")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print("=" * 80)


def verify_indexes():
    """Verify that all indexes were created."""
    engine = create_engine(DATABASE_URL)

    print("\n" + "=" * 80)
    print("VERIFYING INDEXES")
    print("=" * 80)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE indexname LIKE 'idx_%'
            ORDER BY tablename, indexname;
        """))

        indexes = result.fetchall()

        print(f"\nTotal custom indexes found: {len(indexes)}\n")

        current_table = None
        for idx in indexes:
            if idx[1] != current_table:
                current_table = idx[1]
                print(f"\n📊 {current_table}:")

            print(f"  - {idx[2]}")


if __name__ == "__main__":
    create_indexes()
    verify_indexes()
