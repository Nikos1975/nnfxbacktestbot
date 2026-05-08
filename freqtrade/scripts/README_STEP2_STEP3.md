# NNFX Step 2 + Step 3 Scripts

Install these files into:

D:\_projects\trading\freqtrade\scripts\

Run all commands from:

D:\_projects\trading\freqtrade

## Step 2: Compare 1D / 4H / 1H regime summaries

After you have these files:

user_data\backtest_results\regime_performance_MAX_summary.csv
user_data\backtest_results\regime_performance_4h_MAX_summary.csv
user_data\backtest_results\regime_performance_1h_MAX_summary.csv

Run:

python .\scripts\compare_regime_timeframes.py `
  --inputs `
    .\user_data\backtest_results\regime_performance_MAX_summary.csv `
    .\user_data\backtest_results\regime_performance_4h_MAX_summary.csv `
    .\user_data\backtest_results\regime_performance_1h_MAX_summary.csv `
  --outdir .\user_data\backtest_results\step2_compare `
  --min-trades 30

Outputs:

step2_all_regime_results_with_flags.csv
step2_best_by_pair_timeframe_regime.csv
step2_survivors_min_trades.csv
step2_timeframe_comparison.csv
step2_regime_router_candidates.csv

## Step 3: Generate signal-exit-only strategy variants

This creates copies of the 7 NNFX strategies and changes:

minimal_roi = {"0": 100}

Run:

python .\scripts\generate_signal_exit_only_strategies.py `
  --strategies-dir .\user_data\strategies

Then verify:

docker compose run --rm freqtrade list-strategies

## Step 3 backtests

Run only after the signal-exit-only strategies appear in list-strategies.

4h:

.\scripts\backtest_all_nnfx_signal_exit_only_4h_max.ps1

Analyze recent 4h signal-exit-only results:

python .\scripts\analyze_regime_performance_intraday_v2.py `
  --exports .\user_data\backtest_results `
  --out .\user_data\backtest_results\regime_performance_4h_SIGNAL_EXIT_ONLY_summary.csv `
  --timeframe 4h `
  --start 2017-01-01 `
  --since-minutes 600

1h:

.\scripts\backtest_all_nnfx_signal_exit_only_1h_max.ps1

Analyze recent 1h signal-exit-only results:

python .\scripts\analyze_regime_performance_intraday_v2.py `
  --exports .\user_data\backtest_results `
  --out .\user_data\backtest_results\regime_performance_1h_SIGNAL_EXIT_ONLY_summary.csv `
  --timeframe 1h `
  --start 2017-01-01 `
  --since-minutes 600

1d:

.\scripts\backtest_all_nnfx_signal_exit_only_1d_max.ps1

Analyze 1d signal-exit-only results:

python .\scripts\analyze_regime_performance_intraday_v2.py `
  --exports .\user_data\backtest_results `
  --out .\user_data\backtest_results\regime_performance_1d_SIGNAL_EXIT_ONLY_summary.csv `
  --timeframe 1d `
  --start 2017-01-01 `
  --since-minutes 600
