#!/usr/bin/env python3
"""
Download Recent EURUSD Data (2020-2025)

Uses yfinance to download recent EURUSD hourly data for improved model training.
Recent data is more relevant for current market conditions.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

def download_recent_eurusd():
    """Download EURUSD data from 2020 to 2025."""

    print("=" * 70)
    print("DOWNLOADING RECENT EURUSD DATA (2020-2025)")
    print("=" * 70)

    # Download EURUSD from Yahoo Finance
    # Ticker: EURUSD=X
    # Note: Yahoo Finance limits 1h data to last 730 days
    print("\n📡 Downloading from Yahoo Finance...")
    print("   Ticker: EURUSD=X")
    print("   Period: Last 729 days (Yahoo limit for 1h data)")
    print("   Interval: 1 hour")

    try:
        # Download data
        ticker = yf.Ticker("EURUSD=X")

        # Get 1-hour data for the last 729 days (Yahoo's limit)
        df = ticker.history(period="729d", interval="1h")

        print(f"\n✅ Downloaded {len(df):,} candles")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")

        # Convert to standard format
        print("\n🔄 Converting to standard OHLCV format...")

        df_clean = pd.DataFrame({
            'timestamp': df.index,
            'open': df['Open'],
            'high': df['High'],
            'low': df['Low'],
            'close': df['Close'],
            'volume': df['Volume'].fillna(1000),  # Use actual volume or default
        })

        # Remove timezone info for consistency
        df_clean['timestamp'] = df_clean['timestamp'].dt.tz_localize(None)

        # Data quality checks
        print("\n📊 Data Quality Checks:")

        # Remove NaN
        initial_rows = len(df_clean)
        df_clean = df_clean.dropna(subset=['open', 'high', 'low', 'close'])
        removed_nan = initial_rows - len(df_clean)

        if removed_nan > 0:
            print(f"   ⚠️  Removed {removed_nan} rows with missing values")

        # Remove duplicates
        initial_rows = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=['timestamp'])
        removed_duplicates = initial_rows - len(df_clean)

        if removed_duplicates > 0:
            print(f"   ⚠️  Removed {removed_duplicates} duplicate timestamps")

        # Sort by timestamp
        df_clean = df_clean.sort_values('timestamp').reset_index(drop=True)

        # Validate OHLC relationships
        invalid_ohlc = (
            (df_clean['high'] < df_clean['low']) |
            (df_clean['high'] < df_clean['open']) |
            (df_clean['high'] < df_clean['close']) |
            (df_clean['low'] > df_clean['open']) |
            (df_clean['low'] > df_clean['close'])
        )

        if invalid_ohlc.sum() > 0:
            print(f"   ⚠️  Found {invalid_ohlc.sum()} rows with invalid OHLC relationships")
            df_clean = df_clean[~invalid_ohlc]
            print(f"   ✅ Removed invalid rows. Remaining: {len(df_clean):,}")
        else:
            print("   ✅ All OHLC relationships valid")

        # Check price range
        print(f"\n📈 Data Summary:")
        print(f"   Total candles: {len(df_clean):,}")
        print(f"   Date range: {df_clean['timestamp'].min()} to {df_clean['timestamp'].max()}")
        print(f"   Price range: {df_clean['close'].min():.5f} - {df_clean['close'].max():.5f}")
        print(f"   Latest price: {df_clean['close'].iloc[-1]:.5f}")

        # Check for gaps
        df_clean['time_diff'] = df_clean['timestamp'].diff()
        expected_diff = pd.Timedelta(hours=1)
        gaps = df_clean[df_clean['time_diff'] > expected_diff * 2]  # More than 2 hours

        if len(gaps) > 0:
            print(f"\n   ⚠️  Found {len(gaps)} gaps in hourly data (>2 hours)")
            print("   First 5 gaps:")
            for idx in gaps.index[:5]:
                print(f"      - {df_clean.loc[idx, 'timestamp']}: {df_clean.loc[idx, 'time_diff']}")
        else:
            print("   ✅ No significant gaps in hourly data")

        # Drop temporary column
        df_clean = df_clean.drop('time_diff', axis=1)

        # Save to file
        output_dir = Path("ohlcv/eurusd")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "eurusd_1h_recent.csv"
        df_clean.to_csv(output_file, index=False)

        print(f"\n💾 Saved to: {output_file}")
        print(f"   Final dataset: {len(df_clean):,} candles")
        print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")

        # Show sample
        print(f"\n📋 Data Sample:")
        print(df_clean.head(3).to_string())
        print("\n" + df_clean.tail(3).to_string())

        print("\n" + "=" * 70)
        print("✅ RECENT EURUSD DATA DOWNLOAD COMPLETE")
        print("=" * 70)

        print("\n🎯 Next Steps:")
        print("   1. Create forex_features.py with forex-specific features")
        print("   2. Train model with recent data")
        print("   3. Compare with baseline (old data model)")

        return df_clean

    except Exception as e:
        print(f"\n❌ Error downloading data: {e}")
        print("\n💡 Fallback: If yfinance fails, we can:")
        print("   1. Use MetaTrader 5 (if installed)")
        print("   2. Use existing older data and focus on features")
        print("   3. Download from alternative source (investing.com)")
        raise


if __name__ == '__main__':
    download_recent_eurusd()
