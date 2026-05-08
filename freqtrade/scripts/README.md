# NNFX MAX Data Regime Test Scripts

These scripts test all NNFX prototype strategies on maximum practical Binance spot Daily data.

Run from:

D:\_projects\trading\freqtrade

## 1. Download max Daily data

.\scripts\download_daily_max_data.ps1

Uses:

--timerange 20170101-

This is practical max for Binance spot. Individual coins start later depending on listing date.

## 2. Backtest all strategies

.\scripts\backtest_all_nnfx_1d_max.ps1

Exports trade JSON files to:

user_data\backtest_results\

## 3. Analyze regime performance

python .\scripts\analyze_regime_performance_max.py `
  --exports .\user_data\backtest_results `
  --out .\user_data\backtest_results\regime_performance_MAX_summary.csv `
  --start 2017-01-01

## Regime classification

- UPTREND:
  close > EMA200, EMA200 slope > 0, ADX >= 20, CHOP < 55

- DOWNTREND:
  close < EMA200, EMA200 slope < 0, ADX >= 20, CHOP < 55

- CONSOLIDATING:
  ADX < 20 or CHOP >= 55

- TRANSITION:
  everything else

## Outputs

- regime_performance_MAX_summary.csv
- regime_performance_MAX_summary_trades.csv

Use this only as a first-pass architecture test. The strategies include proxy indicators.
