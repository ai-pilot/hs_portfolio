#!/bin/bash
# Azure Web App startup script
# Strategy: bind PORT immediately via Node, install Python deps + start backend in background

VENV_DIR="/home/site/venv"
BACKEND_DIR="/home/site/wwwroot/Chat Bot/backend"
LOG_FILE="/home/LogFiles/chatbot-bootstrap.log"

# Background bootstrap — installs deps + starts uvicorn
bootstrap_backend() {
    {
        echo "=== [bg] Backend bootstrap started at $(date) ==="

        # Bootstrap pip + venv tools
        if ! python3 -m pip --version > /dev/null 2>&1; then
            echo "[bg] Installing python3-pip + python3-venv via apt-get..."
            apt-get update -qq && apt-get install -y -qq python3-pip python3-venv
        fi

        # Create venv if missing
        if [ ! -d "$VENV_DIR" ]; then
            echo "[bg] Creating venv (first-boot only)..."
            python3 -m venv "$VENV_DIR"
        fi

        source "$VENV_DIR/bin/activate"

        echo "[bg] Installing Python dependencies (verbose)..."
        pip install --upgrade pip
        pip install -r "$BACKEND_DIR/requirements.txt" --prefer-binary

        echo "=== [bg] Starting uvicorn at $(date) ==="
        cd "$BACKEND_DIR"
        PYTHONPATH=. exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    } >> "$LOG_FILE" 2>&1
}

echo ">>> startup.sh: launching backend bootstrap in background"
bootstrap_backend &

echo ">>> startup.sh: starting Node portfolio server (binding PORT=$PORT)"
cd /home/site/wwwroot
exec node server.js
