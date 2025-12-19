#!/usr/bin/env python3
"""
High Win-Rate Scalping Model for XAUUSD.

Strategy: PRIORITIZE WIN RATE over trade frequency.

Techniques:
1. Trend-following only (trade with HTF trend)
2. Session filtering (only prime time)
3. Volatility filtering (avoid low/extreme volatility)
4. Multi-confirmation signals
5. Conservative target definition
6. Probability calibration
"""

import os
import sys
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class HighWinRateFeatures:
    """Feature engineering optimized for high win-rate."""
    
    def __init__(self):
        self.feature_columns = []
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features focused on high-probability setups."""
        df = df.copy()
        
        # Ensure numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # ===== TREND FEATURES (Most Important for Win Rate) =====
        # Multiple EMAs for trend confirmation
        for period in [10, 20, 50, 100, 200]:
            df[f'ema_{period}'] = df['Close'].ewm(span=period).mean()
        
        # Trend direction from multiple EMAs
        df['ema_10_above_20'] = (df['ema_10'] > df['ema_20']).astype(int)
        df['ema_20_above_50'] = (df['ema_20'] > df['ema_50']).astype(int)
        df['ema_50_above_100'] = (df['ema_50'] > df['ema_100']).astype(int)
        df['ema_100_above_200'] = (df['ema_100'] > df['ema_200']).astype(int)
        
        # Trend strength score (0-4)
        df['bull_trend_score'] = (
            df['ema_10_above_20'] + 
            df['ema_20_above_50'] + 
            df['ema_50_above_100'] + 
            df['ema_100_above_200']
        )
        df['bear_trend_score'] = 4 - df['bull_trend_score']
        
        # Strong trend filter
        df['strong_bull_trend'] = (df['bull_trend_score'] >= 3).astype(int)
        df['strong_bear_trend'] = (df['bear_trend_score'] >= 3).astype(int)
        df['has_trend'] = ((df['bull_trend_score'] >= 3) | (df['bear_trend_score'] >= 3)).astype(int)
        
        # Price vs EMAs
        for ema in [20, 50, 100]:
            df[f'price_vs_ema_{ema}'] = (df['Close'] - df[f'ema_{ema}']) / df[f'ema_{ema}']
            df[f'price_above_ema_{ema}'] = (df['Close'] > df[f'ema_{ema}']).astype(int)
        
        # EMA slopes (trend momentum)
        df['ema_20_slope'] = df['ema_20'].pct_change(5)
        df['ema_50_slope'] = df['ema_50'].pct_change(10)
        
        # ===== MOMENTUM FEATURES =====
        # RSI with extreme zones
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        for period in [7, 14, 21]:
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            rs = avg_gain / (avg_loss + 1e-8)
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # RSI zones for entries
        df['rsi_oversold'] = (df['rsi_14'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi_14'] > 70).astype(int)
        df['rsi_neutral'] = ((df['rsi_14'] >= 40) & (df['rsi_14'] <= 60)).astype(int)
        
        # RSI divergence
        df['rsi_slope'] = df['rsi_14'].diff(5)
        df['price_slope'] = df['Close'].pct_change(5)
        df['rsi_price_divergence'] = np.sign(df['rsi_slope']) != np.sign(df['price_slope'])
        
        # MACD
        ema_12 = df['Close'].ewm(span=12).mean()
        ema_26 = df['Close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['macd_bullish'] = ((df['macd'] > df['macd_signal']) & (df['macd_hist'] > 0)).astype(int)
        df['macd_bearish'] = ((df['macd'] < df['macd_signal']) & (df['macd_hist'] < 0)).astype(int)
        
        # Stochastic
        lowest = df['Low'].rolling(14).min()
        highest = df['High'].rolling(14).max()
        df['stoch_k'] = 100 * (df['Close'] - lowest) / (highest - lowest + 1e-8)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        df['stoch_oversold'] = (df['stoch_k'] < 20).astype(int)
        df['stoch_overbought'] = (df['stoch_k'] > 80).astype(int)
        
        # ===== VOLATILITY FEATURES =====
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        
        for period in [5, 10, 14, 20]:
            df[f'atr_{period}'] = df['tr'].rolling(period).mean()
        
        # Volatility regime
        df['volatility_ratio'] = df['atr_5'] / (df['atr_20'] + 1e-8)
        df['normal_volatility'] = ((df['volatility_ratio'] > 0.8) & (df['volatility_ratio'] < 1.5)).astype(int)
        df['high_volatility'] = (df['volatility_ratio'] >= 1.5).astype(int)
        df['low_volatility'] = (df['volatility_ratio'] <= 0.8).astype(int)
        
        # ATR normalized
        df['atr_normalized'] = df['atr_14'] / df['Close']
        
        # ===== PRICE ACTION =====
        df['body'] = df['Close'] - df['Open']
        df['body_size'] = abs(df['body']) / (df['High'] - df['Low'] + 1e-8)
        df['is_bullish'] = (df['Close'] > df['Open']).astype(int)
        df['is_strong_bullish'] = ((df['Close'] > df['Open']) & (df['body_size'] > 0.6)).astype(int)
        df['is_strong_bearish'] = ((df['Close'] < df['Open']) & (df['body_size'] > 0.6)).astype(int)
        
        # Consecutive candles
        df['consec_bull'] = df['is_bullish'].rolling(3).sum()
        df['consec_bear'] = 3 - df['consec_bull']
        
        # Support/Resistance
        df['recent_high'] = df['High'].rolling(50).max()
        df['recent_low'] = df['Low'].rolling(50).min()
        df['range'] = df['recent_high'] - df['recent_low']
        df['position_in_range'] = (df['Close'] - df['recent_low']) / (df['range'] + 1e-8)
        
        # ===== TIME FEATURES =====
        if 'Date' in df.columns:
            try:
                df['datetime'] = pd.to_datetime(df['Date'])
                df['hour'] = df['datetime'].dt.hour
                df['day_of_week'] = df['datetime'].dt.dayofweek
                
                # Best hours for gold (London & NY sessions)
                df['is_london'] = ((df['hour'] >= 7) & (df['hour'] < 15)).astype(int)
                df['is_ny'] = ((df['hour'] >= 12) & (df['hour'] < 20)).astype(int)
                df['is_overlap'] = ((df['hour'] >= 12) & (df['hour'] < 15)).astype(int)
                
                # Prime trading hours only
                df['is_prime_london'] = ((df['hour'] >= 8) & (df['hour'] < 11)).astype(int)
                df['is_prime_ny'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)
                df['is_prime_time'] = ((df['is_prime_london'] == 1) | (df['is_prime_ny'] == 1)).astype(int)
                
                # Avoid bad times
                df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
                df['is_dead_hour'] = ((df['hour'] >= 21) | (df['hour'] < 3)).astype(int)
                df['tradeable_session'] = ((df['is_prime_time'] == 1) & (df['is_dead_hour'] == 0) & (df['is_weekend'] == 0)).astype(int)
                
            except:
                df['hour'] = 12
                df['day_of_week'] = 2
                df['is_prime_time'] = 1
                df['is_dead_hour'] = 0
                df['tradeable_session'] = 1
        
        # ===== CONFLUENCE SCORE =====
        # Buy setup score
        df['buy_confluence'] = (
            df['strong_bull_trend'].astype(int) +
            df['macd_bullish'].astype(int) +
            df['price_above_ema_20'].astype(int) +
            df['is_prime_time'].astype(int) +
            df['normal_volatility'].astype(int) +
            (df['rsi_14'] < 60).astype(int)
        )
        
        # Sell setup score
        df['sell_confluence'] = (
            df['strong_bear_trend'].astype(int) +
            df['macd_bearish'].astype(int) +
            (1 - df['price_above_ema_20']).astype(int) +
            df['is_prime_time'].astype(int) +
            df['normal_volatility'].astype(int) +
            (df['rsi_14'] > 40).astype(int)
        )
        
        # Feature columns
        self.feature_columns = [
            # Trend
            'bull_trend_score', 'bear_trend_score', 
            'strong_bull_trend', 'strong_bear_trend', 'has_trend',
            'price_vs_ema_20', 'price_vs_ema_50', 'price_vs_ema_100',
            'ema_20_slope', 'ema_50_slope',
            # Momentum
            'rsi_7', 'rsi_14', 'rsi_21',
            'rsi_oversold', 'rsi_overbought', 'rsi_neutral',
            'macd_hist', 'macd_bullish', 'macd_bearish',
            'stoch_k', 'stoch_d', 'stoch_oversold', 'stoch_overbought',
            # Volatility
            'atr_normalized', 'volatility_ratio',
            'normal_volatility', 'high_volatility', 'low_volatility',
            # Price action
            'body_size', 'is_bullish', 'is_strong_bullish', 'is_strong_bearish',
            'consec_bull', 'consec_bear', 'position_in_range',
            # Time
            'hour', 'day_of_week', 'is_prime_time', 'is_dead_hour', 'tradeable_session',
            # Confluence
            'buy_confluence', 'sell_confluence',
        ]
        
        return df
    
    def create_high_probability_target(
        self, 
        df: pd.DataFrame, 
        lookahead: int = 8,
        min_move_pips: float = 5.0,
    ) -> pd.DataFrame:
        """
        Create target focused on high-probability direction.
        
        Only label as BUY/SELL if:
        1. Clear directional move happens
        2. Move is significant (> min_move_pips)
        3. Move happens relatively quickly
        """
        df = df.copy()
        
        pip_value = 0.1  # XAUUSD
        threshold = min_move_pips * pip_value
        
        entry = df['Close'].values
        target = np.zeros(len(df))
        
        for i in range(len(df) - lookahead):
            future_closes = df['Close'].iloc[i+1:i+1+lookahead].values
            max_up = (future_closes - entry[i]).max()
            max_down = (entry[i] - future_closes).max()
            
            # Only strong directional signals
            if max_up >= threshold and max_up > max_down * 1.5:
                # Clear upward move, up > 1.5x down
                target[i] = 1  # BUY
            elif max_down >= threshold and max_down > max_up * 1.5:
                # Clear downward move
                target[i] = 2  # SELL
            else:
                target[i] = 0  # HOLD (unclear)
        
        df['target'] = target.astype(int)
        return df


def train_high_winrate_model(
    data_path: str,
    timeframe: str = "M5",
    lookahead: int = 8,
    min_move_pips: float = 5.0,
    test_size: float = 0.2,
    max_rows: int = None,
):
    """Train model optimized for high win-rate."""
    
    print("=" * 70)
    print(f"🎯 HIGH WIN-RATE XAUUSD Scalping Model ({timeframe})")
    print("=" * 70)
    print(f"   Settings: Lookahead={lookahead}, Min Move={min_move_pips} pips")
    
    # Load data
    print(f"\n📊 Loading data from {data_path}...")
    df = pd.read_csv(data_path, sep=';', nrows=max_rows)
    print(f"   Loaded {len(df):,} rows")
    
    # Use recent data
    if len(df) > 400000:
        print(f"📅 Using last 400,000 rows...")
        df = df.tail(400000).reset_index(drop=True)
    
    # Feature engineering
    print("\n🔧 Creating features...")
    fe = HighWinRateFeatures()
    df = fe.create_features(df)
    df = fe.create_high_probability_target(df, lookahead=lookahead, min_move_pips=min_move_pips)
    
    # Drop NaN
    df = df.dropna()
    print(f"   Dataset: {len(df):,} rows")
    
    # Prepare features
    feature_cols = [c for c in fe.feature_columns if c in df.columns]
    print(f"   Using {len(feature_cols)} features")
    
    X = df[feature_cols].values
    y = df['target'].values
    
    # Class distribution
    unique, counts = np.unique(y, return_counts=True)
    print(f"\n📊 Target distribution:")
    for u, c in zip(unique, counts):
        label = ['HOLD', 'BUY', 'SELL'][u]
        print(f"   {label}: {c:,} ({c/len(y)*100:.1f}%)")
    
    # Split
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # Additional filter: Only train on prime time data
    # This helps the model learn high-quality patterns
    if 'tradeable_session' in df.columns:
        train_mask = df['tradeable_session'].iloc[:split_idx].values == 1
        X_train_filtered = X_train[train_mask]
        y_train_filtered = y_train[train_mask]
        print(f"\n📈 Training on prime-time data only: {len(X_train_filtered):,} samples")
    else:
        X_train_filtered = X_train
        y_train_filtered = y_train
    
    print(f"   Test set: {len(X_test):,} samples")
    
    # Scale
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train_filtered)
    X_test_scaled = scaler.transform(X_test)
    
    X_train_scaled = np.nan_to_num(X_train_scaled, nan=0, posinf=1, neginf=-1)
    X_test_scaled = np.nan_to_num(X_test_scaled, nan=0, posinf=1, neginf=-1)
    
    # ===== TRAIN WITH CALIBRATION =====
    print("\n🎯 Training LightGBM with probability calibration...")
    
    base_lgb = lgb.LGBMClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.02,
        num_leaves=32,
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_samples=100,
        reg_alpha=0.5,
        reg_lambda=1.0,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    
    # Fit and calibrate
    base_lgb.fit(X_train_scaled, y_train_filtered)
    
    # Calibrated classifier for better probability estimates
    calibrated_lgb = CalibratedClassifierCV(base_lgb, method='isotonic', cv='prefit')
    calibrated_lgb.fit(X_train_scaled, y_train_filtered)
    
    print("🎯 Training XGBoost...")
    
    base_xgb = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.02,
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_weight=10,
        gamma=0.5,
        reg_alpha=0.5,
        reg_lambda=2.0,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    
    base_xgb.fit(X_train_scaled, y_train_filtered)
    
    # ===== EVALUATION =====
    print("\n📊 EVALUATION:")
    
    # Predictions
    lgb_proba = calibrated_lgb.predict_proba(X_test_scaled)
    xgb_proba = base_xgb.predict_proba(X_test_scaled)
    
    # Ensemble
    ensemble_proba = (lgb_proba + xgb_proba) / 2
    ensemble_pred = np.argmax(ensemble_proba, axis=1)
    
    ensemble_acc = accuracy_score(y_test, ensemble_pred)
    print(f"\n   Overall Ensemble Accuracy: {ensemble_acc:.4f}")
    
    print(f"\n   Full Classification Report:")
    print(classification_report(y_test, ensemble_pred, target_names=['HOLD', 'BUY', 'SELL']))
    
    # ===== WIN RATE AT DIFFERENT CONFIDENCE LEVELS =====
    print("\n💰 WIN RATE BY CONFIDENCE THRESHOLD:")
    print("-" * 60)
    
    max_proba = ensemble_proba.max(axis=1)
    
    best_threshold = 0.50
    best_winrate = 0
    best_trades = 0
    
    for threshold in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        # Only trade (not HOLD) with high confidence
        trade_mask = (ensemble_pred != 0) & (max_proba >= threshold)
        
        if trade_mask.sum() < 10:
            continue
        
        filtered_pred = ensemble_pred[trade_mask]
        filtered_actual = y_test[trade_mask]
        
        # Win = our direction prediction matches actual
        wins = (filtered_pred == filtered_actual).sum()
        total = len(filtered_pred)
        win_rate = wins / total * 100
        
        # Track best
        if win_rate > best_winrate and total >= 50:
            best_winrate = win_rate
            best_threshold = threshold
            best_trades = total
        
        marker = " ⭐" if win_rate > 50 else ""
        print(f"   Confidence >= {threshold:.0%}: Trades={total:5,}  Win Rate={win_rate:5.1f}%{marker}")
    
    print("-" * 60)
    
    # ===== BEST THRESHOLD ANALYSIS =====
    print(f"\n🏆 BEST SETTING FOR >50% WIN RATE:")
    print(f"   Confidence Threshold: {best_threshold:.0%}")
    print(f"   Expected Trades: {best_trades:,}")
    print(f"   Win Rate: {best_winrate:.1f}%")
    
    # Detailed breakdown at best threshold
    trade_mask = (ensemble_pred != 0) & (max_proba >= best_threshold)
    if trade_mask.sum() > 0:
        filtered_pred = ensemble_pred[trade_mask]
        filtered_actual = y_test[trade_mask]
        
        buy_signals = (filtered_pred == 1).sum()
        sell_signals = (filtered_pred == 2).sum()
        buy_correct = ((filtered_pred == 1) & (filtered_actual == 1)).sum()
        sell_correct = ((filtered_pred == 2) & (filtered_actual == 2)).sum()
        
        buy_wr = buy_correct / buy_signals * 100 if buy_signals > 0 else 0
        sell_wr = sell_correct / sell_signals * 100 if sell_signals > 0 else 0
        
        print(f"\n   BUY signals:  {buy_signals:,} (Win Rate: {buy_wr:.1f}%)")
        print(f"   SELL signals: {sell_signals:,} (Win Rate: {sell_wr:.1f}%)")
    
    # ===== FEATURE IMPORTANCE =====
    print("\n🔍 Top 10 Feature Importances:")
    importance = base_lgb.feature_importances_
    indices = np.argsort(importance)[-10:][::-1]
    for i in indices:
        print(f"   {feature_cols[i]}: {importance[i]:.0f}")
    
    # ===== SAVE MODEL =====
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = backend_dir / "models"
    model_dir.mkdir(exist_ok=True)
    
    model_filename = f"model_highwinrate_xauusd_{timeframe}_{timestamp}.pkl"
    model_path = model_dir / model_filename
    
    model_data = {
        'lgb_model': base_lgb,
        'calibrated_lgb': calibrated_lgb,
        'xgb_model': base_xgb,
        'scaler': scaler,
        'feature_columns': feature_cols,
        'timeframe': timeframe,
        'lookahead': lookahead,
        'min_move_pips': min_move_pips,
        'ensemble_accuracy': ensemble_acc,
        'best_threshold': best_threshold,
        'best_winrate': best_winrate,
        'trained_at': datetime.now().isoformat(),
        'model_type': 'high_winrate_scalping',
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved to: {model_path}")
    
    return str(model_path), model_data


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Train High Win-Rate XAUUSD Model')
    parser.add_argument('--timeframe', type=str, default='M5', choices=['M5', 'M15'])
    parser.add_argument('--lookahead', type=int, default=8)
    parser.add_argument('--min-move', type=float, default=5.0)
    parser.add_argument('--max-rows', type=int, default=None)
    
    args = parser.parse_args()
    
    base_path = Path(__file__).parent.parent.parent
    if args.timeframe == 'M5':
        data_path = base_path / 'ohlcv' / 'xauusd' / 'XAU_5m_data.csv'
    else:
        data_path = base_path / 'ohlcv' / 'xauusd' / 'XAU_15m_data.csv'
    
    if not data_path.exists():
        print(f"❌ Data not found: {data_path}")
        return 1
    
    try:
        model_path, model_data = train_high_winrate_model(
            data_path=str(data_path),
            timeframe=args.timeframe,
            lookahead=args.lookahead,
            min_move_pips=args.min_move,
            max_rows=args.max_rows,
        )
        
        print("\n" + "=" * 70)
        print("🎉 TRAINING COMPLETE!")
        print("=" * 70)
        print(f"Model: {model_path}")
        print(f"Best Confidence Threshold: {model_data['best_threshold']:.0%}")
        print(f"Win Rate at Best Threshold: {model_data['best_winrate']:.1f}%")
        
        if model_data['best_winrate'] > 50:
            print("\n✅ SUCCESS: Win rate > 50% achieved!")
        else:
            print("\n⚠️  Win rate < 50%. Consider:")
            print("   - Higher confidence threshold")
            print("   - Longer timeframe (M15/H1)")
            print("   - Additional filters")
        
        return 0
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
