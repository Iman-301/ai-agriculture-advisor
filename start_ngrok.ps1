# Start ngrok with browser warning disabled
Write-Host "Starting ngrok tunnel..."
Write-Host "This will create a public URL for your local server on port 8000"
Write-Host ""

# Stop existing ngrok if running
$ngrokProcess = Get-Process ngrok -ErrorAction SilentlyContinue
if ($ngrokProcess) {
    Write-Host "Stopping existing ngrok..."
    Stop-Process -Name ngrok -Force
    Start-Sleep -Seconds 2
}

# Start ngrok without browser warning
Write-Host "Starting ngrok (without browser warning)..."
Write-Host ""
ngrok http 8000 --log=stdout
