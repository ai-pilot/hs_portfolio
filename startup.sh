#!/bin/bash
# Azure Web App startup script — runs both Python backend and Node.js server
set -e

VENV_DIR=/home/site/venv
REQ_FILE=/home/site/wwwroot/Chat\ Bot/backend/requirements.txt

echo "=== Python version ==="
python3 --version

echo "=== Bootstrapping pip ==="
if ! python3 -m pip --version > /dev/null 2>&1; then
    echo "pip not found — installing via apt-get..."
    apt-get update -qq && apt-get install -y -qq python3-pip python3-venv
fi

echo "=== Setting up virtualenv at $VENV_DIR ==="
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating new venv (first boot — this only happens once)..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

echo "=== Installing/updating Python dependencies ==="
pip install --upgrade pip --quiet
pip install -r "$REQ_FILE" --quiet --prefer-binary

echo "=== Starting chatbot backend ==="
cd /home/site/wwwroot/Chat\ Bot/backend
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /home/LogFiles/chatbot.log 2>&1 &

# Wait for backend to index CV and be ready
sleep 15

echo "=== Starting portfolio server ==="
cd /home/site/wwwroot
PORT=$PORT node server.js
