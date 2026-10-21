# ==============================================================================
# DataPulse AI - Windows PowerShell Service & Pipeline Launcher
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DataPulse AI - Platform Service Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Select an option to launch:"
Write-Host "  [1] Seed Database & Train ML Models (5,000 Transactions)" -ForegroundColor Green
Write-Host "  [2] Start FastAPI Backend Server (http://127.0.0.1:8000/docs)" -ForegroundColor Yellow
Write-Host "  [3] Start Streamlit Interactive Dashboard (http://localhost:8501)" -ForegroundColor Magenta
Write-Host "  [4] Run Full Pytest Test Suite" -ForegroundColor Blue
Write-Host "  [5] Start Full Docker Compose Stack (PostgreSQL, Airflow, API, Dashboard)" -ForegroundColor DarkCyan
Write-Host "  [6] Run Ingestion Pipeline (CSV / Simulated REST API)" -ForegroundColor White
Write-Host "  [0] Exit" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "Enter your choice (0-6)"

switch ($choice) {
    "1" {
        Write-Host "--> Running seed data workflow..." -ForegroundColor Green
        .\.venv\Scripts\python.exe scripts/seed_data.py
    }
    "2" {
        Write-Host "--> Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
        Write-Host "--> Interactive Swagger API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
        .\.venv\Scripts\python.exe -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000 --reload
    }
    "3" {
        Write-Host "--> Launching Streamlit Dashboard on http://localhost:8501..." -ForegroundColor Magenta
        .\.venv\Scripts\python.exe -m streamlit run dashboard/Home.py --server.port 8501
    }
    "4" {
        Write-Host "--> Running test suite with Pytest..." -ForegroundColor Blue
        .\.venv\Scripts\python.exe -m pytest -v
    }
    "5" {
        Write-Host "--> Starting Docker Compose stack..." -ForegroundColor DarkCyan
        docker compose up -d
        Write-Host "Containers started! URLs:" -ForegroundColor Green
        Write-Host "  FastAPI Swagger Docs: http://localhost:8000/docs"
        Write-Host "  Streamlit Dashboard:  http://localhost:8501"
        Write-Host "  Airflow Webserver:    http://localhost:8080 (admin / admin)"
    }
    "6" {
        Write-Host "--> Running data ingestion pipeline..." -ForegroundColor White
        .\.venv\Scripts\python.exe scripts/run_pipeline.py --source simulated_api --records 1000
    }
    default {
        Write-Host "Exiting. Have a great day!" -ForegroundColor Gray
    }
}
