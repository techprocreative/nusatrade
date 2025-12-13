# BTC Model Training Results

## Training Summary

**Date:** 2025-12-13
**Symbol:** BTCUSD (Bitcoin)
**Model Type:** Gradient Boosting Classifier
**Training Duration:** ~12 minutes

---

## Training Metrics

| Metric | Value |
|--------|-------|
| **Data Points** | 69,548 candles (2018-2025) |
| **Train Samples** | 55,479 (80%) |
| **Test Samples** | 13,870 (20%) |
| **Training Accuracy** | 35.0% |

### Target Distribution
- HOLD: 49.4%
- SELL: 25.8%
- BUY: 24.8%

### Top Features for BTC
1. OBV (On-Balance Volume) - 6.14%
2. Volume SMA 20 - 5.43%
3. ADX - 4.52%
4. Volume Ratio - 3.79%
5. ATR Percent - 3.68%

---

## Backtest Results

### Performance (7 months backtest: May 2024 - Dec 2025)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Total Trades** | 750 | - | ✅ |
| **Win Rate** | 42.5% | >60% | ❌ |
| **Profit Factor** | 1.16 | >1.5 | ❌ |
| **ROI** | +411% | - | ✅ |
| **Net Profit** | $41,107 | - | ✅ |

### Trade Distribution
- Winning Trades: 319 (42.5%)
- Losing Trades: 431 (57.5%)
- Avg Win: $927.63
- Avg Loss: $591.20
- Risk/Reward: 1:1.57

### Signal Distribution (65% confidence)
- HOLD: 87.0%
- SELL: 12.6%
- BUY: 0.4%

---

## Assessment

### ❌ MODEL NOT READY FOR PRODUCTION

**Reasons:**
1. **Win Rate Too Low:** 42.5% << 60% target
   - Model loses more often than it wins
   - High uncertainty in predictions

2. **Profit Factor Below Target:** 1.16 << 1.5 target
   - Not enough edge over break-even
   - Risk/reward not sustainable long-term

3. **Highly Imbalanced Signals:**
   - Only 0.4% BUY signals (too conservative)
   - May miss profitable opportunities

### ✅ Positive Indicators
- High ROI (+411%) shows potential
- Good Risk/Reward ratio (1:1.57)
- Large profit per winning trade ($927 avg)
- 750 trades = sufficient sample size

---

## Root Cause Analysis

### Why BTC Model Underperforms vs XAUUSD?

| Aspect | XAUUSD (Gold) | BTCUSD (Bitcoin) |
|--------|---------------|------------------|
| **Volatility** | Low-Medium | VERY HIGH |
| **Price Range** | $1,800-$2,100 (2018-2025) | $3,172-$126,011 (40x range!) |
| **Market Hours** | 23h/day | 24/7 non-stop |
| **Drivers** | Macro factors, USD | Sentiment, news, whales |
| **Patterns** | Mean-reverting | Trend-following + chaotic |
| **Model Accuracy** | High (75% WR) | Low (35% accuracy) |

**Conclusion:** Bitcoin's extreme volatility and unpredictability makes it harder for ML models to predict accurately.

---

## Recommendations

### Option 1: Retrain with Different Parameters ⚙️

```bash
# Try more aggressive targets for crypto
backend/venv/bin/python3 train_symbol_model.py \
  --symbol BTCUSD \
  --model-type xgboost

# With adjusted config:
# - profit_target_atr: 2.0 (larger targets)
# - stop_loss_atr: 1.5 (wider stops)
# - max_holding_hours: 4 (faster moves)
```

### Option 2: Add Crypto-Specific Features 📊

BTC needs different features than Gold:
- **Volume analysis** (whale movements)
- **Funding rates** (perpetual futures)
- **Social sentiment** (Twitter, Reddit)
- **Exchange flows** (on-chain data)
- **Weekend gaps** (24/7 trading)

### Option 3: Use Ensemble/Hybrid Approach 🤖

Combine ML with traditional strategies:
- ML for trend direction
- RSI/MACD for entry timing
- Volume confirmation
- Multiple timeframes

### Option 4: Focus on XAUUSD Only (Recommended) ✅

**Rationale:**
- XAUUSD model is **proven profitable** (75% WR, 2.02 PF)
- BTC too volatile for current ML approach
- Better to have 1 **excellent** model than 2 mediocre ones

**Action Plan:**
1. **Keep XAUUSD in production** (already profitable)
2. **Mark BTC as experimental** (staging only)
3. **Research before retraining:**
   - Study successful crypto ML strategies
   - Add crypto-specific features
   - Consider deep learning (LSTM/Transformer)
4. **Try EURUSD next** (more similar to Gold)

---

## Next Steps

### Immediate Action
- [x] Document BTC results ✅
- [ ] Update MULTI_SYMBOL_STATUS.md
- [ ] Keep model in staging (do NOT move to production)
- [ ] Try EURUSD training (more stable than BTC)

### Research Phase (Before Retry)
- [ ] Study crypto-specific ML features
- [ ] Analyze BTC volatility regimes
- [ ] Consider alternative models (LSTM, XGBoost with crypto features)
- [ ] Gather on-chain data sources

### Testing on Demo
If retrained model shows improvement:
- Target: WR > 55%, PF > 1.3 (lower bars for crypto)
- Test on demo for 60 days (longer than forex)
- Monitor during high volatility events

---

## Conclusion

**BTC Model Status: NOT PROFITABLE (Staging Only)**

While the BTC model shows potential with high ROI, the low win rate (42.5%) and profit factor (1.16) indicate it's **not reliable enough for live trading**.

**Recommendation:** Focus on **XAUUSD** (proven) and **EURUSD** (similar characteristics). Postpone BTC deployment until crypto-specific features and strategies are developed.

---

**Model File:** `models/btcusd/staging/model_gradient_boosting_20251213_085347.pkl`
**Status:** Experimental - NOT for production
**Action:** Keep in staging, continue research
