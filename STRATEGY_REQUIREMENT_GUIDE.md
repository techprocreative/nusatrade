# Strategy Requirement Implementation Guide

## ✅ IMPLEMENTED: Mandatory Strategy for Auto-Trading

**Status:** Deployed
**Date:** 2025-12-15
**Commit:** 810c0b0

---

## 🎯 What Changed

### User Request:
> "yang saya mau adalah user harus memilih atau membuat strategi terlebih dahulu. jika tidak ada strategi yang digunakan. auto trading tidak bisa jalan"

### Implementation:
**ML models MUST be linked to a strategy before activation.**
**Auto-trading will SKIP models without strategy.**

---

## 📋 New Workflow

### Before (Problematic):
```
1. User clicks "Activate Model"
2. Model activated (is_active = true)
3. Auto-trading runs
4. ❌ NO risk management
5. ❌ NO entry/exit rules
6. ❌ Trades without limits = DANGEROUS
```

### After (Safe):
```
1. User selects/creates strategy
2. User links model to strategy
3. User clicks "Activate Model"
4. Backend validates strategy_id exists
5. Auto-trading runs with strategy rules ✅
6. ✅ Risk management enforced
7. ✅ Safe trading operations
```

---

## 🔧 API Changes

### 1. POST /api/v1/ml/models/{model_id}/activate (Modified)

**Before:**
```json
Request: POST /api/v1/ml/models/123/activate
Response: {
  "status": "active"
}
```

**After:**
```json
Request: POST /api/v1/ml/models/123/activate

Response if NO strategy:
{
  "detail": "Model must be linked to a strategy before activation. Please select or create a strategy first."
}

Response if SUCCESS:
{
  "id": "123",
  "status": "active",
  "strategy_id": "456",
  "strategy_name": "Conservative XAUUSD",
  "message": "Model activated for live trading with strategy"
}
```

---

### 2. POST /api/v1/ml/models/{model_id}/link-strategy (NEW)

**Purpose:** Link model to strategy before activation

**Request:**
```bash
POST /api/v1/ml/models/{model_id}/link-strategy
Content-Type: application/json
Authorization: Bearer {token}

Body:
{
  "strategy_id": "strategy-uuid-here"
}
```

**Response:**
```json
{
  "id": "model-uuid",
  "strategy_id": "strategy-uuid",
  "strategy_name": "Conservative XAUUSD",
  "message": "Model successfully linked to strategy 'Conservative XAUUSD'"
}
```

**Validations:**
- Strategy must exist and belong to user
- Symbol must match (model.symbol == strategy.symbol)
- Both model and strategy IDs must be valid UUIDs

---

### 3. GET /api/v1/ml/strategies/for-model/{symbol} (NEW)

**Purpose:** Get available strategies for a symbol

**Request:**
```bash
GET /api/v1/ml/strategies/for-model/XAUUSD
Authorization: Bearer {token}
```

**Response:**
```json
{
  "symbol": "XAUUSD",
  "count": 3,
  "strategies": [
    {
      "id": "uuid-1",
      "name": "Conservative XAUUSD",
      "description": "Low risk, small positions",
      "strategy_type": "ml_auto",
      "timeframe": "H1",
      "config": {
        "max_lot_size": 0.01,
        "min_confidence": 0.75,
        "max_daily_loss": 50.0
      },
      "created_at": "2025-12-15T10:00:00"
    },
    {
      "id": "uuid-2",
      "name": "Aggressive XAUUSD",
      "description": "Higher risk, larger positions",
      "strategy_type": "ml_auto",
      "timeframe": "H1",
      "config": {
        "max_lot_size": 0.05,
        "min_confidence": 0.60,
        "max_daily_loss": 200.0
      },
      "created_at": "2025-12-15T11:00:00"
    }
  ]
}
```

---

### 4. GET /api/v1/ml/auto-trading/status (Enhanced)

**Before:**
```json
{
  "active_models": 1,
  "predictions_today": 5
}
```

**After:**
```json
{
  "scheduler_running": true,
  "interval_minutes": 15,
  "active_models_with_strategy": 2,
  "active_models_without_strategy": 1,
  "predictions_today": 5,
  "last_run": "2025-12-15T12:00:00",
  "warnings": [
    "1 model(s) need strategy assignment"
  ],
  "config": {
    "default_confidence_threshold": 0.70,
    "default_max_trades_per_day": 5,
    "default_cooldown_minutes": 30
  }
}
```

---

## 🔍 Auto-Trading Service Behavior

### Logs:

**Before fix:**
```
Auto-trading: Checking 1 active models
```

**After fix (with strategies):**
```
Auto-trading: Checking 2 active models with strategies
```

**After fix (with warnings):**
```
Auto-trading: Checking 1 active models with strategies
⚠️  1 active model(s) skipped: no strategy linked. Please link a strategy to enable auto-trading.
```

### SQL Query:

**Before:**
```sql
SELECT * FROM ml_models
WHERE is_active = true
  AND file_path IS NOT NULL;
```

**After:**
```sql
SELECT * FROM ml_models
WHERE is_active = true
  AND file_path IS NOT NULL
  AND strategy_id IS NOT NULL;  -- ← CRITICAL CHANGE
```

---

## 🎨 Frontend Integration Guide

### Step 1: Fetch Available Strategies

```typescript
// Get strategies for model's symbol
const response = await fetch(
  `/api/v1/ml/strategies/for-model/${model.symbol}`,
  {
    headers: { Authorization: `Bearer ${token}` }
  }
);
const data = await response.json();
const strategies = data.strategies;
```

### Step 2: Show Strategy Selection UI

```typescript
// Before activate button, show strategy dropdown
<select onChange={(e) => setSelectedStrategy(e.target.value)}>
  <option value="">Select Strategy...</option>
  {strategies.map(s => (
    <option key={s.id} value={s.id}>
      {s.name} - {s.config.max_lot_size} lot
    </option>
  ))}
</select>

<button onClick={linkStrategy}>Link Strategy</button>
```

### Step 3: Link Strategy

```typescript
async function linkStrategy() {
  await fetch(`/api/v1/ml/models/${modelId}/link-strategy`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ strategy_id: selectedStrategy })
  });
}
```

### Step 4: Activate Model

```typescript
async function activateModel() {
  try {
    const response = await fetch(`/api/v1/ml/models/${modelId}/activate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!response.ok) {
      const error = await response.json();
      // Show error: "Model must be linked to a strategy..."
      alert(error.detail);
    } else {
      const data = await response.json();
      // Show success with strategy name
      alert(`Model activated with ${data.strategy_name}`);
    }
  } catch (error) {
    console.error('Activation failed:', error);
  }
}
```

### Complete Example Flow:

```tsx
function ModelCard({ model }) {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [isLinked, setIsLinked] = useState(!!model.strategy_id);

  // Load strategies on mount
  useEffect(() => {
    loadStrategies();
  }, [model.symbol]);

  async function loadStrategies() {
    const res = await fetch(`/api/v1/ml/strategies/for-model/${model.symbol}`);
    const data = await res.json();
    setStrategies(data.strategies);
  }

  async function handleLinkStrategy() {
    await fetch(`/api/v1/ml/models/${model.id}/link-strategy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy_id: selectedStrategy })
    });
    setIsLinked(true);
  }

  async function handleActivate() {
    if (!isLinked) {
      alert('Please link a strategy first');
      return;
    }

    const res = await fetch(`/api/v1/ml/models/${model.id}/activate`, {
      method: 'POST'
    });

    if (res.ok) {
      alert('Model activated!');
    } else {
      const error = await res.json();
      alert(error.detail);
    }
  }

  return (
    <div className="model-card">
      <h3>{model.name}</h3>

      {!isLinked && (
        <div className="strategy-selector">
          <select onChange={(e) => setSelectedStrategy(e.target.value)}>
            <option value="">Select Strategy...</option>
            {strategies.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <button onClick={handleLinkStrategy}>Link Strategy</button>
        </div>
      )}

      {isLinked && (
        <p className="success">✓ Strategy linked: {model.strategy_name}</p>
      )}

      <button
        onClick={handleActivate}
        disabled={!isLinked}
      >
        Activate Model
      </button>
    </div>
  );
}
```

---

## ✅ Testing Checklist

- [ ] Try activating model without strategy → Should get 400 error
- [ ] Link model to strategy → Should succeed
- [ ] Try activating after linking → Should succeed
- [ ] Check auto-trading status → Should show correct counts
- [ ] Monitor logs → Should see warning for models without strategy
- [ ] Wait for auto-trading cycle → Only models with strategy should trade

---

## 🚀 Deployment

**Backend auto-deploys on Render** when commit is pushed.

**No database migration needed** - uses existing strategy_id column.

**Frontend needs update** to add strategy selection UI.

---

## 📊 Benefits

1. **Safety**: No trades without risk management
2. **Control**: User must consciously choose strategy
3. **Accountability**: All trades linked to strategy
4. **Tracking**: Better performance analysis per strategy
5. **Flexibility**: Can change strategy without retraining model

---

**Status:** ✅ Ready for Production
**Next Step:** Update frontend to add strategy selection UI
