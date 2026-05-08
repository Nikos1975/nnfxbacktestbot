$ErrorActionPreference = "Stop"
. .\.venv\Scripts\Activate.ps1

grid-backtest `
  --data data/raw/BTCUSDT_1h.csv `
  --config configs/grid/btc_usdt_grid_1h.yaml `
  --out reports/backtests
