#!/usr/bin/env python3
"""
Run database migrations.
This script can be run manually or as part of deployment process.
"""
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_migrations():
    """Run all pending migrations."""
    print("=" * 60)
    print("Running database migrations...")
    print("=" * 60)

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set!")
        sys.exit(1)

    print(f"Database: {db_url.split('@')[-1]}")  # Print only host/db part for security

    # Create Alembic config
    alembic_ini = Path(__file__).parent / "alembic.ini"
    if not alembic_ini.exists():
        print(f"ERROR: alembic.ini not found at {alembic_ini}")
        sys.exit(1)

    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", db_url)

    try:
        # Run migrations
        print("\nChecking current database version...")
        command.current(config, verbose=True)

        print("\nUpgrading to latest version...")
        command.upgrade(config, "head")

        print("\n" + "=" * 60)
        print("✅ Migrations completed successfully!")
        print("=" * 60)

        # Show final version
        print("\nCurrent database version:")
        command.current(config, verbose=True)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Migration failed: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
