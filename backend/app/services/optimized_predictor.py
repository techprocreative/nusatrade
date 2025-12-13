"""
Production-Ready ML Prediction Service
Uses optimal configuration for profitable trading.

This service:
1. Loads optimal configuration
2. Applies all filters (confidence, session, volatility, trend)
3. Returns high-quality BUY/SELL/HOLD signals
4. Includes TP/SL prices based on optimal ratio
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, 'backend/app/ml')
from improved_features import ImprovedFeatureEngineer


class OptimizedTradingPredictor:
    """Production-ready predictor with optimal filters."""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.75,
        tp_sl_ratio: float = 2.0,
        use_session_filter: bool = True,
        use_volatility_filter: bool = True,
        use_trend_filter: bool = True
    ):
        """
        Initialize predictor with optimal configuration.

        Args:
            model_path: Path to trained model
            confidence_threshold: Minimum confidence to trade (default: 75%)
            tp_sl_ratio: TP to SL ratio (default: 2:1)
            use_session_filter: Only trade London/NY sessions
            use_volatility_filter: Avoid extreme volatility
            use_trend_filter: Only trade with strong trend
        """
        # Load model
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_columns = model_data['feature_columns']
        self.stop_loss_atr = model_data['stop_loss_atr']

        # Configuration
        self.confidence_threshold = confidence_threshold
        self.tp_sl_ratio = tp_sl_ratio
        self.profit_target_atr = self.stop_loss_atr * tp_sl_ratio

        # Filters
        self.use_session_filter = use_session_filter
        self.use_volatility_filter = use_volatility_filter
        self.use_trend_filter = use_trend_filter

        # Feature engineer
        self.engineer = ImprovedFeatureEngineer()

        print(f"✅ Optimized Predictor Loaded")
        print(f"   Confidence Threshold: {confidence_threshold:.0%}")
        print(f"   TP/SL Ratio: {tp_sl_ratio:.1f}:1")
        print(f"   Session Filter: {'ON' if use_session_filter else 'OFF'}")
        print(f"   Volatility Filter: {'ON' if use_volatility_filter else 'OFF'}")
        print(f"   Trend Filter: {'ON' if use_trend_filter else 'OFF'}")

    def predict(
        self,
        current_data: pd.DataFrame,
        spread_pips: float = 3.0
    ) -> Dict[str, Any]:
        """
        Make prediction with optimal filters.

        Args:
            current_data: DataFrame with recent OHLCV data
            spread_pips: Spread cost in pips

        Returns:
            dict with:
                - signal: "BUY", "SELL", or "HOLD"
                - confidence: Model confidence (0-1)
                - entry_price: Suggested entry (with spread)
                - tp_price: Take profit price
                - sl_price: Stop loss price
                - tp_pips: TP distance in pips
                - sl_pips: SL distance in pips
                - filters_passed: Which filters were applied
                - reason: Why HOLD (if applicable)
        """

        # Build features
        df_featured = self.engineer.build_features(current_data)
        df_featured = df_featured.dropna()

        if len(df_featured) == 0:
            return {
                'signal': 'HOLD',
                'reason': 'Insufficient data for features',
                'confidence': 0.0
            }

        # Get last row (most recent)
        row = df_featured.iloc[-1:]

        # Make prediction
        X = row[self.feature_columns]
        X_scaled = self.scaler.transform(X)

        pred_class = self.model.predict(X_scaled)[0]
        pred_proba = self.model.predict_proba(X_scaled)[0]
        confidence = float(pred_proba[pred_class])

        # Initialize result
        result = {
            'signal': 'HOLD',
            'confidence': confidence,
            'filters_passed': [],
            'reason': None
        }

        # Check if model predicts HOLD
        if pred_class == 0:
            result['reason'] = 'Model predicts HOLD'
            return result

        # FILTER 1: Confidence threshold
        if confidence < self.confidence_threshold:
            result['reason'] = f'Low confidence ({confidence:.1%} < {self.confidence_threshold:.0%})'
            return result

        result['filters_passed'].append('Confidence')

        # FILTER 2: Session filter
        if self.use_session_filter:
            hour = int(row['hour'].values[0]) if 'hour' in row.columns else None

            if hour is not None:
                # Only trade during London (8-16) or NY (13-21)
                if not ((8 <= hour < 16) or (13 <= hour < 21)):
                    result['reason'] = f'Outside trading hours (hour={hour}, need London 8-16 or NY 13-21)'
                    return result

            result['filters_passed'].append('Session')

        # FILTER 3: Volatility filter
        if self.use_volatility_filter:
            vol_low = float(row['vol_regime_low'].values[0]) if 'vol_regime_low' in row.columns else 0
            vol_high = float(row['vol_regime_high'].values[0]) if 'vol_regime_high' in row.columns else 0

            if vol_low == 1:
                result['reason'] = 'Volatility too low (avoid ranging market)'
                return result

            if vol_high == 1:
                result['reason'] = 'Volatility too high (avoid chaotic market)'
                return result

            result['filters_passed'].append('Volatility')

        # FILTER 4: Trend filter
        if self.use_trend_filter:
            strong_trend = float(row['strong_trend'].values[0]) if 'strong_trend' in row.columns else 0

            if strong_trend != 1:
                result['reason'] = 'No strong trend (ADX < 25, avoid choppy market)'
                return result

            result['filters_passed'].append('Trend')

        # All filters passed - generate trade signal
        trade_type = "SELL" if pred_class == 1 else "BUY"

        # Calculate entry, TP, SL
        close_price = float(row['close'].values[0])
        atr = float(row['atr'].values[0])

        if pd.isna(atr):
            result['reason'] = 'ATR not available'
            return result

        # Spread cost
        spread_cost = spread_pips / 10000 * close_price

        # Calculate TP/SL distances
        profit_target = atr * self.profit_target_atr
        stop_loss = atr * self.stop_loss_atr

        if trade_type == "BUY":
            entry_price = close_price + spread_cost
            tp_price = entry_price + profit_target
            sl_price = entry_price - stop_loss
        else:  # SELL
            entry_price = close_price - spread_cost
            tp_price = entry_price - profit_target
            sl_price = entry_price + stop_loss

        # Convert to pips
        tp_pips = abs((tp_price - entry_price) / close_price * 10000)
        sl_pips = abs((sl_price - entry_price) / close_price * 10000)

        result = {
            'signal': trade_type,
            'confidence': confidence,
            'entry_price': round(entry_price, 2),
            'tp_price': round(tp_price, 2),
            'sl_price': round(sl_price, 2),
            'tp_pips': round(tp_pips, 1),
            'sl_pips': round(sl_pips, 1),
            'tp_sl_ratio': round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0,
            'current_price': round(close_price, 2),
            'atr': round(atr, 2),
            'filters_passed': result['filters_passed'],
            'reason': 'All filters passed - High quality signal ✅'
        }

        return result

    def load_optimal_config(self, config_file: str = 'optimal_config.txt'):
        """Load optimal configuration from file."""
        if not Path(config_file).exists():
            print(f"⚠️  Config file not found: {config_file}")
            return

        with open(config_file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if line.startswith('confidence_threshold'):
                self.confidence_threshold = float(line.split('=')[1].strip())
            elif line.startswith('tp_sl_ratio'):
                self.tp_sl_ratio = float(line.split('=')[1].strip())
                self.profit_target_atr = self.stop_loss_atr * self.tp_sl_ratio

        print(f"✅ Loaded optimal config from {config_file}")
        print(f"   Confidence: {self.confidence_threshold:.0%}")
        print(f"   TP/SL Ratio: {self.tp_sl_ratio:.1f}:1")


# Example usage
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')

    # Initialize predictor with optimal settings
    predictor = OptimizedTradingPredictor(
        model_path='models/model_improved_gradient_boosting_20251212_223406.pkl',
        confidence_threshold=0.75,
        tp_sl_ratio=2.0,
        use_session_filter=True,
        use_volatility_filter=True,
        use_trend_filter=True
    )

    # Load recent data
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    recent_data = df.tail(100)  # Last 100 candles

    # Get prediction
    prediction = predictor.predict(recent_data)

    print("\n" + "="*60)
    print("PREDICTION RESULT")
    print("="*60)
    print(f"\nSignal: {prediction['signal']}")
    print(f"Confidence: {prediction.get('confidence', 0):.1%}")

    if prediction['signal'] != 'HOLD':
        print(f"\n💰 Trade Setup:")
        print(f"  Entry: ${prediction['entry_price']}")
        print(f"  TP: ${prediction['tp_price']} (+{prediction['tp_pips']:.0f} pips)")
        print(f"  SL: ${prediction['sl_price']} (-{prediction['sl_pips']:.0f} pips)")
        print(f"  Risk/Reward: 1:{prediction['tp_sl_ratio']:.1f}")

    print(f"\n📋 Filters Passed: {', '.join(prediction.get('filters_passed', []))}")
    print(f"📝 Reason: {prediction.get('reason', 'N/A')}")
    print("="*60)
