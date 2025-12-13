-- Fix model paths in default_ml_models table
-- Remove 'models/' prefix from paths

UPDATE default_ml_models
SET model_path = 'model_xgboost_20251212_235414.pkl'
WHERE symbol = 'XAUUSD' AND model_path LIKE 'models/%';

UPDATE default_ml_models
SET model_path = 'eurusd/forex-optimized/model_forex_xgboost_20251213_112218.pkl'
WHERE symbol = 'EURUSD' AND model_path LIKE 'models/%';

UPDATE default_ml_models
SET model_path = 'btcusd/crypto-optimized/model_crypto_xgboost_20251213_104319.pkl'
WHERE symbol = 'BTCUSD' AND model_path LIKE 'models/%';

-- Verify changes
SELECT symbol, model_path, model_id, win_rate, profit_factor
FROM default_ml_models
ORDER BY symbol;
