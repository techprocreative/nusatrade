#!/usr/bin/env python3
"""
Seed ML Scalping Model into the database.

This script registers the trained scalping model so it can be used
by the auto-trading system.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.ml import MLModel
from app.models.user import User


def seed_scalping_model(db: Session):
    """Seed the scalping model into the database."""
    
    print("=" * 60)
    print("🚀 Seeding ML Scalping Model")
    print("=" * 60)
    
    # Find admin or first user
    user = db.query(User).first()
    
    if not user:
        print("❌ No users found in database. Create a user first.")
        return False
    
    print(f"📧 Using user: {user.email}")
    
    # Check if model already exists
    existing = db.query(MLModel).filter(
        MLModel.name == "XAUUSD M15 Scalping Model",
        MLModel.user_id == user.id,
    ).first()
    
    if existing:
        print(f"⚠️  Model already exists: {existing.name}")
        print(f"   ID: {existing.id}")
        print(f"   Active: {existing.is_active}")
        
        # Optionally update and activate
        if not existing.is_active:
            existing.is_active = True
            existing.file_path = "models/model_realistic_xauusd_M15_20251219_100151.pkl"
            db.commit()
            print("   → Activated existing model")
        
        return True
    
    # Create new model entry
    # Note: MLModel schema uses 'config' for training config and doesn't have description
    model = MLModel(
        id=uuid4(),
        user_id=user.id,
        name="XAUUSD M15 Scalping Model",
        symbol="XAUUSD",
        timeframe="M15",
        model_type="lightgbm",
        file_path="models/model_realistic_xauusd_M15_20251219_100151.pkl",
        config={
            "lookahead": 8,
            "tp_pips": 5.0,
            "sl_pips": 8.0,
            "confidence_threshold": 0.55,
            "strategy_type": "ml_scalping",
            "description": "High win-rate scalping model. TP=5 pips, SL=8 pips. 58% win rate at 55% confidence.",
        },
        performance_metrics={
            "win_rate": 58.1,
            "total_trades": 544,
            "accuracy": 44.81,
            "risk_reward_ratio": 0.625,
            "feature_importance": {
                "hour": 6488,
                "ret_1": 6164,
                "atr_norm": 5460,
                "body": 4796,
                "vol_ratio": 4543,
            },
        },
        is_active=True,  # Activate immediately for testing
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    db.add(model)
    db.commit()
    db.refresh(model)
    
    print(f"\n✅ Model created and activated!")
    print(f"   ID: {model.id}")
    print(f"   Name: {model.name}")
    print(f"   Symbol: {model.symbol}")
    print(f"   Timeframe: {model.timeframe}")
    print(f"   File: {model.file_path}")
    print(f"   Active: {model.is_active}")
    
    return True


def seed_h1_model(db: Session):
    """Seed the H1 profitable model as well."""
    
    print("\n" + "=" * 60)
    print("🚀 Seeding ML H1 Profitable Model")
    print("=" * 60)
    
    user = db.query(User).first()
    
    if not user:
        return False
    
    # Check if model already exists
    existing = db.query(MLModel).filter(
        MLModel.name == "XAUUSD H1 Profitable Model",
        MLModel.user_id == user.id,
    ).first()
    
    if existing:
        print(f"⚠️  Model already exists: {existing.name}")
        return True
    
    model = MLModel(
        id=uuid4(),
        user_id=user.id,
        name="XAUUSD H1 Profitable Model",
        symbol="XAUUSD",
        timeframe="H1",
        model_type="xgboost",
        file_path="models/model_xgboost_20251212_235414.pkl",
        config={
            "confidence_threshold": 0.70,
            "use_session_filter": True,
            "use_volatility_filter": True,
            "strategy_type": "ml_profitable",
            "description": "Conservative swing trading model with 75% win rate.",
        },
        performance_metrics={
            "win_rate": 75.0,
            "profit_factor": 2.02,
            "max_drawdown": 7.20,
        },
        is_active=False,  # Keep inactive by default
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    db.add(model)
    db.commit()
    
    print(f"✅ H1 Model created!")
    print(f"   ID: {model.id}")
    print(f"   Active: {model.is_active}")
    
    return True


def main():
    """Main entry point."""
    try:
        db = SessionLocal()
        
        try:
            success1 = seed_scalping_model(db)
            success2 = seed_h1_model(db)
            
            if success1 or success2:
                print("\n" + "=" * 60)
                print("🎉 Seeding complete!")
                print("=" * 60)
                print("\nNext steps:")
                print("1. Start the backend server")
                print("2. The scalping model is now active and ready")
                print("3. Auto-trading will use the M15 scalping model")
                return 0
            else:
                print("\n❌ Seeding failed")
                return 1
        finally:
            db.close()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
