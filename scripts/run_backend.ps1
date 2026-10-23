# Start Task Reviewer AI FastAPI Backend (Local Dev)
Write-Host ">>> Starting Task Reviewer AI Backend..." -ForegroundColor Cyan

if (-Not (Test-Path ".venv")) {
    Write-Host "Virtual environment not detected. Creating .venv..." -ForegroundColor Yellow
    uv venv .venv
}

.venv\Scripts\Activate.ps1

Write-Host ">>> Applying database migrations..." -ForegroundColor Cyan
alembic upgrade head

Write-Host ">>> Seeding initial accounts & sample task..." -ForegroundColor Cyan
python backend/seed_data.py

Write-Host ">>> Launching Uvicorn on http://127.0.0.1:8000..." -ForegroundColor Green
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
