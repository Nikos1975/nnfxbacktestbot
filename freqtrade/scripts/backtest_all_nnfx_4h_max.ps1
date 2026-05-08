# Backtest all NNFX prototype strategies on maximum practical 4h data.
# Run from: D:\_projects\trading\freqtrade

$strategies = @(
  "NnfxCoreJmaTdfiKijunVoxiChandelier",
  "NnfxAdaptiveOttHalftrendRsxKeltnerVolStop",
  "NnfxVolumeMcginleyAlphatrendStcChopWae",
  "NnfxAlphaTrendRsxVoxiChandelier",
  "NnfxTdfiKijunChopChandelier",
  "NnfxMacZVwapOttVoxiVolStop",
  "NnfxPriceOnlySmiMfiKeltnerChandelier"
)

$pairs = @("BTC/USDT", "ETH/USDT", "SOL/USDT")
$timeframe = "4h"
$timerange = "20170101-"

foreach ($strategy in $strategies) {
  $filename = "user_data/backtest_results/$strategy-4h-MAX.json"

  Write-Host ""
  Write-Host "============================================================"
  Write-Host "Backtesting $strategy on MAX 4h data"
  Write-Host "Export: $filename"
  Write-Host "============================================================"

  docker compose run --rm freqtrade backtesting `
    --config user_data/config.json `
    --strategy $strategy `
    --pairs $pairs `
    --timeframe $timeframe `
    --timerange $timerange `
    --export trades `
    --export-filename $filename
}
