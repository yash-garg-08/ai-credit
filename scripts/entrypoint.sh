#!/bin/sh
set -e

echo "==> Waiting for PostgreSQL..."
until python -c "
import sys, asyncio, asyncpg, os
url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
async def check():
    conn = await asyncpg.connect(url)
    await conn.close()
try:
    asyncio.run(check())
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    printf '.'
    sleep 2
done
echo ""
echo "==> PostgreSQL ready."

echo "==> Running migrations..."
alembic upgrade head

echo "==> Seeding pricing data..."
python -m scripts.seed

echo "==> Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
