#!/usr/bin/env python3
"""
Seed default ML models to database.

Run this script to insert/update default model data in production.
Safe to run multiple times - uses INSERT ON CONFLICT to avoid duplicates.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, create_engine
from app.config import get_settings


def seed_default_models():
    """Insert default models into database."""
    print("🌱 Seeding default ML models...")

    settings = get_settings()
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'default_ml_models'
            );
        """))

        table_exists = result.fetchone()[0]

        if not table_exists:
            print("❌ Table 'default_ml_models' does not exist!")
            print("   Run migrations first: alembic upgrade head")
            return False

        print("✅ Table 'default_ml_models' exists")

        # Insert default models (with ON CONFLICT to avoid duplicates)
        print("\n📥 Inserting default models...")

        conn.execute(text("""
            INSERT INTO default_ml_models (
                id, symbol, model_path, model_id,
                win_rate, profit_factor, accuracy, total_trades,
                is_system_default
            ) VALUES
            (
                gen_random_uuid(),
                'XAUUSD',
                'models/model_xgboost_20251212_235414.pkl',
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
                'models/eurusd/forex-optimized/model_forex_xgboost_20251213_112218.pkl',
                'model_forex_xgboost_20251213_112218',
                79.1,
                3.77,
                60.3,
                4675,
                TRUE
            ),
            (
                gen_random_uuid(),
                'BTCUSD',
                'models/btcusd/crypto-optimized/model_crypto_xgboost_20251213_104319.pkl',
                'model_crypto_xgboost_20251213_104319',
                NULL,
                1.14,
                NULL,
                NULL,
                TRUE
            )
            ON CONFLICT (symbol) DO UPDATE SET
                model_path = EXCLUDED.model_path,
                model_id = EXCLUDED.model_id,
                win_rate = EXCLUDED.win_rate,
                profit_factor = EXCLUDED.profit_factor,
                accuracy = EXCLUDED.accuracy,
                total_trades = EXCLUDED.total_trades,
                updated_at = NOW();
        """))

        conn.commit()

        # Verify inserted data
        result = conn.execute(text("""
            SELECT symbol, model_id, win_rate, profit_factor
            FROM default_ml_models
            ORDER BY symbol;
        """))

        models = result.fetchall()

        print(f"\n✅ Successfully seeded {len(models)} default models:")
        for model in models:
            symbol, model_id, win_rate, pf = model
            wr_str = f"{win_rate:.1f}%" if win_rate else "N/A"
            pf_str = f"{pf:.2f}" if pf else "N/A"
            print(f"   • {symbol}: {model_id[:30]}... (WR: {wr_str}, PF: {pf_str})")

        return True


def main():
    """Run seeding."""
    try:
        success = seed_default_models()

        if success:
            print("\n✅ Database seeding completed successfully!")
            print("   Default models are now available in the application.\n")
            return 0
        else:
            print("\n❌ Seeding failed. Check errors above.\n")
            return 1

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
