"""
Script to populate default strategy templates for pretrained models.

These strategies are optimized for each symbol and designed to work
seamlessly with pretrained ML models.
"""

import sys
import os
from pathlib import Path
import json

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from uuid import uuid4
from datetime import datetime, UTC

# Database connection
DATABASE_URL = "postgresql+psycopg2://postgres.nhmihfusyxdjvlisdjvt:TFh7eUP0SFRLGlGn@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

# Default strategies optimized for each symbol
DEFAULT_STRATEGIES = {
    "XAUUSD": {
        "name": "Gold Momentum Strategy (XGBoost Optimized)",
        "description": "Conservative momentum strategy optimized for XAUUSD. Uses RSI + MACD confirmation with session filters. Best for Asian & London sessions. 2:1 R:R with trailing stops.",
        "strategy_type": "preset",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "entry_rules": [
            {
                "indicator": "RSI",
                "period": 14,
                "condition": "oversold_buy",
                "threshold": 30,
                "direction": "BUY",
                "description": "RSI below 30 for BUY signal"
            },
            {
                "indicator": "RSI",
                "period": 14,
                "condition": "overbought_sell",
                "threshold": 70,
                "direction": "SELL",
                "description": "RSI above 70 for SELL signal"
            },
            {
                "indicator": "MACD",
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "condition": "bullish_crossover",
                "direction": "BUY",
                "description": "MACD bullish crossover confirmation"
            },
            {
                "indicator": "MACD",
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "condition": "bearish_crossover",
                "direction": "SELL",
                "description": "MACD bearish crossover confirmation"
            },
            {
                "type": "session_filter",
                "allowed_sessions": ["asian", "london"],
                "description": "Trade only during Asian and London sessions"
            }
        ],
        "exit_rules": [
            {
                "type": "trailing_stop",
                "activation_pips": 25,
                "trail_distance_pips": 20,
                "description": "Trailing stop activates after 25 pips profit"
            },
            {
                "type": "take_profit",
                "method": "risk_reward",
                "ratio": 2.0,
                "description": "Take profit at 2:1 risk-reward ratio"
            }
        ],
        "risk_management": {
            "stop_loss_type": "atr_based",
            "stop_loss_value": 2.5,
            "take_profit_type": "risk_reward",
            "take_profit_value": 2.0,
            "risk_per_trade_percent": 2.0,
            "max_position_size": 0.1,
            "trailing_stop": {
                "enabled": True,
                "activation_pips": 25,
                "trail_distance_pips": 20,
                "breakeven_pips": 15
            }
        },
        "parameters": {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "atr_period": 14,
            "atr_multiplier": 2.5
        },
        "indicators": ["RSI", "MACD", "ATR", "EMA"]
    },
    "EURUSD": {
        "name": "EUR/USD Trend Following Strategy",
        "description": "Professional trend-following strategy for EURUSD. Uses EMA crossover with ADX strength filter. Optimized for H1 timeframe with 1.5:1 minimum R:R.",
        "strategy_type": "preset",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "entry_rules": [
            {
                "indicator": "EMA",
                "fast_period": 20,
                "slow_period": 50,
                "condition": "bullish_crossover",
                "direction": "BUY",
                "description": "EMA 20 crosses above EMA 50"
            },
            {
                "indicator": "EMA",
                "fast_period": 20,
                "slow_period": 50,
                "condition": "bearish_crossover",
                "direction": "SELL",
                "description": "EMA 20 crosses below EMA 50"
            },
            {
                "indicator": "ADX",
                "period": 14,
                "condition": "strong_trend",
                "threshold": 25,
                "description": "ADX above 25 confirms strong trend"
            },
            {
                "indicator": "RSI",
                "period": 14,
                "condition": "not_extreme",
                "min_threshold": 35,
                "max_threshold": 65,
                "description": "RSI between 35-65 (avoid extremes)"
            }
        ],
        "exit_rules": [
            {
                "type": "trailing_stop",
                "activation_pips": 20,
                "trail_distance_pips": 15,
                "description": "Trailing stop after 20 pips profit"
            },
            {
                "type": "take_profit",
                "method": "risk_reward",
                "ratio": 1.5,
                "description": "TP at 1.5:1 R:R"
            }
        ],
        "risk_management": {
            "stop_loss_type": "atr_based",
            "stop_loss_value": 2.0,
            "take_profit_type": "risk_reward",
            "take_profit_value": 1.5,
            "risk_per_trade_percent": 2.0,
            "max_position_size": 0.15,
            "trailing_stop": {
                "enabled": True,
                "activation_pips": 20,
                "trail_distance_pips": 15,
                "breakeven_pips": 12
            }
        },
        "parameters": {
            "ema_fast": 20,
            "ema_slow": 50,
            "adx_period": 14,
            "adx_threshold": 25,
            "rsi_period": 14,
            "atr_period": 14,
            "atr_multiplier": 2.0
        },
        "indicators": ["EMA", "ADX", "RSI", "ATR"]
    },
    "GBPUSD": {
        "name": "GBP/USD Volatility Breakout Strategy",
        "description": "Volatility breakout strategy for GBPUSD. Uses Bollinger Bands with volume confirmation. Best for volatile London session. Conservative 2:1 R:R.",
        "strategy_type": "preset",
        "symbol": "GBPUSD",
        "timeframe": "H1",
        "entry_rules": [
            {
                "indicator": "BBANDS",
                "period": 20,
                "std_dev": 2,
                "condition": "price_below_lower",
                "direction": "BUY",
                "description": "Price touches lower Bollinger Band"
            },
            {
                "indicator": "BBANDS",
                "period": 20,
                "std_dev": 2,
                "condition": "price_above_upper",
                "direction": "SELL",
                "description": "Price touches upper Bollinger Band"
            },
            {
                "indicator": "RSI",
                "period": 14,
                "condition": "oversold_buy",
                "threshold": 30,
                "direction": "BUY",
                "description": "RSI confirmation for oversold"
            },
            {
                "indicator": "RSI",
                "period": 14,
                "condition": "overbought_sell",
                "threshold": 70,
                "direction": "SELL",
                "description": "RSI confirmation for overbought"
            },
            {
                "type": "session_filter",
                "allowed_sessions": ["london", "newyork"],
                "description": "Trade during London and NY sessions"
            }
        ],
        "exit_rules": [
            {
                "type": "trailing_stop",
                "activation_pips": 30,
                "trail_distance_pips": 20,
                "description": "Trailing stop after 30 pips"
            },
            {
                "type": "take_profit",
                "method": "risk_reward",
                "ratio": 2.0,
                "description": "TP at 2:1 R:R"
            }
        ],
        "risk_management": {
            "stop_loss_type": "atr_based",
            "stop_loss_value": 2.5,
            "take_profit_type": "risk_reward",
            "take_profit_value": 2.0,
            "risk_per_trade_percent": 1.5,
            "max_position_size": 0.1,
            "trailing_stop": {
                "enabled": True,
                "activation_pips": 30,
                "trail_distance_pips": 20,
                "breakeven_pips": 18
            }
        },
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_period": 14,
            "atr_multiplier": 2.5
        },
        "indicators": ["BBANDS", "RSI", "ATR"]
    },
    "USDJPY": {
        "name": "USD/JPY Range Trading Strategy",
        "description": "Range-bound trading strategy for USDJPY. Uses Stochastic oscillator with support/resistance levels. Optimized for Asian session. 1.8:1 R:R.",
        "strategy_type": "preset",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "entry_rules": [
            {
                "indicator": "STOCH",
                "k_period": 14,
                "d_period": 3,
                "condition": "oversold_crossover",
                "threshold": 20,
                "direction": "BUY",
                "description": "Stochastic oversold crossover"
            },
            {
                "indicator": "STOCH",
                "k_period": 14,
                "d_period": 3,
                "condition": "overbought_crossover",
                "threshold": 80,
                "direction": "SELL",
                "description": "Stochastic overbought crossover"
            },
            {
                "indicator": "RSI",
                "period": 14,
                "condition": "not_extreme",
                "min_threshold": 30,
                "max_threshold": 70,
                "description": "RSI not at extremes"
            },
            {
                "type": "session_filter",
                "allowed_sessions": ["asian", "london"],
                "description": "Best for Asian and early London"
            }
        ],
        "exit_rules": [
            {
                "type": "trailing_stop",
                "activation_pips": 25,
                "trail_distance_pips": 18,
                "description": "Trailing stop after 25 pips"
            },
            {
                "type": "take_profit",
                "method": "risk_reward",
                "ratio": 1.8,
                "description": "TP at 1.8:1 R:R"
            }
        ],
        "risk_management": {
            "stop_loss_type": "atr_based",
            "stop_loss_value": 2.0,
            "take_profit_type": "risk_reward",
            "take_profit_value": 1.8,
            "risk_per_trade_percent": 2.0,
            "max_position_size": 0.12,
            "trailing_stop": {
                "enabled": True,
                "activation_pips": 25,
                "trail_distance_pips": 18,
                "breakeven_pips": 15
            }
        },
        "parameters": {
            "stoch_k": 14,
            "stoch_d": 3,
            "stoch_overbought": 80,
            "stoch_oversold": 20,
            "rsi_period": 14,
            "atr_period": 14,
            "atr_multiplier": 2.0
        },
        "indicators": ["STOCH", "RSI", "ATR"]
    }
}


def populate_strategies():
    """Populate default strategies in database."""
    engine = create_engine(DATABASE_URL)

    print("=" * 80)
    print("POPULATING DEFAULT STRATEGY TEMPLATES")
    print("=" * 80)

    with engine.connect() as conn:
        for symbol, strategy_data in DEFAULT_STRATEGIES.items():
            strategy_id = str(uuid4())

            print(f"\nCreating strategy for {symbol}...")
            print(f"  Name: {strategy_data['name']}")
            print(f"  Description: {strategy_data['description'][:80]}...")

            # Insert strategy
            conn.execute(
                text("""
                    INSERT INTO strategies (
                        id, name, description, strategy_type, symbol, timeframe,
                        entry_rules, exit_rules, risk_management, parameters, indicators,
                        is_active, is_public, created_at, updated_at
                    ) VALUES (
                        :id, :name, :description, :strategy_type, :symbol, :timeframe,
                        CAST(:entry_rules AS jsonb), CAST(:exit_rules AS jsonb),
                        CAST(:risk_management AS jsonb), CAST(:parameters AS jsonb),
                        CAST(:indicators AS jsonb),
                        :is_active, :is_public, :created_at, :updated_at
                    )
                """),
                {
                    "id": strategy_id,
                    "name": strategy_data["name"],
                    "description": strategy_data["description"],
                    "strategy_type": strategy_data["strategy_type"],
                    "symbol": strategy_data["symbol"],
                    "timeframe": strategy_data["timeframe"],
                    "entry_rules": json.dumps(strategy_data["entry_rules"]),
                    "exit_rules": json.dumps(strategy_data["exit_rules"]),
                    "risk_management": json.dumps(strategy_data["risk_management"]),
                    "parameters": json.dumps(strategy_data["parameters"]),
                    "indicators": json.dumps(strategy_data["indicators"]),
                    "is_active": True,  # Active by default
                    "is_public": True,  # Public template
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC)
                }
            )

            conn.commit()
            print(f"  ✅ Created: {strategy_id}")

    print("\n" + "=" * 80)
    print("✅ ALL DEFAULT STRATEGIES CREATED SUCCESSFULLY")
    print("=" * 80)

    # Verify
    with engine.connect() as conn:
        count = conn.execute(text("""
            SELECT COUNT(*) FROM strategies
            WHERE strategy_type = 'preset' AND is_public = true
        """)).fetchone()[0]

        print(f"\nTotal public preset strategies in database: {count}")


if __name__ == "__main__":
    populate_strategies()
