"""Market Data Service - Fetches real market data from various sources.

This module provides a unified interface for fetching market data
used by ML predictions and auto-trading services.
"""

from typing import Optional, Dict, Any
import pandas as pd

from app.core.logging import get_logger


logger = get_logger(__name__)


class MarketDataFetcher:
    """Fetches real market data for prediction and trading."""
    
    # Map forex symbols to yfinance tickers
    SYMBOL_MAP = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "USDCAD": "USDCAD=X",
        "USDCHF": "USDCHF=X",
        "NZDUSD": "NZDUSD=X",
        "XAUUSD": "GC=F",  # Gold futures
        "BTCUSD": "BTC-USD",
    }
    
    TIMEFRAME_MAP = {
        "M1": "1m",
        "M5": "5m",
        "M15": "15m",
        "M30": "30m",
        "H1": "1h",
        "H4": "4h",
        "D1": "1d",
    }
    
    @classmethod
    def fetch_data(cls, symbol: str, timeframe: str = "H1", bars: int = 200) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from yfinance.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe (e.g., "H1", "M15")
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        import yfinance as yf
        
        ticker = cls.SYMBOL_MAP.get(symbol.upper(), f"{symbol}=X")
        interval = cls.TIMEFRAME_MAP.get(timeframe.upper(), "1h")
        
        # Determine period based on interval
        if interval in ["1m", "5m", "15m", "30m"]:
            period = "7d"
        elif interval in ["1h", "4h"]:
            period = "60d"
        else:
            period = "2y"
        
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            
            if data.empty:
                logger.warning(f"No data returned for {ticker}")
                return None
            
            # Rename columns to lowercase
            data.columns = [c.lower() for c in data.columns]
            data = data.reset_index()
            
            # Handle timezone-aware datetime
            if 'datetime' in data.columns:
                data = data.rename(columns={'datetime': 'timestamp'})
            elif 'date' in data.columns:
                data = data.rename(columns={'date': 'timestamp'})
            
            # Only return last N bars
            data = data.tail(bars).reset_index(drop=True)
            
            logger.info(f"Fetched {len(data)} bars for {symbol} ({timeframe})")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None
    
    @classmethod
    def get_current_price(cls, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            
        Returns:
            Current price or None if failed
        """
        import yfinance as yf
        
        ticker = cls.SYMBOL_MAP.get(symbol.upper(), f"{symbol}=X")
        
        try:
            data = yf.download(ticker, period="1d", interval="1m", progress=False)
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
        
        return None
    
    @classmethod
    def get_symbol_info(cls, symbol: str) -> Dict[str, Any]:
        """
        Get symbol information including pip value calculations.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with symbol info
        """
        # Standard forex pip values
        pip_info = {
            "EURUSD": {"pip_size": 0.0001, "pip_value": 10.0},
            "GBPUSD": {"pip_size": 0.0001, "pip_value": 10.0},
            "USDJPY": {"pip_size": 0.01, "pip_value": 9.0},
            "AUDUSD": {"pip_size": 0.0001, "pip_value": 10.0},
            "USDCAD": {"pip_size": 0.0001, "pip_value": 7.5},
            "USDCHF": {"pip_size": 0.0001, "pip_value": 10.0},
            "NZDUSD": {"pip_size": 0.0001, "pip_value": 10.0},
            "XAUUSD": {"pip_size": 0.01, "pip_value": 1.0},
            "BTCUSD": {"pip_size": 1.0, "pip_value": 1.0},
        }
        
        info = pip_info.get(symbol.upper(), {"pip_size": 0.0001, "pip_value": 10.0})
        info["symbol"] = symbol.upper()
        
        # Get current price
        current_price = cls.get_current_price(symbol)
        if current_price:
            info["current_price"] = current_price
        
        return info


# Default prices for fallback
DEFAULT_PRICES = {
    "EURUSD": 1.0850,
    "GBPUSD": 1.2650,
    "USDJPY": 149.50,
    "AUDUSD": 0.6550,
    "USDCAD": 1.3650,
    "USDCHF": 0.8850,
    "NZDUSD": 0.6150,
    "XAUUSD": 2050.00,
    "BTCUSD": 42000.00,
}


def get_default_price(symbol: str) -> float:
    """Get default price for a symbol when market data is unavailable."""
    return DEFAULT_PRICES.get(symbol.upper(), 1.0)
