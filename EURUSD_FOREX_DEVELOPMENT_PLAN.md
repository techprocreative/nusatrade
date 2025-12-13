# EURUSD Forex-Specific Development Plan

**Date:** 2025-12-13
**Goal:** Build profitable EURUSD model with forex-specific features
**Timeline:** 2-3 weeks
**Success Target:** PF > 1.5, WR > 60%

---

## Phase 1: Data Acquisition (Day 1)

### 1.1 Download Recent EURUSD Data
- **Source:** MetaTrader 5 or yfinance
- **Period:** 2020-2025 (5 years recent data)
- **Timeframe:** 1-hour candles
- **Format:** timestamp, open, high, low, close, volume

**Why Recent Data:**
- Market regime has changed (COVID, ECB policy, rate hikes)
- 2005-2020 data includes financial crisis (different dynamics)
- Recent patterns more relevant for live trading

### 1.2 Data Quality Checks
- Remove gaps and weekends
- Validate OHLC relationships
- Check for anomalies
- Ensure sufficient samples (>50,000 candles)

---

## Phase 2: Forex-Specific Feature Engineering (Day 2-5)

### 2.1 Core Forex Features

**A. Interest Rate Differential Proxy**
Since we don't have real-time interest rate data, we'll use proxies:
- Price momentum as rate expectation proxy
- Trend strength (ADX) as policy divergence signal
- Multi-timeframe momentum alignment

**B. Dollar Strength Index**
- Calculate USD strength from EURUSD movements
- Rolling correlation with price
- Divergence detection

**C. Cross-Pair Correlations**
Even without other pairs, we can infer:
- EUR strength from EURUSD momentum
- USD weakness from declining EURUSD resistance
- Pattern correlation (similar to currency index)

### 2.2 Forex-Specific Indicators

**A. Mean Reversion Features**
EURUSD tends to mean-revert more than Gold:
- Z-score from moving average
- Bollinger Band position
- Standard deviation from trend
- Oscillator extremes (RSI, Stochastic)

**B. Range vs Trend Detection**
Critical for forex pairs:
- ADX (trend strength)
- ATR expansion/contraction
- Donchian channel width
- Pivot point clustering

**C. Session Analysis**
Forex has distinct trading sessions:
- Hour of day (0-23)
- Day of week (1-5)
- Session volatility (Asian/London/NY)
- Session-specific momentum

**D. Support/Resistance Levels**
Forex respects S/R more than crypto:
- Round number proximity (1.0000, 1.0500, etc.)
- Recent swing highs/lows
- Pivot points (traditional + Fibonacci)
- Distance from psychological levels

### 2.3 Advanced Features

**A. Volatility Regime Detection**
- Low volatility (compression) → breakout pending
- High volatility → mean reversion likely
- ATR percentile ranking
- Volatility clustering

**B. Momentum Divergence**
- Price vs momentum indicator divergence
- Volume-weighted momentum
- Multi-timeframe momentum agreement

**C. Pattern Recognition**
- Double tops/bottoms
- Head and shoulders
- Triangle breakouts
- Flag/pennant patterns

---

## Phase 3: Feature Implementation (Day 6-8)

### File Structure

Create: `backend/app/ml/forex_features.py`

```python
class ForexFeatureEngineer:
    """
    Forex-specific feature engineering for currency pairs like EURUSD.

    Focus areas:
    - Mean reversion patterns
    - Support/Resistance levels
    - Session-based analysis
    - Range vs Trend detection
    - Interest rate differential proxies
    """

    def build_forex_features(self, df):
        """Build comprehensive forex feature set"""
        df = self.add_base_features(df)
        df = self.add_mean_reversion_features(df)
        df = self.add_session_features(df)
        df = self.add_support_resistance_features(df)
        df = self.add_volatility_regime_features(df)
        df = self.add_trend_range_features(df)
        return df
```

### Key Methods

1. **add_mean_reversion_features()**
   - Z-score from various MAs
   - Bollinger Band position
   - RSI extremes
   - Stochastic levels

2. **add_session_features()**
   - Hour of day
   - Day of week
   - Session volatility patterns
   - Time-based momentum

3. **add_support_resistance_features()**
   - Distance to round numbers
   - Pivot points
   - Recent swing levels
   - Psychological level proximity

4. **add_volatility_regime_features()**
   - ATR percentile
   - Volatility clustering
   - Compression vs expansion
   - Regime classification

5. **add_trend_range_features()**
   - ADX for trend strength
   - Donchian channel analysis
   - Range width
   - Breakout detection

---

## Phase 4: Model Training (Day 9-11)

### 4.1 Training Configuration

**File:** `train_eurusd_forex.py`

```python
EURUSD_FOREX_CONFIG = {
    'spread_pips': 1.5,
    'profit_target_atr': 1.5,  # Start wider
    'stop_loss_atr': 1.0,      # Balanced
    'max_holding_hours': 24,   # Allow daily cycles
    'description': 'EURUSD - Forex Pair (Forex-Optimized)',

    # Forex-specific parameters
    'min_adx': 20,              # Lower threshold for forex
    'use_session_filter': True,  # Trade during liquid sessions
    'use_sr_filter': True,       # Respect S/R levels
    'mean_reversion_mode': True, # Enable MR strategies
}
```

### 4.2 Multiple Model Approaches

Test 3 different strategies:

**A. Trend-Following Model**
- Use when ADX > 25
- Momentum alignment required
- Wider TP/SL (2.0:1.2)

**B. Mean-Reversion Model**
- Use when price at extremes (RSI <30 or >70)
- Near support/resistance
- Tighter TP/SL (0.8:0.6)

**C. Hybrid Model**
- Regime detection first
- Apply appropriate strategy based on regime
- Adaptive TP/SL

### 4.3 Target Engineering

Create forex-specific targets:
- Shorter holding periods (mean reversion)
- Respect S/R levels in TP calculation
- Avoid news events (use session filters)

---

## Phase 5: Backtesting (Day 12-15)

### 5.1 Comprehensive Backtesting

Test configurations:
- Multiple confidence thresholds (35%-65%)
- Multiple TP/SL combinations:
  - Conservative: 1.0:0.8
  - Balanced: 1.5:1.0
  - Aggressive: 2.0:1.2
- Session filters (trade only London + NY)
- S/R filters (avoid major levels)

### 5.2 Walk-Forward Analysis

- Train on 2020-2023
- Test on 2024-2025
- Validate model doesn't overfit

### 5.3 Comparison

Compare with baseline (original XAUUSD-approach model):
- Profit Factor improvement
- Win Rate improvement
- Consistency across different periods

---

## Phase 6: Optimization (Day 16-18)

### 6.1 Hyperparameter Tuning

Optimize:
- XGBoost parameters (depth, learning rate, trees)
- Feature selection (remove low-importance features)
- Confidence thresholds
- TP/SL ratios

### 6.2 Ensemble Testing

If single model not profitable enough:
- Combine trend + mean-reversion models
- Use regime detector to switch strategies
- Ensemble multiple timeframes

---

## Phase 7: Validation (Day 19-21)

### 7.1 Final Validation

- Out-of-sample testing
- Multiple market conditions
- Monte Carlo simulation
- Sensitivity analysis

### 7.2 Production Readiness

**Success Criteria:**
- ✅ Profit Factor > 1.5
- ✅ Win Rate > 60%
- ✅ Minimum 500 trades in backtest
- ✅ Consistent across different periods
- ✅ Robust to parameter changes

---

## Key Differences: EURUSD vs XAUUSD

| Aspect | XAUUSD (Gold) | EURUSD (Forex) |
|--------|---------------|----------------|
| **Behavior** | Trending, directional | Mean-reverting, range-bound |
| **Drivers** | Safe haven, inflation | Interest rates, economic data |
| **Volatility** | High, expanding | Lower, cyclical |
| **S/R Respect** | Moderate | Very high (psychological levels) |
| **Session Impact** | Moderate | Very high (London/NY) |
| **Best Strategy** | Trend-following | Hybrid (trend + MR) |
| **TP/SL** | Wide (momentum) | Balanced (respect levels) |

---

## Risk Mitigation

### Risk 1: Forex features may not improve profitability
**Mitigation:**
- Test incrementally (add feature groups one by one)
- Compare each addition vs baseline
- A/B test with and without specific features

### Risk 2: Still unprofitable after development
**Fallback:**
- Document learnings
- Focus resources on XAUUSD
- Revisit EURUSD later with ML advances

### Risk 3: Overfitting on historical data
**Mitigation:**
- Walk-forward validation
- Out-of-sample testing
- Parameter sensitivity analysis
- Monte Carlo simulation

---

## Success Metrics

### Minimum Viable Product (MVP):
- PF > 1.3 (acceptable)
- WR > 55% (acceptable)
- Consistent across validation periods

### Target Performance:
- PF > 1.5 (good)
- WR > 60% (good)
- ROI > 30% on backtest period

### Stretch Goal:
- PF > 1.8 (excellent)
- WR > 65% (excellent)
- Match XAUUSD quality

---

## Development Phases Summary

| Phase | Days | Deliverable | Success Metric |
|-------|------|-------------|----------------|
| 1. Data | 1 | Recent EURUSD data | >50k candles |
| 2-3. Features | 7 | forex_features.py | >80 features |
| 4. Training | 3 | Forex-optimized model | Accuracy >45% |
| 5. Backtest | 4 | Performance results | PF >1.3 |
| 6. Optimize | 3 | Tuned configuration | PF >1.5 |
| 7. Validate | 3 | Production model | Ready for demo |

**Total:** 21 days (3 weeks)

---

## Files to Create

1. `backend/app/ml/forex_features.py` - Forex feature engineering
2. `train_eurusd_forex.py` - Training script
3. `backtest_eurusd_forex.py` - Backtesting script
4. `optimize_eurusd_params.py` - Parameter optimization
5. `download_recent_eurusd.py` - Data download script
6. `EURUSD_FOREX_RESULTS.md` - Final results documentation

---

## Next Immediate Steps

1. ✅ Create this plan document
2. Download recent EURUSD data (2020-2025)
3. Start building forex_features.py
4. Implement mean reversion features first
5. Add session and S/R features
6. Train initial model and evaluate

---

**Last Updated:** 2025-12-13
**Status:** Plan approved, ready to execute
**Current Phase:** Starting Phase 1 - Data Acquisition
