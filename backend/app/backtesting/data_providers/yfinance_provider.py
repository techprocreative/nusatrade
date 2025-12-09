"""Yahoo Finance data provider for historical forex data."""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional

from app.core.logging import get_logger


logger = get_logger(__name__)


class YFinanceDataProvider:
    """Download historical forex/market data from Yahoo Finance."""

    # Map internal symbol names to yfinance tickers
    SYMBOL_MAP = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "USDCAD": "USDCAD=X",
        "USDCHF": "USDCHF=X",
        "NZDUSD": "NZDUSD=X",
        "EURGBP": "EURGBP=X",
        "EURJPY": "EURJPY=X",
        "GBPJPY": "GBPJPY=X",
        # Commodities
        "XAUUSD": "GC=F",  # Gold futures
        "XAGUSD": "SI=F",  # Silver futures
        # Crypto (optional)
        "BTCUSD": "BTC-USD",
        "ETHUSD": "ETH-USD",
    }

    # Map internal timeframe to yfinance interval
    TIMEFRAME_MAP = {
        "M1": "1m",    # Max 7 days
        "M2": "2m",    # Max 60 days
        "M5": "5m",    # Max 60 days
        "M15": "15m",  # Max 60 days
        "M30": "30m",  # Max 60 days
        "H1": "1h",    # Max 730 days
        "H4": "1h",    # Will resample from 1h
        "D1": "1d",    # Unlimited
        "W1": "1wk",   # Unlimited
        "MN1": "1mo",  # Unlimited
    }

    # Maximum days of data available per interval
    INTERVAL_MAX_DAYS = {
        "1m": 7,
        "2m": 60,
        "5m": 60,
        "15m": 60,
        "30m": 60,
        "1h": 730,
        "1d": None,  # Unlimited
        "1wk": None,
        "1mo": None,
    }

    def __init__(self):
        pass

    def get_ticker(self, symbol: str) -> str:
        """Convert internal symbol to yfinance ticker."""
        symbol_upper = symbol.upper()
        return self.SYMBOL_MAP.get(symbol_upper, f"{symbol_upper}=X")

    def get_interval(self, timeframe: str) -> str:
        """Convert internal timeframe to yfinance interval."""
        timeframe_upper = timeframe.upper()
        return self.TIMEFRAME_MAP.get(timeframe_upper, "1d")

    def download(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """
        Download OHLCV data from Yahoo Finance.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe (e.g., "H1", "D1")
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ticker = self.get_ticker(symbol)
        interval = self.get_interval(timeframe)
        needs_resample = timeframe.upper() == "H4"

        # Check max days limit
        max_days = self.INTERVAL_MAX_DAYS.get(interval)
        if max_days:
            days_requested = (end_date - start_date).days
            if days_requested > max_days:
                logger.warning(
                    f"Requested {days_requested} days but {interval} interval only supports {max_days} days. "
                    f"Adjusting start date."
                )
                start_date = end_date - timedelta(days=max_days)

        logger.info(f"Downloading {symbol} ({ticker}) {timeframe} from {start_date} to {end_date}")

        try:
            df = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True,
                progress=False,
            )

            if df.empty:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return pd.DataFrame()

            # Reset index to get timestamp as column
            df = df.reset_index()

            # Handle multi-level columns from yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            # Normalize column names
            df.columns = [col.lower() for col in df.columns]
            
            # Rename date/datetime to timestamp
            if "date" in df.columns:
                df = df.rename(columns={"date": "timestamp"})
            elif "datetime" in df.columns:
                df = df.rename(columns={"datetime": "timestamp"})

            # Ensure we have required columns
            required_cols = ["timestamp", "open", "high", "low", "close"]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")

            # Add volume if missing (forex typically has 0 volume)
            if "volume" not in df.columns:
                df["volume"] = 0

            # Select and order columns
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]

            # Resample to H4 if needed
            if needs_resample:
                df = self._resample_to_h4(df)

            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            logger.info(f"Downloaded {len(df)} candles for {symbol} {timeframe}")
            return df

        except Exception as e:
            logger.error(f"Failed to download data from yfinance: {e}")
            raise

    def _resample_to_h4(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample H1 data to H4."""
        df = df.set_index("timestamp")
        
        resampled = df.resample("4H").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()
        
        return resampled.reset_index()

    def get_available_symbols(self) -> list:
        """Return list of available symbols."""
        return list(self.SYMBOL_MAP.keys())

    def get_available_timeframes(self) -> list:
        """Return list of available timeframes."""
        return list(self.TIMEFRAME_MAP.keys())
