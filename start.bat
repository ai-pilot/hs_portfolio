@echo off
echo Starting Orient Express Portfolio...
echo.

:: Start Python chatbot backend
echo [1/2] Starting chatbot backend (port 8000)...
cd /d "%~dp0Chat Bot\backend"
start /b cmd /c "set PYTHONPATH=. && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1"

:: Wait for backend to be ready
timeout /t 6 /nobreak >nul

:: Start Node.js portfolio server
echo [2/2] Starting portfolio server (port 8080)...
cd /d "%~dp0"
node server.js
