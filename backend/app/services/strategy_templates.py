"""Strategy Templates for Quick Start

Pre-configured strategy templates optimized for different trading styles.
Users can create strategies from these templates for ML auto-trading.
"""

STRATEGY_TEMPLATES = {
    "conservative": {
        "name_suffix": "Conservative Auto-Trading",
        "description": "Low risk strategy with small positions and high confidence threshold",
        "config": {
            # Risk Management
            "max_lot_size": 0.01,
            "min_lot_size": 0.01,
            "default_lot_size": 0.01,
            "max_daily_loss": 50.0,
            "max_drawdown_pct": 3.0,
            "max_open_positions": 1,

            # ML Settings
            "min_confidence": 0.75,  # Require 75% confidence
            "use_ml_tp_sl": True,

            # Position Management
            "max_trades_per_day": 3,
            "cooldown_minutes": 60,

            # Time Filters
            "trading_hours": {
                "enabled": True,
                "start": "01:00",
                "end": "22:00",
                "timezone": "UTC"
            },

            # Filters
            "use_session_filter": True,
            "use_volatility_filter": True,
            "use_trend_filter": True,
        }
    },

    "balanced": {
        "name_suffix": "Balanced Auto-Trading",
        "description": "Medium risk strategy with standard settings for most traders",
        "config": {
            # Risk Management
            "max_lot_size": 0.02,
            "min_lot_size": 0.01,
            "default_lot_size": 0.02,
            "max_daily_loss": 100.0,
            "max_drawdown_pct": 5.0,
            "max_open_positions": 2,

            # ML Settings
            "min_confidence": 0.65,  # Standard 65% confidence
            "use_ml_tp_sl": True,

            # Position Management
            "max_trades_per_day": 5,
            "cooldown_minutes": 30,

            # Time Filters
            "trading_hours": {
                "enabled": True,
                "start": "00:00",
                "end": "23:00",
                "timezone": "UTC"
            },

            # Filters
            "use_session_filter": True,
            "use_volatility_filter": True,
            "use_trend_filter": False,
        }
    },

    "aggressive": {
        "name_suffix": "Aggressive Auto-Trading",
        "description": "Higher risk strategy with larger positions and more frequent trading",
        "config": {
            # Risk Management
            "max_lot_size": 0.05,
            "min_lot_size": 0.01,
            "default_lot_size": 0.03,
            "max_daily_loss": 200.0,
            "max_drawdown_pct": 10.0,
            "max_open_positions": 3,

            # ML Settings
            "min_confidence": 0.60,  # Lower threshold for more trades
            "use_ml_tp_sl": True,

            # Position Management
            "max_trades_per_day": 10,
            "cooldown_minutes": 15,

            # Time Filters
            "trading_hours": {
                "enabled": False,  # Trade 24/7
            },

            # Filters
            "use_session_filter": False,
            "use_volatility_filter": False,
            "use_trend_filter": False,
        }
    },

    "scalping": {
        "name_suffix": "Scalping Auto-Trading",
        "description": "Quick in-and-out trades with tight stops and small targets",
        "config": {
            # Risk Management
            "max_lot_size": 0.03,
            "min_lot_size": 0.01,
            "default_lot_size": 0.02,
            "max_daily_loss": 150.0,
            "max_drawdown_pct": 5.0,
            "max_open_positions": 1,

            # ML Settings
            "min_confidence": 0.70,
            "use_ml_tp_sl": True,
            "tp_multiplier": 0.5,  # Smaller targets
            "sl_multiplier": 1.0,

            # Position Management
            "max_trades_per_day": 15,
            "cooldown_minutes": 10,

            # Time Filters
            "trading_hours": {
                "enabled": True,
                "start": "06:00",  # Active trading sessions only
                "end": "20:00",
                "timezone": "UTC"
            },

            # Filters
            "use_session_filter": True,
            "use_volatility_filter": True,
            "use_trend_filter": True,
        }
    },
}


def get_template(template_name: str) -> dict:
    """Get a strategy template by name."""
    return STRATEGY_TEMPLATES.get(template_name, STRATEGY_TEMPLATES["balanced"])


def list_templates() -> list:
    """List all available templates with descriptions."""
    return [
        {
            "id": name,
            "name": f"{name.capitalize()} Strategy",
            "description": template["description"],
            "risk_level": _get_risk_level(name),
            "recommended_for": _get_recommendations(name),
        }
        for name, template in STRATEGY_TEMPLATES.items()
    ]


def _get_risk_level(template_name: str) -> str:
    """Get risk level for a template."""
    risk_levels = {
        "conservative": "Low",
        "balanced": "Medium",
        "aggressive": "High",
        "scalping": "Medium-High",
    }
    return risk_levels.get(template_name, "Medium")


def _get_recommendations(template_name: str) -> list:
    """Get recommendations for who should use this template."""
    recommendations = {
        "conservative": ["Beginners", "Risk-averse traders", "Small accounts"],
        "balanced": ["Intermediate traders", "Most users", "Standard accounts"],
        "aggressive": ["Experienced traders", "Larger accounts", "High risk tolerance"],
        "scalping": ["Active traders", "Quick decision makers", "Experienced with ML"],
    }
    return recommendations.get(template_name, ["Most users"])
