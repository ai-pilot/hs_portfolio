#!/bin/bash
# Azure Web App startup script — runs both Python backend and Node.js server
set -e

export PIP_CACHE_DIR=/home/pip-cache
mkdir -p $PIP_CACHE_DIR

echo "=== Python version ==="
python3 --version

echo "=== Bootstrapping pip ==="
if ! python3 -m pip --version > /dev/null 2>&1; then
    echo "pip not found — installing via apt-get..."
    apt-get update -qq && apt-get install -y -qq python3-pip
fi

echo "=== pip version ==="
python3 -m pip --version

echo "=== Installing Python dependencies (cached in $PIP_CACHE_DIR) ==="
cd /home/site/wwwroot/Chat\ Bot/backend
python3 -m pip install -r requirements.txt --quiet --prefer-binary 2>&1

echo "=== Starting chatbot backend ==="
cd /home/site/wwwroot/Chat\ Bot/backend
PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /home/LogFiles/chatbot.log 2>&1 &

# Wait for backend to index CV and be ready
sleep 15

echo "=== Starting portfolio server ==="
cd /home/site/wwwroot
PORT=$PORT node server.js
