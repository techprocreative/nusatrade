#!/usr/bin/env python3
"""
Download ML model files from Cloudflare R2 storage.

This script downloads profitable XGBoost models from R2 to local models/ directory.
Run on startup to ensure models are available for predictions.
"""
import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# R2 configuration from environment variables
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "forex-ai-storage")

# Models to download
MODELS = [
    {
        "key": "models/model_xgboost_20251212_235414.pkl",
        "local_path": "models/model_xgboost_20251212_235414.pkl",
        "symbol": "XAUUSD"
    },
    {
        "key": "models/eurusd/forex-optimized/model_forex_xgboost_20251213_112218.pkl",
        "local_path": "models/eurusd/forex-optimized/model_forex_xgboost_20251213_112218.pkl",
        "symbol": "EURUSD"
    },
    {
        "key": "models/btcusd/crypto-optimized/model_crypto_xgboost_20251213_104319.pkl",
        "local_path": "models/btcusd/crypto-optimized/model_crypto_xgboost_20251213_104319.pkl",
        "symbol": "BTCUSD"
    },
]


def get_r2_client():
    """Create S3-compatible client for Cloudflare R2."""
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
        print("⚠️  WARNING: R2 credentials not configured. Skipping model download.")
        print("   Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY environment variables.")
        return None

    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto"  # R2 uses 'auto' region
    )


def download_model(s3_client, model_info: dict) -> bool:
    """Download a single model file from R2."""
    key = model_info["key"]
    local_path = Path(model_info["local_path"])
    symbol = model_info["symbol"]

    # Check if file already exists and skip if it does
    if local_path.exists():
        file_size = local_path.stat().st_size / (1024 * 1024)  # MB
        print(f"  ✓ {symbol}: Already exists ({file_size:.1f}MB) - skipping")
        return True

    # Create parent directory if needed
    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        print(f"  ⏳ {symbol}: Downloading from R2...", end="", flush=True)

        # Download file
        s3_client.download_file(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Filename=str(local_path)
        )

        file_size = local_path.stat().st_size / (1024 * 1024)  # MB
        print(f" ✓ ({file_size:.1f}MB)")
        return True

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            print(f" ✗ Not found in R2")
            print(f"     Make sure '{key}' exists in bucket '{R2_BUCKET_NAME}'")
        else:
            print(f" ✗ Error: {e}")
        return False

    except Exception as e:
        print(f" ✗ Error: {e}")
        return False


def main():
    """Download all required models from R2."""
    print("\n🔽 Downloading ML models from Cloudflare R2...")

    # Get R2 client
    s3_client = get_r2_client()
    if not s3_client:
        print("\n⚠️  Skipping model download (R2 not configured)")
        print("   Application will use local models if available.\n")
        return 0

    # Download each model
    success_count = 0
    failed_models = []

    for model in MODELS:
        if download_model(s3_client, model):
            success_count += 1
        else:
            failed_models.append(model["symbol"])

    # Print summary
    print(f"\n📊 Download Summary:")
    print(f"   ✓ Success: {success_count}/{len(MODELS)} models")

    if failed_models:
        print(f"   ✗ Failed: {', '.join(failed_models)}")
        print(f"\n⚠️  WARNING: Some models failed to download.")
        print(f"   Auto-trading may not work for these symbols.")
        print(f"   Upload models to R2 bucket: {R2_BUCKET_NAME}\n")
        return 1  # Non-zero exit code but don't fail startup

    print(f"   ✅ All models ready!\n")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Download cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
