$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment with Python 3.11..."
py -3.11 -m venv .venv

Write-Host "Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Checking Python version..."
python --version

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing local package..."
pip install -e .

Write-Host "Installing research extras..."
pip install vectorbt backtesting yfinance ccxt

Write-Host "Running tests..."
pytest

Write-Host "Done."