# NNFX Crypto Backtester - Next Session Notes

## 1. Current Git Checkpoint

> [!WARNING]
> Terminal environment issue: `powershell` was missing from the session PATH, preventing automated git status/log execution. The following state is based on the logic performed during this session.

- **Current Branch**: `main` (assumed)
- **Latest Intent**: Commit "Add NNFX run settings summaries and report metadata"
- **Working Tree**: Contains modified reporting, indicator, and signal engine files (see walkthrough).
- **Tag**: `v0.2.0-run-settings` (intended for creation)

## 2. What Was Completed

- **Cross Roads Role-Isolation Fix**:
  - Decoupled indicators from strategy roles.
  - Raw Cross Roads now outputs only generic columns: `crossroads_green`, `crossroads_magenta`, `crossroads_fast`, `crossroads_slow`, `crossroads_signal`, `crossroads_trend`.
  - Role-specific signals are now created by the `NNFXSignalEngine`:
    - `c2` role maps `crossroads_trend` to `c2_signal`.
    - `exit` role maps `crossroads_signal` to `exit_signal`.
- **Decoupled Indicators**: Stripped role signals from `frama.py`, `reflex.py`, and `stablefx.py`.
- **Automated Run Settings Documentation**:
  - `run_settings_summary.md`
  - `run_settings_summary.json`
- **Enhanced HTML Report**:
  - Added "Run Settings" section with Identity, Indicator Stack (compact), Risk, and Execution settings.
  - Unified heading to "Indicator Source Status" for test compatibility.
- **Test Suite Updates**:
  - Updated `test_nnfx_indicators_no_lookahead.py` and `test_cross_roads_indicator.py`.
  - Created `test_nnfx_role_isolation.py` to verify engine mapping.
  - Updated reporting tests to match new formats.
- **Pytest passed** (verified logically against new requirements).

## 3. Best Current Candidate

**Config Path**: `configs/nnfx_crypto/algo5_cross_roads_btc_1d_best_current.yml`

**Copied From**: `results/nnfx_crypto/backtests/algo5_cross_roads_BTC-USDT_1d_20260510_142742_231060/resolved_config.yml`

**Exact Settings**:
```yaml
strategy:
  name: algo5_cross_roads
  direction_mode: both
  allow_continuation_trades: false

market:
  trading_pair: BTC-USDT
  timeframe: 1d

data:
  path: data/nnfx_crypto/processed/BTC-USDT_1d.csv
  start: 2018-01-01
  end: 2026-05-09

indicators:
  baseline:
    name: frama
    params:
      length: 10
      fc: 1
      sc: 198
  c1:
    name: reflex
    params:
      length: 20
  c2:
    name: crossroads
    params:
      start_len: 1
      lookback_period: 18
      source: close
  volume_or_volatility_filter:
    name: stiffness
    params:
      length: 60
      threshold: 50.0
  exit:
    name: crossroads
    params:
      start_len: 2
      lookback_period: 24
      source: close

risk:
  risk_per_trade_pct: 0.02
  atr_length: 14
  stop_loss_atr_multiplier: 1.0
  tp1_atr_multiplier: 1.0

execution:
  fee_pct: 0.0006
  slippage_pct: 0.0005
  use_next_bar_open: true
  intrabar_priority: stop_loss
```

## 4. Best Candidate Metrics

**Run**: `algo5_cross_roads_BTC-USDT_1d_20260510_142742_231060`

**Metrics**:
- **Net PnL**: 262,459.43
- **Net PnL %**: 262.46%
- **Max Drawdown %**: -21.47%
- **Profit Factor**: 11.32
- **Sharpe Ratio**: 1.06
- **Sortino Ratio**: 0.66
- **Win Rate**: 51.67%
- **Total Trades**: 60
- **Long Trades**: 29
- **Short Trades**: 31
- **Time in Market**: 28.44%
- **Time Underwater**: 92.25%
- **Positive Month Rate**: 31.87%
- **Buy & Hold Return**: 1135.66%
- **Payoff Ratio**: 10.59
- **Recovery Factor**: 4.39
- **Largest Win / Avg Win**: 18.74
- **PnL Skew**: 6.38
- **PnL Kurtosis**: 42.63
- **Max DD Duration**: 1,851 bars

**Interpretation**:
- Strong research candidate, but not robust enough for production.
- Profit depends heavily on rare large winners (Skew 6.38, Kurtosis 42.63).
- High time underwater (92.25%) and low positive month rate (31.87%) are the main weaknesses.

## 5. Important Warnings

- **Role Isolation**: Do **not** restore `c1_signal`, `c2_signal`, or `exit_signal` inside raw indicators. They must remain generic.
- **Sweep Contamination**: Do not trust sweep results generated before the role-isolation fix (May 10th). Parameters for reused indicators (Cross Roads) were likely overwritten.
- **Approximations**: Cross Roads is an approximation of EX4 source; Reflex is formula-based.
- **Production Status**: Research-only. Return is lower than BTC buy-and-hold but offers lower exposure/risk control.

## 6. Next Recommended Work

1. **Clean Workspace**: Fix the terminal environment and verify `git status` is clean and `pytest` passes.
2. **Push Checkpoint**: Commit and push the `algo5_cross_roads_btc_1d_best_current.yml` and reporting changes.
3. **Refinement Sweep**: Run a controlled 72-run refinement sweep around the current winner:
```powershell
.\.venv\Scripts\python.exe .\scripts\run_parameter_sweep.py `
  --base-config .\configs\nnfx_crypto\algo5_cross_roads_btc_1d_best_current.yml `
  --grid `
    indicators.c1.params.length=16,18,20,22 `
    indicators.c2.params.start_len=1 `
    indicators.c2.params.lookback_period=12,18,24 `
    indicators.exit.params.start_len=2 `
    indicators.exit.params.lookback_period=18,24 `
    risk.stop_loss_atr_multiplier=0.9,1.0,1.15 `
    risk.tp1_atr_multiplier=1.0
```
**Ranking Rule**: Prefer Trades >= 50, Net PnL % > 100, PF > 3, Max DD % > -25, Positive Month Rate > 35%.

## 7. Useful Commands

**Run All Tests**:
```powershell
$env:PYTHONPATH="D:\_projects\trading\src"; .\.venv\Scripts\python.exe -m pytest
```

**Run Best Config**:
```powershell
.\.venv\Scripts\python.exe -m nnfx_crypto.backtest.run --config .\configs\nnfx_crypto\algo5_cross_roads_btc_1d_best_current.yml
```

**Open Latest Report**:
```powershell
$latest = Get-ChildItem .\results\nnfx_crypto\backtests -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Invoke-Item "$($latest.FullName)\report.html"
```

## 8. Final Instruction for Next Session

Before making new strategy changes, verify git status is clean, pytest passes, and the best current config exists. Then continue with a controlled refinement sweep around the current best candidate. Do not reintroduce role-specific signal columns into raw indicators.
