# Multi-Symbol ML Strategy - Implementation Status

## Overview

The ML Profitable Strategy was initially trained exclusively on **XAUUSD (Gold)** data. This document tracks the implementation of multi-symbol support to enable trading on EURUSD, BTCUSD, and other symbols.

---

## Current Status: PHASE 1 COMPLETE ✅

### Phase 1: XAUUSD-Only Enforcement (COMPLETED)

**Goal:** Prevent users from accidentally using the XAUUSD-trained model on other symbols.

**Implementation:**

#### Backend Validation ✅
1. **ml_profitable_strategy.py**
   - Added `SUPPORTED_SYMBOLS = ["XAUUSD"]`
   - Symbol validation in `__init__()` with ValueError for invalid symbols
   - Static methods: `get_supported_symbols()`, `is_symbol_supported()`
   - Updated docstrings with XAUUSD-only warnings

2. **ml_auto_trading.py**
   - Symbol validation before processing signals
   - Early return with descriptive error for unsupported symbols
   - Warning logs for invalid attempts

3. **optimized_predictor.py**
   - Added `SUPPORTED_SYMBOLS` constant
   - Symbol parameter with validation in constructor
   - Raises ValueError for unsupported symbols

4. **strategies API**
   - Clone endpoint forces `symbol = "XAUUSD"` in config
   - Adds `supported_symbols: ["XAUUSD"]` to metadata
   - Appends symbol restriction to description

#### Frontend Warnings ✅
1. **MLProfitableStrategyCard.tsx**
   - "XAUUSD ONLY" badge next to title
   - "Trained on: XAUUSD (Gold) Only" in configuration list
   - Dedicated blue Alert explaining symbol limitation
   - Updated card description

**Testing:**
- ✅ User cannot clone strategy for non-XAUUSD symbols
- ✅ Auto-trading validates symbol before predictions
- ✅ Clear error messages in logs and UI
- ✅ Database enforces XAUUSD symbol

**Commit:** `6853070` - feat(phase1): lock ML model to XAUUSD with comprehensive validation

---

## Phase 2: Multi-Symbol Infrastructure (IN PROGRESS)

### Goal
Enable support for multiple symbols by training separate models and creating infrastructure for symbol-specific model selection.

### Priority Symbols
1. **EURUSD** - Most liquid forex pair
2. **BTCUSD** - High volatility crypto

### Implementation Tasks

#### 2.1 Enhanced Model Registry
**File:** `backend/app/services/model_registry.py`

**Current Status:** File exists, needs enhancement
**Tasks:**
- [ ] Add `symbol` field to ModelMetadata
- [ ] Implement `get_model_by_symbol(symbol: str)`
- [ ] Implement `list_models_for_symbol(symbol: str)`
- [ ] Update directory structure:
  ```
  models/
    ├── xauusd/
    │   ├── production/model_xgboost_20251212_235414.pkl
    │   └── staging/
    ├── eurusd/
    │   ├── production/
    │   └── staging/
    └── btcusd/
        ├── production/
        └── staging/
  ```

#### 2.2 Symbol-Specific Training Pipeline
**New File:** `train_symbol_model.py`

**Tasks:**
- [ ] Create training script accepting `--symbol` argument
- [ ] Load data from `ohlcv/{symbol}/{symbol}_1h_clean.csv`
- [ ] Use ImprovedFeatureEngineer (symbol-agnostic features)
- [ ] Save model to `models/{symbol}/staging/`
- [ ] Auto-run backtests
- [ ] Promote to production only if profitable (PF > 1.5, WR > 60%)

**New File:** `scripts/download_symbol_data.py`

**Tasks:**
- [ ] Download EURUSD historical data (yfinance or MT5)
- [ ] Download BTCUSD historical data
- [ ] Save to `ohlcv/{symbol}/{symbol}_1h_clean.csv`
- [ ] Ensure same format as XAUUSD data

#### 2.3 Auto-Trading Symbol Matching
**File:** `backend/app/services/ml_auto_trading.py`

**Tasks:**
- [ ] Get model's supported symbol from strategy config
- [ ] Match trading pair with available models
- [ ] Return "NO_MODEL" signal if symbol not supported
- [ ] Log warnings for unavailable symbols

**File:** `backend/app/strategies/ml_profitable_strategy.py`

**Tasks:**
- [ ] Make symbol configurable via `__init__` parameter
- [ ] Support XAUUSD, EURUSD, BTCUSD
- [ ] Load appropriate model file based on symbol
- [ ] Validate model exists before initialization

#### 2.4 UI - Symbol Selection
**File:** `frontend/components/strategies/MLProfitableStrategyCard.tsx`

**Tasks:**
- [ ] Add symbol dropdown (XAUUSD, EURUSD, BTCUSD)
- [ ] Show "Not Available Yet" for untrained symbols
- [ ] Display different performance metrics per symbol
- [ ] Update clone to include selected symbol

**New Component:** `frontend/components/strategies/SymbolModelStatus.tsx`

**Tasks:**
- [ ] Display list of all symbols
- [ ] Show training status (✅ Available, ⏳ Training, ❌ Not Trained)
- [ ] Display performance metrics if trained
- [ ] "Start Training" button for admins

---

## Implementation Timeline

### Week 1: Phase 1 (COMPLETED ✅)
- Day 1-2: Backend validation ✅
- Day 3: Frontend warnings ✅
- Day 4: API enforcement ✅
- Day 5: Testing and commit ✅

### Week 2-3: Phase 2 (PLANNED)
- **Day 1-3:** Download EURUSD data + train model
- **Day 4-6:** Download BTCUSD data + train model
- **Day 7-10:** Backtest both models (require 30+ days data)
- **Day 11-14:** If profitable → Implement multi-symbol UI
- **Day 15-21:** Testing and gradual rollout

---

## Testing Strategy

### Phase 1 Testing (COMPLETED ✅)
- [x] Clone ML strategy → Auto-set to XAUUSD
- [x] Try to use strategy with EURUSD → Show error/warning
- [x] Check UI shows "XAUUSD ONLY" badge
- [x] Verify auto-trading validates symbols

### Phase 2 Testing (PENDING)
- [ ] Download EURUSD data → Verify format matches XAUUSD
- [ ] Train EURUSD model → Run backtest → Check profitability
- [ ] Train BTCUSD model → Run backtest → Check profitability
- [ ] Create strategy for each symbol → Verify correct model loaded
- [ ] Test auto-trading with multiple symbols → Each uses correct model

---

## Success Criteria

### Phase 1 (ACHIEVED ✅)
- ✅ No user can accidentally use XAUUSD model for other symbols
- ✅ UI clearly shows symbol limitation
- ✅ Database enforces symbol constraint
- ✅ Comprehensive error messages and logging

### Phase 2 (TARGET)
- ✅ EURUSD model trained and backtested
- ✅ BTCUSD model trained and backtested
- ✅ At least one additional symbol is profitable (PF > 1.5)
- ✅ Users can select and use appropriate model per symbol
- ✅ Auto-trading correctly matches model to symbol

---

## Risk Mitigation

### Risk 1: New Models May Not Be Profitable
**Mitigation:**
- Extensive backtesting before deployment (minimum 30 days)
- Only promote to production if profitable
- Keep XAUUSD-only as fallback

**Fallback:**
- If EURUSD/BTCUSD models not profitable, keep XAUUSD-only
- Document which symbols are not suitable for ML trading

### Risk 2: Feature Engineering May Not Generalize
**Mitigation:**
- Test features on each symbol separately
- Analyze feature importance per symbol
- Adjust hyperparameters symbol-specifically

**Fallback:**
- Create symbol-specific feature sets if needed
- Different feature engineering for forex vs crypto vs commodities

### Risk 3: User Confusion About Symbol Restrictions
**Mitigation:**
- Clear UI messaging
- Help text: "Each model is trained for specific symbol only"
- Disable unavailable symbols in dropdown

**Fallback:**
- Comprehensive documentation
- Video tutorials for multi-symbol usage

---

## File Changes Summary

### Phase 1 (COMPLETED)
1. ✅ `backend/app/strategies/ml_profitable_strategy.py` - Symbol validation
2. ✅ `backend/app/services/ml_auto_trading.py` - Symbol check
3. ✅ `backend/app/services/optimized_predictor.py` - Symbol validation
4. ✅ `frontend/components/strategies/MLProfitableStrategyCard.tsx` - Warnings
5. ✅ `backend/app/api/v1/strategies.py` - Enforce XAUUSD

### Phase 2 (PLANNED)
6. [ ] `backend/app/services/model_registry.py` - Symbol support
7. [ ] `train_symbol_model.py` - New training script
8. [ ] `scripts/download_symbol_data.py` - Data downloader
9. [ ] `frontend/components/strategies/MLProfitableStrategyCard.tsx` - Symbol selector
10. [ ] `frontend/components/strategies/SymbolModelStatus.tsx` - New component

---

## Documentation Updates

### Completed ✅
- [x] This file: `MULTI_SYMBOL_STATUS.md`

### Pending
- [ ] Update `ML_AUTO_TRADING_GUIDE.md` - Add multi-symbol section
- [ ] Update `ML_AUTO_TRADING_SUMMARY.md` - Add symbol info
- [ ] Create `MULTI_SYMBOL_TRAINING_GUIDE.md` - Step-by-step for new symbols

---

## Quick Commands

### Phase 1 (Current - XAUUSD Only)
```bash
# Clone ML strategy (auto-locks to XAUUSD)
curl -X POST http://localhost:8000/api/v1/strategies/templates/ml-profitable/clone \
  -H "Authorization: Bearer <token>"

# Check validation
python -c "from backend.app.strategies.ml_profitable_strategy import MLProfitableStrategy; print(MLProfitableStrategy.get_supported_symbols())"
```

### Phase 2 (Future - Multi-Symbol)
```bash
# Download EURUSD data
python scripts/download_symbol_data.py --symbol EURUSD --timeframe 1H --years 5

# Train EURUSD model
python train_symbol_model.py --symbol EURUSD --optimize

# Check model registry
python -c "from backend.app.services.model_registry import MLModelRegistry; registry = MLModelRegistry(); print(registry.list_models_for_symbol('EURUSD'))"
```

---

## Contact & Support

**Status:** Phase 1 Complete, Phase 2 In Planning
**Last Updated:** 2025-12-13
**Next Review:** Start Phase 2 implementation

For questions or issues, check:
1. This status file for current progress
2. Plan file: `/home/d88k/.claude/plans/glimmering-roaming-steele.md`
3. Commit history: `git log --grep="multi-symbol"`
