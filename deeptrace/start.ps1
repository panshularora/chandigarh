# DeepTrace local station — starts API then Vite
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$root\backend`"; python -m uvicorn app.main:app --reload --port 8000"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$root\frontend`"; npm run dev"
Write-Host "Backend  http://127.0.0.1:8000/api/docs"
Write-Host "Console  http://localhost:5173"
Write-Host "Login    inspector / chandigarh2026"
