"""
Risk Management Settings Model

Adds user-specific risk management configuration.
"""

import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres.nhmihfusyxdjvlisdjvt:TFh7eUP0SFRLGlGn@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def add_risk_settings_to_users():
    """Add default risk settings to existing users."""

    engine = create_engine(DATABASE_URL)

    default_risk_settings = {
        "max_daily_loss": 500.0,
        "max_positions": 10,
        "max_lot_size": 0.5,
        "confidence_threshold": 0.70,
        "daily_trade_limit": 20,
        "max_drawdown_percent": 15.0,
        "enabled": True
    }

    print("=" * 80)
    print("ADDING DEFAULT RISK SETTINGS TO USERS")
    print("=" * 80)

    with engine.connect() as conn:
        # Get all users without risk settings
        result = conn.execute(text("""
            SELECT id, email, settings
            FROM users
        """))

        users = result.fetchall()
        updated = 0

        for user in users:
            user_id, email, current_settings = user

            # Parse current settings (JSON)
            if current_settings is None:
                current_settings = {}

            # Add risk_management if not exists
            if "risk_management" not in current_settings:
                current_settings["risk_management"] = default_risk_settings

                # Update user settings with proper JSON
                conn.execute(
                    text("""
                        UPDATE users
                        SET settings = CAST(:settings AS jsonb)
                        WHERE id = :user_id
                    """),
                    {
                        "settings": json.dumps(current_settings),
                        "user_id": user_id
                    }
                )

                print(f"✅ Added risk settings to user: {email}")
                updated += 1
            else:
                print(f"⏭️  User {email} already has risk settings")

        conn.commit()

    print("\n" + "=" * 80)
    print(f"✅ RISK SETTINGS MIGRATION COMPLETED")
    print(f"   Users updated: {updated}")
    print("=" * 80)


if __name__ == "__main__":
    add_risk_settings_to_users()
