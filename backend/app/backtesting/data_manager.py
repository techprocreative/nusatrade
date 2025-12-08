"""Data manager for backtesting with historical market data."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import get_logger


logger = get_logger(__name__)


class DataManager:
    """Manages historical market data for backtesting."""

    SUPPORTED_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        self.symbol = symbol.upper()
        self.timeframe = timeframe.upper()
        self.start_date = start_date
        self.end_date = end_date
        self._data: Optional[pd.DataFrame] = None
        self._validate()

    def _validate(self):
        """Validate initialization parameters."""
        if self.timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

    def load(self) -> pd.DataFrame:
        """Load data from cache or source."""
        if self._data is not None:
            return self._data
        raise ValueError("No data loaded. Call load_from_csv or load_from_db first.")

    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        """Load historical data from a CSV file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Data file not found: {filepath}")

        logger.info(f"Loading data from {filepath}")

        df = pd.read_csv(filepath, parse_dates=["timestamp"])
        df = self._normalize_columns(df)
        df = self._filter_date_range(df)
        df = df.sort_values("timestamp").reset_index(drop=True)

        self._data = df
        logger.info(f"Loaded {len(df)} candles for {self.symbol} {self.timeframe}")
        return df

    def load_from_db(self, db: Session) -> pd.DataFrame:
        """Load historical data from the database."""
        from app.models.backtest import HistoricalData

        query = db.query(HistoricalData).filter(
            HistoricalData.symbol == self.symbol,
            HistoricalData.timeframe == self.timeframe,
        )

        if self.start_date:
            query = query.filter(HistoricalData.timestamp >= self.start_date)
        if self.end_date:
            query = query.filter(HistoricalData.timestamp <= self.end_date)

        query = query.order_by(HistoricalData.timestamp)

        records = query.all()

        if not records:
            raise ValueError(f"No data found for {self.symbol} {self.timeframe}")

        df = pd.DataFrame([
            {
                "timestamp": r.timestamp,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume) if r.volume else 0,
            }
            for r in records
        ])

        self._data = df
        logger.info(f"Loaded {len(df)} candles from database")
        return df

    def load_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Load data from an existing DataFrame."""
        df = self._normalize_columns(df.copy())
        df = self._filter_date_range(df)
        self._data = df.sort_values("timestamp").reset_index(drop=True)
        return self._data

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format."""
        column_mapping = {
            "date": "timestamp",
            "datetime": "timestamp",
            "time": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
            "vol": "volume",
        }

        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns=column_mapping)

        required = ["timestamp", "open", "high", "low", "close"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ensure datetime
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df

    def _filter_date_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter data to the specified date range."""
        if self.start_date:
            df = df[df["timestamp"] >= self.start_date]
        if self.end_date:
            df = df[df["timestamp"] <= self.end_date]
        return df

    def get_candle(self, index: int) -> Optional[Dict]:
        """Get a single candle by index."""
        if self._data is None or index < 0 or index >= len(self._data):
            return None
        row = self._data.iloc[index]
        return row.to_dict()

    def get_range(self, start_idx: int, end_idx: int) -> pd.DataFrame:
        """Get a range of candles."""
        if self._data is None:
            return pd.DataFrame()
        return self._data.iloc[start_idx:end_idx].copy()

    @property
    def length(self) -> int:
        """Get the number of candles."""
        return len(self._data) if self._data is not None else 0

    def resample(self, target_timeframe: str) -> pd.DataFrame:
        """Resample data to a different timeframe."""
        if self._data is None:
            raise ValueError("No data loaded")

        timeframe_map = {
            "M5": "5T",
            "M15": "15T",
            "M30": "30T",
            "H1": "1H",
            "H4": "4H",
            "D1": "1D",
            "W1": "1W",
            "MN1": "1M",
        }

        if target_timeframe not in timeframe_map:
            raise ValueError(f"Cannot resample to {target_timeframe}")

        df = self._data.set_index("timestamp")
        resampled = df.resample(timeframe_map[target_timeframe]).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna().reset_index()

        return resampled
