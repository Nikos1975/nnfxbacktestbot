$ErrorActionPreference = "Stop"

. .\.venv\Scripts\Activate.ps1

$market = "spot"
$symbol = "BTCUSDT"
$start = "2018-01-01"
$end = "2025-01-01"

$intervals = @("1d", "4h", "1h")

foreach ($interval in $intervals) {
    $out = "data/raw/binance/$market/$symbol/$interval.csv"

    Write-Host "Downloading $market $symbol $interval from $start to $end -> $out"

    python -m trading_system.data.download_binance_klines `
      --market $market `
      --symbol $symbol `
      --interval $interval `
      --start $start `
      --end $end `
      --out $out

    Write-Host "Validating $out"

    python -m trading_system.data.validate_data `
      --data $out `
      --interval $interval
}