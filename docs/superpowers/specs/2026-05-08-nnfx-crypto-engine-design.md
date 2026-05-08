# NNFX Crypto Research Engine Design

Date: 2026-05-08

## Decision

Build a separate portable package at `src/nnfx_crypto/`. Do not integrate the NNFX engine into the existing `src/trading_system/` package.

Runtime artifacts will be namespaced to avoid mixing with existing grid, Freqtrade, and OctoBot work:

- `configs/nnfx_crypto/`
- `data/nnfx_crypto/`
- `results/nnfx_crypto/`

The engine will treat every strategy as a testable hypothesis and will not claim profitability.

## Goals

The system must provide:

- A Hummingbot-independent NNFX-style signal engine.
- YAML-driven configuration using Pydantic validation.
- Replaceable indicators through a registry.
- Single-pair and batch portfolio backtesting without exchange connectivity.
- Backtest exports as CSV, JSON, Markdown, PNG, and HTML.
- A Hummingbot V2 controller wrapper that delegates all strategy logic to the portable engine.
- Unit tests covering config validation, indicators, signal generation, risk behavior, no-lookahead constraints, and output exports.

## Non-Goals

The first build will not:

- Connect live trading.
- Claim or imply profitability.
- Optimize parameters.
- Mix backtest mechanics into the Hummingbot controller.
- Implement proprietary indicator behavior when formulas are unavailable.
- Silently drop missing or malformed data.

## Package Layout

```text
src/nnfx_crypto/
  __init__.py

  config/
    schema.py
    loader.py

  data/
    ohlcv_loader.py
    validation.py
    resample.py

  indicators/
    __init__.py
    base.py
    atr.py
    frama.py
    reflex.py
    stablefx.py
    stiffness.py
    crossroads.py
    registry.py

  signals/
    signal_types.py
    nnfx_signal_engine.py
    continuation_filter.py

  risk/
    atr_risk_model.py
    position_sizing.py
    trade_state.py

  backtest/
    event_backtester.py
    portfolio_backtester.py
    metrics.py
    trade_log.py
    run.py
    run_batch.py

  reports/
    report_writer.py
    chart_writer.py

  hummingbot/
    controllers/
      nnfx_algo5_controller.py
    adapters/
      hummingbot_config_adapter.py
      executor_action_adapter.py
```

Supporting files:

```text
configs/nnfx_crypto/
  algo5_fractal_rigidity_btc_1h.yml
  algo5_fractal_rigidity_eth_4h.yml
  algo5_fractal_rigidity_sol_1d.yml
  portfolio_algo5.yml
  hummingbot_nnfx_algo5_controller.yml

data/nnfx_crypto/
  raw/
  processed/

results/nnfx_crypto/
  backtests/
  reports/
  charts/

tests/
  test_nnfx_config_schema.py
  test_nnfx_indicators_no_lookahead.py
  test_nnfx_signal_engine.py
  test_nnfx_risk_model.py
  test_nnfx_backtester_basic.py
```

## Architecture

The portable package has four boundaries:

1. Config and data loading validate the inputs and return typed config objects plus normalized OHLCV dataframes.
2. Indicators append deterministic columns to OHLCV data using only current and past candles.
3. The signal engine evaluates completed candles and emits entry or exit intents.
4. Backtest and Hummingbot adapters consume those intents differently, without changing strategy rules.

The Hummingbot controller is intentionally thin. It reads controller config, requests candles, converts them into a pandas dataframe, calls `NNFXSignalEngine`, and maps engine intents into executor actions.

## Default Strategy Template

The first default strategy is Algorithm 5: Fractal-Rigidity.

Mapping:

- Baseline: FRAMA
- C1: Reflex
- C2: StableFX
- Filter: Stiffness Indicator
- Exit: Cross Roads
- Risk: ATR(14), 1.25 ATR stop, 1.0 ATR TP1, two half-trades, breakeven after TP1, Cross Roads exit for the remainder

Long entry requires:

- `baseline_signal == LONG`
- `c1_signal == LONG`
- `c2_signal == LONG`
- `filter_pass_long == true`
- risk model allows trade
- no open position on that pair
- no continuation trade when continuation trades are disabled

Short entry mirrors the long rules with short signals.

Long exit occurs on Cross Roads long exit, stop, TP1 for the first half, or risk rule breach.

Short exit mirrors the long exit rules.

## Indicator Policy

All indicators implement:

```python
class Indicator:
    name: str

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        ...
```

Outputs normalize directional state into:

- `LONG = 1`
- `SHORT = -1`
- `NEUTRAL = 0`

Unknown indicator names raise clear validation errors. Missing parameters use documented defaults.

FRAMA, ATR, Stiffness, and Cross Roads will be implemented directly. Reflex and StableFX will be deterministic placeholders unless a reliable exact formula is available in the workspace. Placeholder modules must be named and documented clearly and must not pretend to reproduce proprietary behavior.

## Backtester

The backtester is event-style and bar-based.

Rules:

- Signals use only closed candles.
- Entries occur on the next bar open when `use_next_bar_open = true`.
- Fees and slippage are included.
- ATR stop, TP1, breakeven, and indicator exits are modeled.
- Two half-positions are tracked as linked child positions.
- One open position per pair is enforced by default.
- Missing data raises explicit errors.

Each run writes:

```text
results/nnfx_crypto/backtests/<run_id>/
  resolved_config.yml
  trades.csv
  equity_curve.csv
  metrics.json
  summary.md
  chart_price_signals.png
  chart_equity_curve.png
  report.html
```

Metrics include PnL, drawdown, profit factor, expectancy, Sharpe, Sortino, win rate, trade counts, win/loss sizes, consecutive losses, time in market, underwater time, trade duration, fees, slippage, buy-and-hold return, and pair/timeframe breakdowns.

## CLI

Single run:

```powershell
python -m nnfx_crypto.backtest.run --config configs/nnfx_crypto/algo5_fractal_rigidity_btc_1h.yml
```

Batch run:

```powershell
python -m nnfx_crypto.backtest.run_batch --config configs/nnfx_crypto/portfolio_algo5.yml
```

## Testing Strategy

Implementation will use test-first slices.

Minimum tests:

- Config validation accepts valid Algo 5 config.
- Unknown indicators raise clear errors.
- Indicator modules emit required output columns.
- Indicator outputs do not change for earlier rows when future rows are appended.
- Signal engine emits long entry.
- Signal engine emits short entry.
- Filter blocks entries.
- Cross Roads exits long and short positions.
- ATR sizing uses account equity, risk percent, and stop distance.
- TP1 closes the first half.
- Breakeven moves the second-half stop after TP1.
- One open position per pair is enforced.
- Backtest exports required files.

Verification commands:

```powershell
pytest -q
ruff check .
mypy src
```

`mypy` may require adding it to project dependencies because the current `pyproject.toml` does not list it.

## Implementation Order

1. Add package skeleton, config schema, loader, indicator registry, signal types, and CLI stubs.
2. Add failing tests for config and registry behavior, then implement them.
3. Add indicator tests and implement ATR, FRAMA, Stiffness, Cross Roads, Reflex placeholder, and StableFX placeholder.
4. Add signal engine tests and implement entry, exit, and continuation filter behavior.
5. Add risk model tests and implement ATR sizing, TP1, breakeven, and one-position constraints.
6. Add backtester export tests and implement single-pair backtest, metrics, and reports.
7. Add batch runner and portfolio summary.
8. Add Hummingbot adapter/controller files using the same engine.
9. Update README with usage and dry-run documentation.

## Open Constraints

This workspace is not currently a Git repository, so the design document cannot be committed here unless Git is initialized or this folder is placed inside a repository.

