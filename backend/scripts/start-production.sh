#!/bin/bash
set -e

echo "🚀 Starting production backend..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
python3 -c "
import time
import psycopg2
from app.config import get_settings

settings = get_settings()
max_retries = 30
retry_delay = 2

for i in range(max_retries):
    try:
        # Extract connection params from DATABASE_URL
        import re
        match = re.match(r'postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', settings.database_url)
        if match:
            user, password, host, port, database = match.groups()
            conn = psycopg2.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database,
                connect_timeout=5
            )
            conn.close()
            print('✅ Database is ready!')
            break
    except Exception as e:
        if i == max_retries - 1:
            print(f'❌ Database connection failed after {max_retries} attempts')
            raise
        print(f'⏳ Database not ready (attempt {i+1}/{max_retries}), retrying in {retry_delay}s...')
        time.sleep(retry_delay)
"

# Run database migrations
echo "📦 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Start the application
echo "🎯 Starting Uvicorn server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips "*"
