#!/usr/bin/env python3
"""
Admin User Seed Script
Creates an initial admin user for the NusaTrade platform.

Usage:
    python scripts/seed_admin.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import password hashing from the app's security module (same as backend uses)
from app.core.security import get_password_hash


def create_admin_user():
    """Create an admin user in the database."""
    
    # Get configuration from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in environment")
        sys.exit(1)
    
    # Default admin credentials (override with environment variables)
    admin_email = os.getenv("ADMIN_EMAIL", "admin@nusatrade.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    admin_name = os.getenv("ADMIN_NAME", "Admin User")
    
    print(f"🔧 Creating admin user with email: {admin_email}")
    
    # Hash password using same method as backend
    print("🔐 Hashing password...")
    password_hash = get_password_hash(admin_password)
    print("✅ Password hashed successfully")
    
    # Create database connection
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if admin user already exists
        result = session.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": admin_email}
        )
        existing_user = result.fetchone()
        
        if existing_user:
            print(f"⚠️  User with email {admin_email} already exists!")
            
            # Check if already admin
            if existing_user[2] == "admin":
                print(f"✅ User is already an admin.")
                # Update password anyway
                session.execute(
                    text("UPDATE users SET password_hash = :password_hash WHERE email = :email"),
                    {"email": admin_email, "password_hash": password_hash}
                )
                session.commit()
                print(f"✅ Password updated for existing admin user.")
            else:
                # Update to admin role and password
                session.execute(
                    text("UPDATE users SET role = 'admin', password_hash = :password_hash WHERE email = :email"),
                    {"email": admin_email, "password_hash": password_hash}
                )
                session.commit()
                print(f"✅ Updated user role to 'admin' and password")
        else:
            # Create new admin user
            session.execute(
                text("""
                    INSERT INTO users (id, email, password_hash, full_name, role, subscription_tier, totp_enabled)
                    VALUES (gen_random_uuid(), :email, :password_hash, :full_name, 'admin', 'enterprise', false)
                """),
                {
                    "email": admin_email,
                    "password_hash": password_hash,
                    "full_name": admin_name,
                }
            )
            session.commit()
            print(f"✅ Admin user created successfully!")
        
        print(f"")
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Password: {admin_password}")
        print(f"👤 Name: {admin_name}")
        print(f"🎭 Role: admin")
        print(f"")
        print(f"⚠️  IMPORTANT: Change the password after first login!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()
    
    print("")
    print("🎉 Done! You can now login at /login with admin credentials.")


if __name__ == "__main__":
    print("")
    print("=" * 50)
    print("  NusaTrade Admin User Seed Script")
    print("=" * 50)
    print("")
    create_admin_user()
