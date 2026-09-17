@echo off
title VERIDOC Sovereign Prototype Launcher
color 0A
cls
echo ==============================================================================
echo                VERIDOC: SOVEREIGN IDENTITY & FORENSIC PROTOTYPE
echo                  Offline-First Multi-Modal Document Verification
echo ==============================================================================
echo.
echo [1/3] Checking Python 3 environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10 or 3.11 from python.org to run the backend engine.
    echo Alternatively, you can launch START_OFFLINE_BROWSER.bat for client-side demo.
    echo.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
python -c import fastapi, uvicorn >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing required libraries from backend\requirements.txt...
    python -m pip install -r backend\requirements.txt
)

echo [3/3] Launching VERIDOC Sovereign Server on http://127.0.0.1:8000 ...
echo.
echo ==============================================================================
echo  Web UI:         http://127.0.0.1:8000/
echo  Verify Station: http://127.0.0.1:8000/verifydocuments
echo  Audit Ledger:   http://127.0.0.1:8000/verified-documents
echo  API Sandbox:    http://127.0.0.1:8000/api-access
echo  Swagger Docs:   http://127.0.0.1:8000/docs
echo ==============================================================================
echo.
echo Launching your default web browser...
timeout /t 2 /nobreak >nul
start " http://127.0.0.1:8000/

python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
pause
