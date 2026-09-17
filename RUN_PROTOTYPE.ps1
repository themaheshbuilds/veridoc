Write-Host ============================================================================== -ForegroundColor Green
Write-Host  VERIDOC: SOVEREIGN IDENTITY & FORENSIC PROTOTYPE  -ForegroundColor Green
Write-Host  Offline-First Multi-Modal Verification  -ForegroundColor Green
Write-Host ============================================================================== -ForegroundColor Green
Write-Host "

 = Get-Command python -ErrorAction SilentlyContinue
if (-not ) {
 Write-Host [ERROR] Python is not found in PATH. -ForegroundColor Red
 Write-Host Please install Python 3.10/3.11 or run START_OFFLINE_BROWSER.bat -ForegroundColor Yellow
 Pause
 Exit 1
}

Write-Host [1/3] Python environment verified: Python 3.11.9 -ForegroundColor Cyan
Write-Host [2/3] Launching VERIDOC Sovereign Engine on http://127.0.0.1:8000 ... -ForegroundColor Cyan
Write-Host 

Start-Process http://127.0.0.1:8000/
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
