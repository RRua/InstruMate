#!/bin/bash
set -e

echo "=== InstruMate Web Service ==="
echo "Creating required directories..."
mkdir -p /data/output /data/tmp /data/uploads

echo "Java version:"
java -version 2>&1 | head -1

echo "Python version:"
python3 --version

echo "Starting InstruMate API on port 8000..."
exec uvicorn api.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WORKERS:-2}" \
    --log-level "${LOG_LEVEL:-info}"
