# Stop any existing uvicorn process on port 8000
$process = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($process) {
    Write-Host "Stopping existing server (PID: $process)..."
    Stop-Process -Id $process -Force
    Start-Sleep -Seconds 2
}

# Start the server
Write-Host "Starting FastAPI server..."
Write-Host "Server will run at: http://localhost:8000"
Write-Host "Press Ctrl+C to stop"
Write-Host ""
python -m uvicorn main:app --host 0.0.0.0 --port 8000
