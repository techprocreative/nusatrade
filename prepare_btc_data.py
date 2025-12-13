"""
Prepare BTC data to match XAUUSD format for ML training.

This script:
1. Loads BTC 1H data from Binance format
2. Converts to standard OHLCV format
3. Cleans and validates data
4. Saves as btcusd_1h_clean.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

def prepare_btc_data():
    """Prepare BTC data for ML training."""

    print("=" * 60)
    print("BTC DATA PREPARATION")
    print("=" * 60)

    # Load raw BTC data
    input_file = "ohlcv/btc/btc_1h_data_2018_to_2025.csv"
    output_file = "ohlcv/btc/btcusd_1h_clean.csv"

    print(f"\n📂 Loading data from: {input_file}")
    df = pd.read_csv(input_file)

    print(f"✅ Loaded {len(df)} rows")
    print(f"   Columns: {list(df.columns)}")
    print(f"\nRaw data sample:")
    print(df.head(3))

    # Convert to standard format (matching XAUUSD)
    print("\n🔄 Converting to standard OHLCV format...")

    # Rename columns to match XAUUSD format
    df_clean = pd.DataFrame({
        'timestamp': pd.to_datetime(df['Open time']),
        'open': df['Open'].astype(float),
        'high': df['High'].astype(float),
        'low': df['Low'].astype(float),
        'close': df['Close'].astype(float),
        'volume': df['Volume'].astype(float),
    })

    # Remove any rows with missing values
    initial_rows = len(df_clean)
    df_clean = df_clean.dropna()
    removed_rows = initial_rows - len(df_clean)

    if removed_rows > 0:
        print(f"⚠️  Removed {removed_rows} rows with missing values")

    # Remove duplicates
    initial_rows = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset=['timestamp'])
    removed_duplicates = initial_rows - len(df_clean)

    if removed_duplicates > 0:
        print(f"⚠️  Removed {removed_duplicates} duplicate timestamps")

    # Sort by timestamp
    df_clean = df_clean.sort_values('timestamp').reset_index(drop=True)

    # Data quality checks
    print("\n📊 Data Quality Checks:")
    print(f"   Total candles: {len(df_clean)}")
    print(f"   Date range: {df_clean['timestamp'].min()} to {df_clean['timestamp'].max()}")
    print(f"   Price range: ${df_clean['close'].min():,.2f} - ${df_clean['close'].max():,.2f}")
    print(f"   Average volume: {df_clean['volume'].mean():,.2f} BTC")

    # Check for gaps in data
    df_clean['time_diff'] = df_clean['timestamp'].diff()
    expected_diff = pd.Timedelta(hours=1)
    gaps = df_clean[df_clean['time_diff'] > expected_diff * 1.5]

    if len(gaps) > 0:
        print(f"\n⚠️  Found {len(gaps)} gaps in hourly data (>1.5 hours)")
        print("   First 5 gaps:")
        for idx in gaps.index[:5]:
            print(f"   - {df_clean.loc[idx, 'timestamp']}: {df_clean.loc[idx, 'time_diff']}")
    else:
        print("   ✅ No significant gaps in hourly data")

    # Drop the temporary column
    df_clean = df_clean.drop('time_diff', axis=1)

    # Validate OHLC relationship
    invalid_ohlc = (
        (df_clean['high'] < df_clean['low']) |
        (df_clean['high'] < df_clean['open']) |
        (df_clean['high'] < df_clean['close']) |
        (df_clean['low'] > df_clean['open']) |
        (df_clean['low'] > df_clean['close'])
    )

    if invalid_ohlc.sum() > 0:
        print(f"\n⚠️  Found {invalid_ohlc.sum()} rows with invalid OHLC relationships")
        df_clean = df_clean[~invalid_ohlc]
        print(f"   Removed invalid rows. Remaining: {len(df_clean)}")
    else:
        print("   ✅ All OHLC relationships valid")

    # Save cleaned data
    Path("ohlcv/btc").mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(output_file, index=False)

    print(f"\n💾 Saved cleaned data to: {output_file}")
    print(f"   Final dataset: {len(df_clean)} candles")

    # Show final sample
    print(f"\n📈 Final data sample:")
    print(df_clean.head(3))
    print("\n" + df_clean.tail(3).to_string())

    print("\n" + "=" * 60)
    print("✅ BTC DATA PREPARATION COMPLETE")
    print("=" * 60)

    return df_clean

if __name__ == '__main__':
    prepare_btc_data()
