# ================================
# DSU IQC Backend Starter Script
# ================================

Write-Host "🚀 Starting Flask Backend for IQC Portal..." -ForegroundColor Cyan

# Activate virtual environment
$venvPath = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "✅ Activating virtual environment..." -ForegroundColor Yellow
    & $venvPath
} else {
    Write-Host "⚠️  Virtual environment not found. Please create it first." -ForegroundColor Red
    exit
}

# Set environment variables
$env:FLASK_APP = "main.py"
$env:FLASK_ENV = "development"

# Run Flask on port 5000
Write-Host "💻 Running Flask on http://localhost:5000 ..." -ForegroundColor Green
flask run --port=5000

Pause
