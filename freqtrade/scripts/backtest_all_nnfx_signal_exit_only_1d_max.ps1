# Backtest all signal-exit-only NNFX prototype strategies on 1d.
# Run from: D:\_projects\trading\freqtrade

$strategies = @(
  "NnfxCoreJmaTdfiKijunVoxiChandelierSignalExitOnly",
  "NnfxAdaptiveOttHalftrendRsxKeltnerVolStopSignalExitOnly",
  "NnfxVolumeMcginleyAlphatrendStcChopWaeSignalExitOnly",
  "NnfxAlphaTrendRsxVoxiChandelierSignalExitOnly",
  "NnfxTdfiKijunChopChandelierSignalExitOnly",
  "NnfxMacZVwapOttVoxiVolStopSignalExitOnly",
  "NnfxPriceOnlySmiMfiKeltnerChandelierSignalExitOnly"
)

$pairs = @("BTC/USDT", "ETH/USDT", "SOL/USDT")
$timeframe = "1d"
$timerange = "20170101-"

foreach ($strategy in $strategies) {
  Write-Host ""
  Write-Host "============================================================"
  Write-Host "Backtesting $strategy on MAX 1d data, signal exits only"
  Write-Host "============================================================"

  docker compose run --rm freqtrade backtesting `
    --config user_data/config.json `
    --strategy $strategy `
    --pairs $pairs `
    --timeframe $timeframe `
    --timerange $timerange `
    --export trades
}
