#!/bin/bash
# Azure Web App startup script — runs both Python backend and Node.js server

echo "=== Installing Python dependencies ==="
cd /home/site/wwwroot/Chat\ Bot/backend
pip install -r requirements.txt --quiet 2>&1

echo "=== Starting chatbot backend ==="
cd /home/site/wwwroot/Chat\ Bot/backend
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Wait for backend to index CV and be ready
sleep 8

echo "=== Starting portfolio server ==="
cd /home/site/wwwroot
PORT=$PORT node server.js
