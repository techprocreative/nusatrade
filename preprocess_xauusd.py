"""
XAUUSD Data Preprocessing for ML Training
Converts raw CSV to clean, ML-ready format

This script prepares your 21-year XAUUSD dataset for machine learning model training.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime


def preprocess_xauusd(input_file, output_file, timeframe='1h'):
    """
    Preprocess XAUUSD data for ML training.

    Args:
        input_file: Path to raw CSV (e.g., 'XAU_1h_data.csv')
        output_file: Path to save clean CSV
        timeframe: Timeframe string for logging

    Returns:
        pd.DataFrame: Cleaned data
    """
    print(f"\n{'='*60}")
    print(f"Processing {timeframe} XAUUSD data...")
    print(f"{'='*60}")

    # 1. Read CSV with correct separator
    print(f"\n[1/10] Reading file: {input_file}")
    try:
        df = pd.read_csv(input_file, sep=';')
        print(f"  ✅ Loaded {len(df):,} rows")
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        sys.exit(1)

    # 2. Clean column names
    print(f"\n[2/10] Cleaning column names...")
    df.columns = df.columns.str.strip()
    print(f"  ✅ Columns: {df.columns.tolist()}")

    # 3. Parse dates
    print(f"\n[3/10] Parsing dates...")
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='%Y.%m.%d %H:%M')
        print(f"  ✅ Date range: {df['Date'].min()} to {df['Date'].max()}")
    except Exception as e:
        print(f"  ❌ Error parsing dates: {e}")
        sys.exit(1)

    # 4. Sort by date
    print(f"\n[4/10] Sorting by date...")
    df = df.sort_values('Date').reset_index(drop=True)
    print(f"  ✅ Sorted chronologically")

    # 5. Rename for consistency
    print(f"\n[5/10] Renaming columns for consistency...")
    df = df.rename(columns={
        'Date': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })
    print(f"  ✅ Standardized column names")

    # 6. Data quality checks
    print(f"\n[6/10] Running data quality checks...")
    print(f"  Total rows: {len(df):,}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Years of data: {(df['timestamp'].max() - df['timestamp'].min()).days / 365.25:.1f}")

    missing_values = df.isnull().sum().sum()
    print(f"  Missing values: {missing_values}")

    # 7. Remove rows with invalid data
    print(f"\n[7/10] Removing invalid data...")
    initial_count = len(df)

    # High must be >= Low
    df = df[df['high'] >= df['low']]
    # High must be >= Open
    df = df[df['high'] >= df['open']]
    # High must be >= Close
    df = df[df['high'] >= df['close']]
    # Low must be <= Open
    df = df[df['low'] <= df['open']]
    # Low must be <= Close
    df = df[df['low'] <= df['close']]

    removed_count = initial_count - len(df)
    print(f"  ✅ Removed {removed_count:,} invalid rows ({removed_count/initial_count*100:.2f}%)")

    # 8. Remove duplicates
    print(f"\n[8/10] Removing duplicates...")
    initial_count = len(df)
    df = df.drop_duplicates(subset=['timestamp'], keep='first')
    duplicates_removed = initial_count - len(df)
    print(f"  ✅ Removed {duplicates_removed:,} duplicates")

    # 9. Forward fill missing values
    print(f"\n[9/10] Filling missing values...")
    if df.isnull().sum().sum() > 0:
        df = df.fillna(method='ffill')
        print(f"  ✅ Forward-filled missing values")
    else:
        print(f"  ✅ No missing values to fill")

    # 10. Save clean data
    print(f"\n[10/10] Saving clean data...")
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        file_size = output_path.stat().st_size / 1024 / 1024
        print(f"  ✅ Saved to: {output_file}")
        print(f"  ✅ Rows: {len(df):,}")
        print(f"  ✅ Size: {file_size:.1f} MB")
    except Exception as e:
        print(f"  ❌ Error saving file: {e}")
        sys.exit(1)

    # Final statistics
    print(f"\n{'='*60}")
    print(f"PREPROCESSING COMPLETE ✅")
    print(f"{'='*60}")
    print(f"\nData Summary:")
    print(f"  • Timeframe: {timeframe}")
    print(f"  • Total rows: {len(df):,}")
    print(f"  • Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  • Years: {(df['timestamp'].max() - df['timestamp'].min()).days / 365.25:.1f}")
    print(f"  • Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"  • Average volume: {df['volume'].mean():.0f}")
    print(f"\nOutput file ready for ML training: {output_file}")

    return df


def main():
    """Main preprocessing pipeline."""
    print(f"\n{'#'*60}")
    print(f"# XAUUSD Data Preprocessing for ML Training")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    # Process 1H data (RECOMMENDED for ML training)
    print("\n🎯 Processing 1H timeframe (RECOMMENDED for swing trading)")
    df_1h = preprocess_xauusd(
        input_file='ohlcv/xauusd/XAU_1h_data.csv',
        output_file='ohlcv/xauusd/xauusd_1h_clean.csv',
        timeframe='1h'
    )

    # Optionally process other timeframes
    print("\n" + "="*60)
    print("Additional timeframes (optional):")
    print("="*60)

    # Process 4H data (for position trading)
    print("\n📊 Processing 4H timeframe (for position trading)")
    df_4h = preprocess_xauusd(
        input_file='ohlcv/xauusd/XAU_4h_data.csv',
        output_file='ohlcv/xauusd/xauusd_4h_clean.csv',
        timeframe='4h'
    )

    # Process 15M data (for day trading)
    print("\n⚡ Processing 15M timeframe (for day trading)")
    df_15m = preprocess_xauusd(
        input_file='ohlcv/xauusd/XAU_15m_data.csv',
        output_file='ohlcv/xauusd/xauusd_15m_clean.csv',
        timeframe='15m'
    )

    # Final summary
    print(f"\n{'#'*60}")
    print(f"# ALL PREPROCESSING COMPLETE ✅")
    print(f"# Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")
    print(f"\n📁 Clean data files created:")
    print(f"  1. ohlcv/xauusd/xauusd_1h_clean.csv  ({len(df_1h):,} rows) ⭐ RECOMMENDED")
    print(f"  2. ohlcv/xauusd/xauusd_4h_clean.csv  ({len(df_4h):,} rows)")
    print(f"  3. ohlcv/xauusd/xauusd_15m_clean.csv ({len(df_15m):,} rows)")

    print(f"\n🚀 NEXT STEPS:")
    print(f"\n1. Train your first ML model:")
    print(f"   cd backend")
    print(f"   python3 -c \"\"\"")
    print(f"from app.ml.training import Trainer")
    print(f"import pandas as pd")
    print(f"")
    print(f"# Load clean data")
    print(f"df = pd.read_csv('../ohlcv/xauusd/xauusd_1h_clean.csv')")
    print(f"")
    print(f"# Train model")
    print(f"trainer = Trainer()")
    print(f"result = trainer.train(data=df, model_type='random_forest')")
    print(f"")
    print(f"# Check results")
    print(f"print('\\\\nTraining Results:')")
    print(f"print(f\\\"Accuracy: {{result['metrics']['accuracy']:.1%}}\\\") ")
    print(f"print(f\\\"Train samples: {{result['metrics']['train_samples']:,}}\\\") ")
    print(f"print(f\\\"Test samples: {{result['metrics']['test_samples']:,}}\\\") ")
    print(f"print(f\\\"Model saved: {{result['model_path']}}\\\") ")
    print(f"\"\"\"")
    print(f"\n2. Monitor performance with MLPerformanceTracker")
    print(f"   (See ML_PRODUCTION_READINESS.md for details)")
    print(f"\n3. Test on demo account for 30 days")
    print(f"4. Gradually scale to real account")
    print(f"\n{'#'*60}\n")


if __name__ == '__main__':
    main()
