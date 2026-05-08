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
$outdir = "user_data/backtest_results_signal_4h"

New-Item -ItemType Directory -Force $outdir

foreach ($strategy in $strategies) {
  Write-Host ""
  Write-Host "============================================================"
  Write-Host "Backtesting $strategy on 4h signal-exit-only"
  Write-Host "============================================================"

  docker compose run --rm freqtrade backtesting `
    --config user_data/config.json `
    --strategy $strategy `
    --pairs $pairs `
    --timeframe 4h `
    --timerange 20170101- `
    --export trades `
    --backtest-directory $outdir
}
