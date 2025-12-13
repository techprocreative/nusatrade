#!/usr/bin/env python3
"""
Fix model paths in production database.

This script updates the model_path column to remove 'models/' prefix
so paths are relative to the models/ directory.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, create_engine
from app.config import get_settings


def fix_model_paths():
    """Fix model paths in default_ml_models table."""
    print("🔧 Fixing model paths in database...")

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
            return False

        print("✅ Table 'default_ml_models' exists")

        # Show current paths
        print("\n📋 Current paths:")
        result = conn.execute(text("""
            SELECT symbol, model_path
            FROM default_ml_models
            ORDER BY symbol;
        """))
        for row in result.fetchall():
            print(f"   {row[0]}: {row[1]}")

        # Fix XAUUSD path
        print("\n🔄 Updating XAUUSD path...")
        result = conn.execute(text("""
            UPDATE default_ml_models
            SET model_path = 'model_xgboost_20251212_235414.pkl',
                updated_at = NOW()
            WHERE symbol = 'XAUUSD' AND model_path LIKE 'models/%'
            RETURNING symbol, model_path;
        """))
        updated = result.fetchall()
        if updated:
            print(f"   ✅ Updated {len(updated)} row(s)")

        # Fix EURUSD path
        print("🔄 Updating EURUSD path...")
        result = conn.execute(text("""
            UPDATE default_ml_models
            SET model_path = 'eurusd/forex-optimized/model_forex_xgboost_20251213_112218.pkl',
                updated_at = NOW()
            WHERE symbol = 'EURUSD' AND model_path LIKE 'models/%'
            RETURNING symbol, model_path;
        """))
        updated = result.fetchall()
        if updated:
            print(f"   ✅ Updated {len(updated)} row(s)")

        # Fix BTCUSD path
        print("🔄 Updating BTCUSD path...")
        result = conn.execute(text("""
            UPDATE default_ml_models
            SET model_path = 'btcusd/crypto-optimized/model_crypto_xgboost_20251213_104319.pkl',
                updated_at = NOW()
            WHERE symbol = 'BTCUSD' AND model_path LIKE 'models/%'
            RETURNING symbol, model_path;
        """))
        updated = result.fetchall()
        if updated:
            print(f"   ✅ Updated {len(updated)} row(s)")

        conn.commit()

        # Verify changes
        print("\n✅ Final paths:")
        result = conn.execute(text("""
            SELECT symbol, model_path, win_rate, profit_factor
            FROM default_ml_models
            ORDER BY symbol;
        """))

        models = result.fetchall()
        for model in models:
            symbol, model_path, win_rate, pf = model
            wr_str = f"{win_rate:.1f}%" if win_rate else "N/A"
            pf_str = f"{pf:.2f}" if pf else "N/A"
            print(f"   • {symbol}: {model_path}")
            print(f"     WR: {wr_str}, PF: {pf_str}")

        return True


def main():
    """Run fix."""
    try:
        success = fix_model_paths()

        if success:
            print("\n✅ Model paths fixed successfully!\n")
            return 0
        else:
            print("\n❌ Fix failed. Check errors above.\n")
            return 1

    except Exception as e:
        print(f"\n❌ Error during fix: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
