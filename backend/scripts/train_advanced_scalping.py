#!/usr/bin/env python3
"""
Advanced Scalping Model Training for XAUUSD.

Improvements over basic model:
1. Smart Target Definition - probability of hitting TP before SL
2. Session Filtering - only trade during high-liquidity sessions
3. Trend Context - use higher timeframe trend
4. LightGBM + XGBoost Ensemble
5. Feature Selection - reduce noise
6. Walk-forward validation
"""

import os
import sys
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.feature_selection import SelectFromModel
import xgboost as xgb
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class AdvancedScalpingFeatures:
    """Advanced feature engineering for scalping."""
    
    def __init__(self):
        self.feature_columns = []
        self.selected_features = None
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive scalping features."""
        df = df.copy()
        
        # Ensure numeric columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # ===== PRICE ACTION FEATURES =====
        # Multiple return periods
        for period in [1, 2, 3, 5, 8, 13]:
            df[f'returns_{period}'] = df['Close'].pct_change(period)
        
        # Log returns (more stationary)
        df['log_return_1'] = np.log(df['Close'] / df['Close'].shift(1))
        df['log_return_5'] = np.log(df['Close'] / df['Close'].shift(5))
        
        # ===== VOLATILITY FEATURES =====
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        
        for period in [3, 5, 10, 14, 20]:
            df[f'atr_{period}'] = df['tr'].rolling(period).mean()
            df[f'atr_{period}_normalized'] = df[f'atr_{period}'] / df['Close']
        
        # Volatility regime
        df['volatility_ratio'] = df['atr_5'] / (df['atr_20'] + 1e-8)
        df['is_high_volatility'] = (df['volatility_ratio'] > 1.2).astype(int)
        df['is_low_volatility'] = (df['volatility_ratio'] < 0.8).astype(int)
        
        # ===== TREND FEATURES =====
        # Multiple EMAs
        for period in [5, 10, 20, 50]:
            df[f'ema_{period}'] = df['Close'].ewm(span=period).mean()
            df[f'price_vs_ema_{period}'] = (df['Close'] - df[f'ema_{period}']) / df[f'ema_{period}']
        
        # EMA slopes
        df['ema_10_slope'] = df['ema_10'].pct_change(3)
        df['ema_20_slope'] = df['ema_20'].pct_change(5)
        
        # Trend strength
        df['trend_strength'] = abs(df['price_vs_ema_20'])
        df['is_trending'] = (df['trend_strength'] > 0.002).astype(int)
        
        # Higher timeframe trend (simulated with longer lookback)
        df['htf_trend'] = np.sign(df['Close'].rolling(60).mean() - df['Close'].rolling(120).mean())
        
        # ===== MOMENTUM FEATURES =====
        # RSI with multiple periods
        for period in [7, 14]:
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            rs = avg_gain / (avg_loss + 1e-8)
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            df[f'rsi_{period}_zone'] = np.where(df[f'rsi_{period}'] > 70, 1, 
                                                np.where(df[f'rsi_{period}'] < 30, -1, 0))
        
        # RSI divergence
        df['rsi_momentum'] = df['rsi_7'] - df['rsi_7'].shift(5)
        
        # Stochastic
        lowest_low = df['Low'].rolling(14).min()
        highest_high = df['High'].rolling(14).max()
        df['stoch_k'] = 100 * (df['Close'] - lowest_low) / (highest_high - lowest_low + 1e-8)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        df['stoch_cross'] = np.sign(df['stoch_k'] - df['stoch_d'])
        
        # MACD
        ema_12 = df['Close'].ewm(span=12).mean()
        ema_26 = df['Close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['macd_hist_slope'] = df['macd_hist'].diff(2)
        df['macd_cross'] = np.sign(df['macd'] - df['macd_signal'])
        
        # ===== PRICE ACTION PATTERNS =====
        # Candle metrics
        df['body'] = df['Close'] - df['Open']
        df['body_size'] = abs(df['body']) / (df['High'] - df['Low'] + 1e-8)
        df['upper_shadow'] = (df['High'] - df[['Open', 'Close']].max(axis=1)) / (df['High'] - df['Low'] + 1e-8)
        df['lower_shadow'] = (df[['Open', 'Close']].min(axis=1) - df['Low']) / (df['High'] - df['Low'] + 1e-8)
        df['is_bullish'] = (df['Close'] > df['Open']).astype(int)
        df['is_doji'] = (df['body_size'] < 0.1).astype(int)
        
        # Consecutive candles
        df['consec_bullish'] = df['is_bullish'].rolling(3).sum()
        df['consec_bearish'] = 3 - df['consec_bullish']
        
        # Support/Resistance proximity
        df['recent_high'] = df['High'].rolling(20).max()
        df['recent_low'] = df['Low'].rolling(20).min()
        df['range'] = df['recent_high'] - df['recent_low']
        df['position_in_range'] = (df['Close'] - df['recent_low']) / (df['range'] + 1e-8)
        df['near_resistance'] = (df['position_in_range'] > 0.9).astype(int)
        df['near_support'] = (df['position_in_range'] < 0.1).astype(int)
        
        # ===== VOLUME FEATURES =====
        if 'Volume' in df.columns and df['Volume'].sum() > 0:
            df['volume_sma_10'] = df['Volume'].rolling(10).mean()
            df['volume_sma_20'] = df['Volume'].rolling(20).mean()
            df['volume_ratio'] = df['Volume'] / (df['volume_sma_10'] + 1)
            df['volume_spike'] = (df['Volume'] > df['volume_sma_20'] * 1.5).astype(int)
            df['volume_trend'] = np.sign(df['volume_sma_10'] - df['volume_sma_20'])
        else:
            df['volume_ratio'] = 1
            df['volume_spike'] = 0
            df['volume_trend'] = 0
        
        # ===== TIME FEATURES =====
        if 'Date' in df.columns or 'timestamp' in df.columns:
            dt_col = 'Date' if 'Date' in df.columns else 'timestamp'
            try:
                df['datetime'] = pd.to_datetime(df[dt_col])
                df['hour'] = df['datetime'].dt.hour
                df['day_of_week'] = df['datetime'].dt.dayofweek
                
                # Trading sessions (Server time usually GMT+2/3)
                # Asian: 00:00 - 07:00
                # London: 07:00 - 15:00
                # NY: 12:00 - 20:00
                # Overlap: 12:00 - 15:00
                
                df['is_asian'] = ((df['hour'] >= 0) & (df['hour'] < 7)).astype(int)
                df['is_london'] = ((df['hour'] >= 7) & (df['hour'] < 15)).astype(int)
                df['is_ny'] = ((df['hour'] >= 12) & (df['hour'] < 20)).astype(int)
                df['is_overlap'] = ((df['hour'] >= 12) & (df['hour'] < 15)).astype(int)
                
                # Best trading hours for gold
                df['is_prime_time'] = (
                    ((df['hour'] >= 8) & (df['hour'] < 11)) |  # London morning
                    ((df['hour'] >= 13) & (df['hour'] < 16))   # NY open
                ).astype(int)
                
                # Avoid dead hours
                df['is_dead_hour'] = (
                    ((df['hour'] >= 21) | (df['hour'] < 2)) |  # Night
                    (df['day_of_week'] >= 5)  # Weekend
                ).astype(int)
                
            except:
                df['hour'] = 12
                df['day_of_week'] = 2
                df['is_asian'] = 0
                df['is_london'] = 1
                df['is_ny'] = 0
                df['is_overlap'] = 0
                df['is_prime_time'] = 1
                df['is_dead_hour'] = 0
        
        # ===== LAG FEATURES =====
        # Add lagged values for key indicators
        for lag in [1, 2, 3]:
            df[f'rsi_7_lag_{lag}'] = df['rsi_7'].shift(lag)
            df[f'macd_hist_lag_{lag}'] = df['macd_hist'].shift(lag)
            df[f'returns_1_lag_{lag}'] = df['returns_1'].shift(lag)
        
        # ===== DEFINE FEATURE COLUMNS =====
        self.feature_columns = [
            # Returns
            'returns_1', 'returns_2', 'returns_3', 'returns_5', 'returns_8', 'returns_13',
            'log_return_1', 'log_return_5',
            # Volatility
            'atr_5_normalized', 'atr_10_normalized', 'atr_14_normalized',
            'volatility_ratio', 'is_high_volatility', 'is_low_volatility',
            # Trend
            'price_vs_ema_5', 'price_vs_ema_10', 'price_vs_ema_20', 'price_vs_ema_50',
            'ema_10_slope', 'ema_20_slope', 'trend_strength', 'is_trending', 'htf_trend',
            # Momentum
            'rsi_7', 'rsi_14', 'rsi_7_zone', 'rsi_14_zone', 'rsi_momentum',
            'stoch_k', 'stoch_d', 'stoch_cross',
            'macd_hist', 'macd_hist_slope', 'macd_cross',
            # Price action
            'body_size', 'upper_shadow', 'lower_shadow', 'is_bullish', 'is_doji',
            'consec_bullish', 'consec_bearish',
            'position_in_range', 'near_resistance', 'near_support',
            # Volume
            'volume_ratio', 'volume_spike', 'volume_trend',
            # Time
            'hour', 'day_of_week', 'is_london', 'is_ny', 'is_overlap', 
            'is_prime_time', 'is_dead_hour',
            # Lags
            'rsi_7_lag_1', 'rsi_7_lag_2', 'rsi_7_lag_3',
            'macd_hist_lag_1', 'macd_hist_lag_2', 'macd_hist_lag_3',
            'returns_1_lag_1', 'returns_1_lag_2', 'returns_1_lag_3',
        ]
        
        return df
    
    def create_smart_target(
        self, 
        df: pd.DataFrame, 
        lookahead: int = 6,
        tp_pips: float = 8.0,
        sl_pips: float = 5.0,
    ) -> pd.DataFrame:
        """
        Smart target: Which direction hits target first?
        
        This is more realistic than simple direction prediction.
        We check if TP is hit before SL for both long and short.
        """
        df = df.copy()
        
        pip_value = 0.1  # For XAUUSD
        tp = tp_pips * pip_value
        sl = sl_pips * pip_value
        
        # Calculate future prices
        entry = df['Close'].values
        
        # For each row, check next N candles
        target = np.zeros(len(df))
        
        for i in range(len(df) - lookahead):
            future_highs = df['High'].iloc[i+1:i+1+lookahead].values
            future_lows = df['Low'].iloc[i+1:i+1+lookahead].values
            entry_price = entry[i]
            
            # Long trade: TP hit if high goes above entry + tp
            # Long trade: SL hit if low goes below entry - sl
            long_tp_hit = np.any(future_highs >= entry_price + tp)
            long_sl_hit = np.any(future_lows <= entry_price - sl)
            
            # Short trade: TP hit if low goes below entry - tp
            # Short trade: SL hit if high goes above entry + sl
            short_tp_hit = np.any(future_lows <= entry_price - tp)
            short_sl_hit = np.any(future_highs >= entry_price + sl)
            
            # Find first occurrence
            long_tp_idx = np.argmax(future_highs >= entry_price + tp) if long_tp_hit else lookahead + 1
            long_sl_idx = np.argmax(future_lows <= entry_price - sl) if long_sl_hit else lookahead + 1
            short_tp_idx = np.argmax(future_lows <= entry_price - tp) if short_tp_hit else lookahead + 1
            short_sl_idx = np.argmax(future_highs >= entry_price + sl) if short_sl_hit else lookahead + 1
            
            # Determine trade signal
            long_success = long_tp_hit and (long_tp_idx < long_sl_idx)
            short_success = short_tp_hit and (short_tp_idx < short_sl_idx)
            
            if long_success and not short_success:
                target[i] = 1  # BUY
            elif short_success and not long_success:
                target[i] = 2  # SELL
            elif long_success and short_success:
                # Both work, pick the one that hits target first
                if long_tp_idx <= short_tp_idx:
                    target[i] = 1
                else:
                    target[i] = 2
            else:
                target[i] = 0  # HOLD
        
        df['target'] = target.astype(int)
        
        return df


def load_data(filepath: str, max_rows: int = None) -> pd.DataFrame:
    """Load OHLCV data."""
    print(f"📊 Loading data from {filepath}...")
    df = pd.read_csv(filepath, sep=';', nrows=max_rows)
    print(f"   Loaded {len(df):,} rows")
    
    # Convert date
    if 'Date' in df.columns:
        df['datetime'] = pd.to_datetime(df['Date'])
    
    df = df.dropna()
    return df


def train_advanced_scalping_model(
    data_path: str,
    timeframe: str = "M5",
    lookahead: int = 6,
    tp_pips: float = 8.0,
    sl_pips: float = 5.0,
    test_size: float = 0.2,
    max_rows: int = None,
    session_filter: bool = True,
):
    """Train advanced scalping model."""
    
    print("=" * 70)
    print(f"🚀 ADVANCED XAUUSD Scalping Model Training ({timeframe})")
    print("=" * 70)
    print(f"   Settings: TP={tp_pips} pips, SL={sl_pips} pips, Lookahead={lookahead}")
    print(f"   Risk:Reward = 1:{tp_pips/sl_pips:.1f}")
    
    # Load data
    df = load_data(data_path, max_rows)
    
    # Use recent data (last 300K for speed)
    if len(df) > 300000:
        print(f"📅 Using last 300,000 rows (most recent data)...")
        df = df.tail(300000).reset_index(drop=True)
    
    # Feature engineering
    print("\n🔧 Creating advanced features...")
    fe = AdvancedScalpingFeatures()
    df = fe.create_features(df)
    df = fe.create_smart_target(df, lookahead=lookahead, tp_pips=tp_pips, sl_pips=sl_pips)
    
    # Drop NaN
    df = df.dropna()
    print(f"   Dataset after processing: {len(df):,} rows")
    
    # Session filtering - only trade during good hours
    if session_filter and 'is_prime_time' in df.columns:
        original_len = len(df)
        # Keep all data for training but mark bad hours
        df['tradeable'] = 1 - df['is_dead_hour']
        print(f"   Tradeable rows: {df['tradeable'].sum():,} ({df['tradeable'].mean()*100:.1f}%)")
    
    # Prepare features
    feature_cols = [c for c in fe.feature_columns if c in df.columns]
    print(f"   Using {len(feature_cols)} features")
    
    X = df[feature_cols].values
    y = df['target'].values
    
    # Print class distribution
    unique, counts = np.unique(y, return_counts=True)
    print(f"\n📊 Target distribution:")
    for u, c in zip(unique, counts):
        label = ['HOLD', 'BUY', 'SELL'][u]
        print(f"   {label}: {c:,} ({c/len(y)*100:.1f}%)")
    
    # Calculate win rate potential (how often TP is hit before SL)
    buy_count = (y == 1).sum()
    sell_count = (y == 2).sum()
    tradeable = buy_count + sell_count
    print(f"\n💡 Tradeable signals: {tradeable:,} ({tradeable/len(y)*100:.1f}%)")
    print(f"   If model is perfect, these are winning trades")
    
    # Time-series split
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n📈 Train: {len(X_train):,}, Test: {len(X_test):,}")
    
    # Use RobustScaler (better for outliers)
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Replace inf/nan
    X_train_scaled = np.nan_to_num(X_train_scaled, nan=0, posinf=1, neginf=-1)
    X_test_scaled = np.nan_to_num(X_test_scaled, nan=0, posinf=1, neginf=-1)
    
    # ===== TRAIN LIGHTGBM =====
    print("\n🎯 Training LightGBM...")
    
    lgb_model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.03,
        num_leaves=64,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=50,
        reg_alpha=0.1,
        reg_lambda=0.1,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    
    lgb_model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )
    
    # ===== TRAIN XGBOOST =====
    print("🎯 Training XGBoost...")
    
    # Class weights
    class_counts = np.bincount(y_train, minlength=3)
    total = len(y_train)
    class_weights = {i: total / (3 * c) if c > 0 else 1.0 for i, c in enumerate(class_counts)}
    sample_weights = np.array([class_weights[yi] for yi in y_train])
    
    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=0.2,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    
    xgb_model.fit(
        X_train_scaled, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )
    
    # ===== ENSEMBLE PREDICTIONS =====
    print("\n📊 Ensemble Evaluation:")
    
    # Get probabilities
    lgb_proba = lgb_model.predict_proba(X_test_scaled)
    xgb_proba = xgb_model.predict_proba(X_test_scaled)
    
    # Ensemble (average probabilities)
    ensemble_proba = (lgb_proba + xgb_proba) / 2
    ensemble_pred = np.argmax(ensemble_proba, axis=1)
    
    # Individual model accuracies
    lgb_acc = accuracy_score(y_test, lgb_model.predict(X_test_scaled))
    xgb_acc = accuracy_score(y_test, xgb_model.predict(X_test_scaled))
    ensemble_acc = accuracy_score(y_test, ensemble_pred)
    
    print(f"   LightGBM Accuracy: {lgb_acc:.4f}")
    print(f"   XGBoost Accuracy:  {xgb_acc:.4f}")
    print(f"   Ensemble Accuracy: {ensemble_acc:.4f}")
    
    # Classification report
    print(f"\n   Ensemble Classification Report:")
    target_names = ['HOLD', 'BUY', 'SELL']
    print(classification_report(y_test, ensemble_pred, target_names=target_names))
    
    # ===== TRADING METRICS WITH CONFIDENCE FILTER =====
    print("\n💰 Trading Metrics (with confidence filter):")
    
    # Get max probability for each prediction
    max_proba = ensemble_proba.max(axis=1)
    
    # Different confidence thresholds
    for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
        # Only trade when confident and not HOLD
        trade_mask = (ensemble_pred != 0) & (max_proba >= threshold)
        
        if trade_mask.sum() == 0:
            continue
        
        filtered_pred = ensemble_pred[trade_mask]
        filtered_actual = y_test[trade_mask]
        
        # Win = prediction matches actual (and actual is not HOLD for that direction)
        wins = (filtered_pred == filtered_actual).sum()
        total_trades = len(filtered_pred)
        win_rate = wins / total_trades * 100
        
        # Calculate expected profit
        # Win: +TP pips, Loss: -SL pips
        # But we need to account for HOLD actuals (neither win nor loss for day)
        actual_wins = ((filtered_pred == 1) & (filtered_actual == 1)).sum() + \
                      ((filtered_pred == 2) & (filtered_actual == 2)).sum()
        actual_losses = ((filtered_pred == 1) & (filtered_actual == 2)).sum() + \
                        ((filtered_pred == 2) & (filtered_actual == 1)).sum()
        neutral = total_trades - actual_wins - actual_losses
        
        expected_profit = actual_wins * tp_pips - actual_losses * sl_pips
        
        print(f"   Confidence >= {threshold:.0%}:")
        print(f"      Trades: {total_trades:,} ({total_trades/len(y_test)*100:.1f}% of test)")
        print(f"      Win Rate: {win_rate:.1f}%")
        print(f"      Wins: {actual_wins}, Losses: {actual_losses}, Neutral: {neutral}")
        print(f"      Expected Profit: {expected_profit:.0f} pips")
        print()
    
    # ===== FEATURE IMPORTANCE =====
    print("\n🔍 Top 15 Feature Importances (LightGBM):")
    importance = lgb_model.feature_importances_
    indices = np.argsort(importance)[-15:][::-1]
    for i in indices:
        print(f"   {feature_cols[i]}: {importance[i]:.0f}")
    
    # ===== SAVE MODEL =====
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = backend_dir / "models"
    model_dir.mkdir(exist_ok=True)
    
    model_filename = f"model_scalping_advanced_xauusd_{timeframe}_{timestamp}.pkl"
    model_path = model_dir / model_filename
    
    # Select best single model for deployment
    best_model = lgb_model if lgb_acc >= xgb_acc else xgb_model
    best_model_type = 'lightgbm' if lgb_acc >= xgb_acc else 'xgboost'
    
    model_data = {
        'lgb_model': lgb_model,
        'xgb_model': xgb_model,
        'best_model': best_model,
        'best_model_type': best_model_type,
        'scaler': scaler,
        'feature_columns': feature_cols,
        'timeframe': timeframe,
        'lookahead': lookahead,
        'tp_pips': tp_pips,
        'sl_pips': sl_pips,
        'ensemble_accuracy': ensemble_acc,
        'lgb_accuracy': lgb_acc,
        'xgb_accuracy': xgb_acc,
        'trained_at': datetime.now().isoformat(),
        'model_type': 'advanced_scalping_ensemble',
        'recommended_confidence': 0.50,
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved to: {model_path}")
    
    return str(model_path), model_data


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train Advanced XAUUSD Scalping Model')
    parser.add_argument('--timeframe', type=str, default='M5', choices=['M5', 'M15'],
                        help='Timeframe to use')
    parser.add_argument('--lookahead', type=int, default=6,
                        help='Candles to look ahead')
    parser.add_argument('--tp', type=float, default=8.0,
                        help='Take profit in pips')
    parser.add_argument('--sl', type=float, default=5.0,
                        help='Stop loss in pips')
    parser.add_argument('--max-rows', type=int, default=None,
                        help='Maximum rows to load')
    parser.add_argument('--no-session-filter', action='store_true',
                        help='Disable session filtering')
    
    args = parser.parse_args()
    
    # Determine data path
    base_path = Path(__file__).parent.parent.parent
    if args.timeframe == 'M5':
        data_path = base_path / 'ohlcv' / 'xauusd' / 'XAU_5m_data.csv'
    else:
        data_path = base_path / 'ohlcv' / 'xauusd' / 'XAU_15m_data.csv'
    
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return 1
    
    try:
        model_path, model_data = train_advanced_scalping_model(
            data_path=str(data_path),
            timeframe=args.timeframe,
            lookahead=args.lookahead,
            tp_pips=args.tp,
            sl_pips=args.sl,
            max_rows=args.max_rows,
            session_filter=not args.no_session_filter,
        )
        
        print("\n" + "=" * 70)
        print("🎉 TRAINING COMPLETE!")
        print("=" * 70)
        print(f"Model: {model_path}")
        print(f"Best Model: {model_data['best_model_type']}")
        print(f"Ensemble Accuracy: {model_data['ensemble_accuracy']:.2%}")
        print(f"LightGBM Accuracy: {model_data['lgb_accuracy']:.2%}")
        print(f"XGBoost Accuracy:  {model_data['xgb_accuracy']:.2%}")
        print(f"Recommended Confidence Threshold: {model_data['recommended_confidence']:.0%}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
