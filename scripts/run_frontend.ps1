# Start Task Reviewer AI React + Vite Frontend (Local Dev)
Write-Host ">>> Starting Task Reviewer AI Frontend (React + Vite)..." -ForegroundColor Cyan
Set-Location frontend

if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host ">>> Launching Vite dev server on http://localhost:5173..." -ForegroundColor Green
npm run dev
