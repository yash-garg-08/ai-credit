#!/bin/sh
set -e

echo "==> Waiting for Temporal to be available..."
until python -c "
import sys, asyncio, os
from temporalio.client import Client
async def check():
    await Client.connect(os.environ.get('TEMPORAL_HOST', 'localhost:7233'))
try:
    asyncio.run(check())
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    printf '.'
    sleep 3
done
echo ""
echo "==> Temporal ready."

echo "==> Starting Temporal worker..."
exec python -m app.workflows.worker
