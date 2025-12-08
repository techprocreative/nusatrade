"""ML Model Training Pipeline."""

import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from app.ml.features import FeatureEngineer


class Trainer:
    """ML Model Trainer for forex prediction."""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.feature_engineer = FeatureEngineer()
        self.scaler = StandardScaler()
        self.model = None
        self.feature_columns: List[str] = []

        # Ensure model directory exists
        os.makedirs(model_dir, exist_ok=True)

    def prepare_data(
        self,
        df: pd.DataFrame,
        target_column: str = "target",
        lookahead: int = 5,
        threshold: float = 0.0005,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training."""
        # Build features
        df = self.feature_engineer.build_features(df)

        # Create target: 1 if price goes up by threshold, 0 otherwise
        df["future_return"] = df["close"].shift(-lookahead) / df["close"] - 1
        df[target_column] = (df["future_return"] > threshold).astype(int)

        # Drop rows with NaN
        df = df.dropna()

        # Select feature columns (exclude OHLCV and target)
        exclude_cols = ["open", "high", "low", "close", "volume", "timestamp", 
                        "future_return", target_column]
        self.feature_columns = [c for c in df.columns if c not in exclude_cols]

        X = df[self.feature_columns]
        y = df[target_column]

        return X, y

    def train(
        self,
        data: pd.DataFrame = None,
        model_type: str = "random_forest",
        test_split: float = 0.2,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Train the ML model."""
        config = config or {}

        # Use provided data or generate sample
        if data is None or len(data) == 0:
            data = self._generate_sample_data()

        # Prepare features
        X, y = self.prepare_data(
            data,
            lookahead=config.get("lookahead", 5),
            threshold=config.get("threshold", 0.0005),
        )

        if len(X) < 100:
            return {
                "success": False,
                "error": "Not enough data for training (minimum 100 samples)",
                "model_path": None,
                "metrics": {},
            }

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_split, shuffle=False  # Don't shuffle time series
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Create model
        if model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=config.get("n_estimators", 100),
                max_depth=config.get("max_depth", 5),
                learning_rate=config.get("learning_rate", 0.1),
                random_state=42,
            )
        else:  # random_forest
            self.model = RandomForestClassifier(
                n_estimators=config.get("n_estimators", 100),
                max_depth=config.get("max_depth", 10),
                min_samples_split=config.get("min_samples_split", 5),
                random_state=42,
                n_jobs=-1,
            )

        # Train
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        metrics = {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
            "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(self.feature_columns),
            "class_distribution": {
                "train_positive": int(y_train.sum()),
                "train_negative": int(len(y_train) - y_train.sum()),
                "test_positive": int(y_test.sum()),
                "test_negative": int(len(y_test) - y_test.sum()),
            },
        }

        # Get feature importance
        if hasattr(self.model, "feature_importances_"):
            importance = dict(zip(
                self.feature_columns,
                [round(float(x), 4) for x in self.model.feature_importances_]
            ))
            # Top 10 features
            sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            metrics["top_features"] = dict(sorted_importance[:10])

        # Save model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"model_{model_type}_{timestamp}.pkl"
        model_path = os.path.join(self.model_dir, model_filename)

        self._save_model(model_path)

        return {
            "success": True,
            "model_path": model_path,
            "metrics": metrics,
            "model_type": model_type,
            "trained_at": datetime.utcnow().isoformat(),
        }

    def predict(self, features: pd.DataFrame) -> Dict[str, Any]:
        """Make prediction with trained model."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Ensure features are in correct order
        X = features[self.feature_columns]
        X_scaled = self.scaler.transform(X)

        prediction = self.model.predict(X_scaled)
        probability = self.model.predict_proba(X_scaled)

        return {
            "prediction": int(prediction[0]),
            "direction": "BUY" if prediction[0] == 1 else "SELL",
            "confidence": float(max(probability[0])),
            "probabilities": {
                "sell": float(probability[0][0]),
                "buy": float(probability[0][1]),
            },
        }

    def _save_model(self, path: str):
        """Save model, scaler, and feature columns."""
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_columns": self.feature_columns,
            "saved_at": datetime.utcnow().isoformat(),
        }
        with open(path, "wb") as f:
            pickle.dump(model_data, f)

    def load_model(self, path: str):
        """Load a trained model."""
        with open(path, "rb") as f:
            model_data = pickle.load(f)

        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.feature_columns = model_data["feature_columns"]

    def _generate_sample_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """Generate sample OHLCV data for testing."""
        np.random.seed(42)

        dates = pd.date_range(end=datetime.now(), periods=n_samples, freq="h")
        base_price = 1.0850

        returns = np.random.randn(n_samples) * 0.001
        close_prices = base_price * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            "timestamp": dates,
            "open": close_prices * (1 + np.random.randn(n_samples) * 0.0005),
            "high": close_prices * (1 + abs(np.random.randn(n_samples) * 0.001)),
            "low": close_prices * (1 - abs(np.random.randn(n_samples) * 0.001)),
            "close": close_prices,
            "volume": np.random.randint(1000, 10000, n_samples),
        })

        return df


def train_model_from_csv(
    csv_path: str,
    model_type: str = "random_forest",
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function to train from CSV file."""
    df = pd.read_csv(csv_path)
    trainer = Trainer()
    return trainer.train(df, model_type=model_type, config=kwargs)
