$ErrorActionPreference = "Stop"

. .\.venv\Scripts\Activate.ps1

$jobs = @(
    @{
        Data = "data/raw/binance/spot/BTCUSDT/1d.csv"
        Config = "configs/grid/btc_usdt_grid_1d.yaml"
    },
    @{
        Data = "data/raw/binance/spot/BTCUSDT/4h.csv"
        Config = "configs/grid/btc_usdt_grid_4h.yaml"
    },
    @{
        Data = "data/raw/binance/spot/BTCUSDT/1h.csv"
        Config = "configs/grid/btc_usdt_grid_1h.yaml"
    }
)

foreach ($job in $jobs) {
    Write-Host "Running backtest:"
    Write-Host "  Data:   $($job.Data)"
    Write-Host "  Config: $($job.Config)"

    grid-backtest `
      --data $job.Data `
      --config $job.Config `
      --out reports/backtests

    Write-Host ""
}