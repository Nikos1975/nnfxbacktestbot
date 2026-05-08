# NNFX Crypto Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate `nnfx_crypto` package with a YAML-driven Algo 5 research backtester and a thin Hummingbot V2 controller wrapper.

**Architecture:** The portable engine owns config, data loading, indicators, signals, risk, backtests, and reports. Hummingbot code stays in an adapter/controller layer and calls the same `NNFXSignalEngine` used by the backtester. Runtime files are namespaced under `configs/nnfx_crypto/`, `data/nnfx_crypto/`, and `results/nnfx_crypto/`.

**Tech Stack:** Python 3.11, pandas, numpy, pydantic v2, PyYAML, matplotlib, pytest, ruff, optional mypy.

---

## File Map

- Create `src/nnfx_crypto/config/schema.py`: Pydantic config models and defaults.
- Create `src/nnfx_crypto/config/loader.py`: YAML loading and resolved-config export.
- Create `src/nnfx_crypto/indicators/base.py`: common indicator protocol.
- Create `src/nnfx_crypto/indicators/registry.py`: indicator lookup and clear unknown-name errors.
- Create `src/nnfx_crypto/indicators/*.py`: ATR, FRAMA, Reflex placeholder, StableFX placeholder, Stiffness, Cross Roads.
- Create `src/nnfx_crypto/signals/signal_types.py`: `SignalState`, `ExitSignal`, `TradeIntent`.
- Create `src/nnfx_crypto/signals/continuation_filter.py`: continuation-entry checks.
- Create `src/nnfx_crypto/signals/nnfx_signal_engine.py`: indicator computation and entry/exit intent generation.
- Create `src/nnfx_crypto/risk/*.py`: ATR sizing and trade state transitions.
- Create `src/nnfx_crypto/data/*.py`: OHLCV loading, validation, and resampling.
- Create `src/nnfx_crypto/backtest/*.py`: event backtester, batch runner, metrics, trade log, CLI modules.
- Create `src/nnfx_crypto/reports/*.py`: Markdown/HTML/PNG report writers.
- Create `src/nnfx_crypto/hummingbot/**/*.py`: V2 controller wrapper and adapters.
- Create `configs/nnfx_crypto/*.yml`: Algo 5 single and portfolio configs.
- Modify `pyproject.toml`: add `nnfx-backtest`, `nnfx-backtest-batch`, and `mypy` dependency if absent.
- Modify `README.md`: add NNFX commands and caveats.

---

### Task 1: Package Skeleton And Config Schema

**Files:**
- Create: `src/nnfx_crypto/__init__.py`
- Create: `src/nnfx_crypto/config/__init__.py`
- Create: `src/nnfx_crypto/config/schema.py`
- Create: `src/nnfx_crypto/config/loader.py`
- Create: `tests/test_nnfx_config_schema.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_nnfx_config_schema.py`:

```python
from pathlib import Path

import pytest
from pydantic import ValidationError

from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.config.schema import StrategyConfig


def valid_config_dict() -> dict:
    return {
        "strategy": {
            "name": "algo5_fractal_rigidity",
            "mode": "backtest",
            "direction_mode": "both",
            "allow_continuation_trades": False,
        },
        "market": {
            "connector": "binance_perpetual",
            "trading_pair": "BTC-USDT",
            "timeframe": "1h",
            "quote_asset": "USDT",
            "base_asset": "BTC",
        },
        "data": {
            "source": "csv",
            "path": "data/nnfx_crypto/processed/BTC-USDT_1h.csv",
            "start": "2021-01-01",
            "end": "2026-01-01",
        },
        "indicators": {
            "baseline": {"name": "frama", "params": {"length": 10, "fc": 1, "sc": 198}},
            "c1": {"name": "reflex", "params": {"length": 50}},
            "c2": {"name": "stablefx", "params": {"length": 14, "signal_length": 5}},
            "volume_or_volatility_filter": {
                "name": "stiffness",
                "params": {"length": 60, "threshold": 50.0},
            },
            "exit": {"name": "crossroads", "params": {"fast_length": 2, "slow_length": 24}},
        },
        "risk": {
            "account_equity": 10000,
            "risk_per_trade_pct": 0.005,
            "atr_length": 14,
            "stop_loss_atr_multiplier": 1.25,
            "tp1_atr_multiplier": 1.0,
            "use_two_half_positions": True,
            "move_second_half_to_breakeven_after_tp1": True,
            "max_open_positions_per_pair": 1,
            "max_total_open_positions": 3,
            "max_daily_loss_pct": 0.02,
            "max_total_drawdown_pct": 0.20,
        },
        "execution": {
            "order_type": "market",
            "fee_pct": 0.0006,
            "slippage_pct": 0.0005,
            "use_next_bar_open": True,
        },
        "backtest": {
            "warmup_bars": 300,
            "initial_capital": 10000,
            "export_trades_csv": True,
            "export_equity_curve_csv": True,
            "export_metrics_json": True,
            "export_html_report": True,
            "export_chart_png": True,
        },
    }


def test_strategy_config_accepts_algo5_defaults():
    cfg = StrategyConfig.model_validate(valid_config_dict())

    assert cfg.strategy.name == "algo5_fractal_rigidity"
    assert cfg.market.trading_pair == "BTC-USDT"
    assert cfg.indicators.baseline.name == "frama"
    assert cfg.risk.stop_loss_atr_multiplier == 1.25


def test_strategy_config_rejects_unknown_timeframe():
    data = valid_config_dict()
    data["market"]["timeframe"] = "2h"

    with pytest.raises(ValidationError, match="timeframe"):
        StrategyConfig.model_validate(data)


def test_load_strategy_config_reads_yaml(tmp_path: Path):
    config_path = tmp_path / "strategy.yml"
    config_path.write_text(
        """
strategy:
  name: algo5_fractal_rigidity
market:
  trading_pair: BTC-USDT
data:
  path: data/nnfx_crypto/processed/BTC-USDT_1h.csv
indicators:
  baseline: {name: frama, params: {length: 10}}
  c1: {name: reflex, params: {length: 50}}
  c2: {name: stablefx, params: {length: 14}}
  volume_or_volatility_filter: {name: stiffness, params: {length: 60}}
  exit: {name: crossroads, params: {fast_length: 2, slow_length: 24}}
""",
        encoding="utf-8",
    )

    cfg = load_strategy_config(config_path)

    assert cfg.strategy.mode == "backtest"
    assert cfg.market.connector == "binance_perpetual"
    assert cfg.market.timeframe == "1h"
    assert cfg.risk.atr_length == 14
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_nnfx_config_schema.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'nnfx_crypto'`.

- [ ] **Step 3: Implement config package**

Create `src/nnfx_crypto/__init__.py`:

```python
"""Portable NNFX-style crypto strategy research engine."""

__version__ = "0.1.0"
```

Create `src/nnfx_crypto/config/__init__.py`:

```python
"""Configuration loading and validation."""
```

Create `src/nnfx_crypto/config/schema.py` with literal choices for direction, timeframe, source, and order type; defaults matching the approved design; `extra="forbid"` on all models; and fields named exactly as used by the tests.

Create `src/nnfx_crypto/config/loader.py`:

```python
from pathlib import Path
from typing import Any

import yaml

from nnfx_crypto.config.schema import StrategyConfig


def load_strategy_config(path: str | Path) -> StrategyConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    return StrategyConfig.model_validate(raw)


def dump_resolved_config(config: StrategyConfig, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config.model_dump(mode="json"), handle, sort_keys=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
pytest tests/test_nnfx_config_schema.py -q
```

Expected: PASS.

---

### Task 2: Indicator Registry And Core Indicators

**Files:**
- Create: `src/nnfx_crypto/indicators/__init__.py`
- Create: `src/nnfx_crypto/indicators/base.py`
- Create: `src/nnfx_crypto/indicators/registry.py`
- Create: `src/nnfx_crypto/indicators/atr.py`
- Create: `src/nnfx_crypto/indicators/frama.py`
- Create: `src/nnfx_crypto/indicators/stiffness.py`
- Create: `src/nnfx_crypto/indicators/crossroads.py`
- Create: `src/nnfx_crypto/indicators/reflex.py`
- Create: `src/nnfx_crypto/indicators/stablefx.py`
- Create: `tests/test_nnfx_indicators_no_lookahead.py`

- [ ] **Step 1: Write failing indicator tests**

Create tests that build a deterministic OHLCV dataframe, call each registered indicator, and assert these columns:

```python
EXPECTED_COLUMNS = {
    "atr": ["atr"],
    "frama": ["baseline_value", "baseline_signal"],
    "reflex": ["reflex_value", "c1_signal"],
    "stablefx": ["stablefx_value", "c2_signal"],
    "stiffness": ["stiffness_value", "filter_pass_long", "filter_pass_short"],
    "crossroads": ["crossroads_fast", "crossroads_slow", "exit_signal"],
}
```

Add this no-lookahead assertion:

```python
def assert_no_lookahead(indicator_name: str, params: dict, output_columns: list[str]):
    df = make_ohlcv(120)
    first = get_indicator(indicator_name).compute(df.iloc[:80].copy(), params)
    second = get_indicator(indicator_name).compute(df.copy(), params).iloc[:80]
    for column in output_columns:
        pd.testing.assert_series_equal(
            first[column].reset_index(drop=True),
            second[column].reset_index(drop=True),
            check_names=False,
        )
```

Also test:

```python
def test_unknown_indicator_raises_clear_error():
    with pytest.raises(KeyError, match="Unknown indicator 'not_real'"):
        get_indicator("not_real")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/test_nnfx_indicators_no_lookahead.py -q
```

Expected: FAIL with missing indicator modules.

- [ ] **Step 3: Implement indicators**

Implement:

- `ATRIndicator`: true range max of high-low, abs(high-previous close), abs(low-previous close), then rolling mean over `length`.
- `FRAMAIndicator`: adaptive recursive FRAMA using rolling high-low fractal dimension; output neutral before enough bars; long if close > FRAMA; short if close < FRAMA.
- `StiffnessIndicator`: percentage of the last `length` closes above `close.rolling(length).mean() - 0.2 * close.rolling(length).std()`, pass if value >= threshold.
- `CrossRoadsIndicator`: fast and slow EMAs; `EXIT_LONG = -1` when fast crosses below slow; `EXIT_SHORT = 1` when fast crosses above slow.
- `ReflexIndicator`: clearly documented placeholder using `close - close.ewm(span=length).mean()` and signal only when value crosses zero.
- `StableFXIndicator`: clearly documented placeholder using EMA and signal EMA; long when oscillator crosses above signal, short when below.

All `compute` methods must copy the dataframe before adding columns.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_indicators_no_lookahead.py -q
```

Expected: PASS.

---

### Task 3: Signal Engine

**Files:**
- Create: `src/nnfx_crypto/signals/__init__.py`
- Create: `src/nnfx_crypto/signals/signal_types.py`
- Create: `src/nnfx_crypto/signals/continuation_filter.py`
- Create: `src/nnfx_crypto/signals/nnfx_signal_engine.py`
- Create: `tests/test_nnfx_signal_engine.py`

- [ ] **Step 1: Write failing signal engine tests**

Add tests for:

- Long entry when all current signals are long, filter passes, and previous C1 was not long.
- Short entry when all current signals are short, filter passes, and previous C1 was not short.
- No entry when filter fails.
- No entry when continuation trades are disabled and previous bar was already aligned.
- Long exit when `exit_signal == EXIT_LONG`.
- Short exit when `exit_signal == EXIT_SHORT`.

Use a small dataframe with explicit columns rather than depending on indicator formulas:

```python
df = pd.DataFrame(
    {
        "close": [100, 101],
        "baseline_signal": [0, 1],
        "c1_signal": [0, 1],
        "c2_signal": [1, 1],
        "filter_pass_long": [True, True],
        "filter_pass_short": [True, True],
        "exit_signal": [0, 0],
        "atr": [2.0, 2.0],
    }
)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/test_nnfx_signal_engine.py -q
```

Expected: FAIL with missing signal engine.

- [ ] **Step 3: Implement signal engine**

Implement:

- `SignalState` as `IntEnum`: `SHORT = -1`, `NEUTRAL = 0`, `LONG = 1`.
- `ExitSignal` as `IntEnum`: `EXIT_LONG = -1`, `NONE = 0`, `EXIT_SHORT = 1`.
- `TradeIntent` dataclass with `action`, `side`, `reason`, `index`, `timestamp`.
- `is_continuation_trade(df, row_index, side)` that checks whether the previous row was already aligned.
- `NNFXSignalEngine.evaluate_bar(df, row_index, has_open_position=False)` for precomputed indicator frames.
- `NNFXSignalEngine.compute_indicators(df)` that applies registry indicators from config.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_signal_engine.py -q
```

Expected: PASS.

---

### Task 4: ATR Risk Model And Trade State

**Files:**
- Create: `src/nnfx_crypto/risk/__init__.py`
- Create: `src/nnfx_crypto/risk/position_sizing.py`
- Create: `src/nnfx_crypto/risk/trade_state.py`
- Create: `src/nnfx_crypto/risk/atr_risk_model.py`
- Create: `tests/test_nnfx_risk_model.py`

- [ ] **Step 1: Write failing risk tests**

Tests:

```python
def test_atr_position_size_uses_equity_risk_and_stop_distance():
    model = ATRRiskModel(account_equity=10_000, risk_per_trade_pct=0.005, stop_loss_atr_multiplier=1.25, tp1_atr_multiplier=1.0)
    plan = model.plan_entry(side="long", entry_price=100.0, atr=2.0)
    assert plan.stop_price == 97.5
    assert plan.tp1_price == 102.0
    assert plan.total_quantity == 20.0
    assert plan.first_half_quantity == 10.0
    assert plan.second_half_quantity == 10.0


def test_tp1_closes_half_and_moves_second_stop_to_breakeven():
    trade = OpenTrade.open_long(entry_price=100.0, quantity=20.0, stop_price=97.5, tp1_price=102.0)
    trade.apply_high_low(high=102.1, low=99.5, move_stop_to_breakeven=True)
    assert trade.first_half_closed is True
    assert trade.remaining_quantity == 10.0
    assert trade.stop_price == 100.0
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/test_nnfx_risk_model.py -q
```

Expected: FAIL with missing risk modules.

- [ ] **Step 3: Implement risk model**

Implement long and short entry planning. Formula:

- Risk amount = `account_equity * risk_per_trade_pct`
- Stop distance = `atr * stop_loss_atr_multiplier`
- Quantity = `risk_amount / stop_distance`
- TP1 distance = `atr * tp1_atr_multiplier`
- Long stop = entry - stop distance
- Short stop = entry + stop distance
- Long TP1 = entry + TP1 distance
- Short TP1 = entry - TP1 distance

Implement `OpenTrade.apply_high_low` to close first half at TP1 and move stop to entry for the second half when enabled.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_risk_model.py -q
```

Expected: PASS.

---

### Task 5: Data Loader And Event Backtester

**Files:**
- Create: `src/nnfx_crypto/data/__init__.py`
- Create: `src/nnfx_crypto/data/ohlcv_loader.py`
- Create: `src/nnfx_crypto/data/validation.py`
- Create: `src/nnfx_crypto/backtest/__init__.py`
- Create: `src/nnfx_crypto/backtest/trade_log.py`
- Create: `src/nnfx_crypto/backtest/metrics.py`
- Create: `src/nnfx_crypto/backtest/event_backtester.py`
- Create: `tests/test_nnfx_backtester_basic.py`

- [ ] **Step 1: Write failing backtester test**

Create a 60-bar CSV in `tmp_path`, create a config that points to it, run the backtester, and assert:

- `trades.csv` exists.
- `equity_curve.csv` exists.
- `metrics.json` exists.
- `summary.md` exists.
- `resolved_config.yml` exists.
- No more than one open position per pair appears in the trade log.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/test_nnfx_backtester_basic.py -q
```

Expected: FAIL with missing backtester modules.

- [ ] **Step 3: Implement loader and backtester**

Implement:

- CSV loading with required columns `timestamp`, `open`, `high`, `low`, `close`, `volume`.
- Timestamp parsing and sort.
- Duplicate timestamp rejection.
- Missing OHLCV rejection.
- Warmup skip.
- Closed-candle signal evaluation.
- Next-bar-open entry when configured.
- Slippage and fee application.
- ATR stop, TP1, breakeven, and Cross Roads exit.
- Equity curve update per bar.

Keep the first implementation intentionally simple: one active trade per single-pair run and deterministic close reasons.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_backtester_basic.py -q
```

Expected: PASS.

---

### Task 6: Reports, Charts, And CLI

**Files:**
- Create: `src/nnfx_crypto/reports/__init__.py`
- Create: `src/nnfx_crypto/reports/report_writer.py`
- Create: `src/nnfx_crypto/reports/chart_writer.py`
- Create: `src/nnfx_crypto/backtest/run.py`
- Create: `configs/nnfx_crypto/algo5_fractal_rigidity_btc_1h.yml`
- Create: `configs/nnfx_crypto/algo5_fractal_rigidity_eth_4h.yml`
- Create: `configs/nnfx_crypto/algo5_fractal_rigidity_sol_1d.yml`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing CLI/report test**

Extend `tests/test_nnfx_backtester_basic.py` with a CLI-level smoke test using `subprocess.run`:

```python
result = subprocess.run(
    [sys.executable, "-m", "nnfx_crypto.backtest.run", "--config", str(config_path)],
    cwd=project_root,
    text=True,
    capture_output=True,
)
assert result.returncode == 0
assert "results/nnfx_crypto/backtests/" in result.stdout
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/test_nnfx_backtester_basic.py -q
```

Expected: FAIL because CLI does not exist.

- [ ] **Step 3: Implement reports and CLI**

Implement:

- `report_writer.write_summary_md`
- `report_writer.write_report_html`
- `chart_writer.write_price_signal_chart`
- `chart_writer.write_equity_curve_chart`
- `backtest.run.main` using `argparse`

Use matplotlib with the non-interactive `Agg` backend.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_backtester_basic.py -q
```

Expected: PASS.

---

### Task 7: Batch Runner And Portfolio Config

**Files:**
- Create: `src/nnfx_crypto/backtest/portfolio_backtester.py`
- Create: `src/nnfx_crypto/backtest/run_batch.py`
- Create: `configs/nnfx_crypto/portfolio_algo5.yml`
- Create: `tests/test_nnfx_batch_runner.py`

- [ ] **Step 1: Write failing batch test**

Test that `run_batch` accepts a portfolio config with three strategy config paths and writes:

- `portfolio_summary.csv`
- `portfolio_metrics.json`
- one child run folder per config

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/test_nnfx_batch_runner.py -q
```

Expected: FAIL with missing batch runner.

- [ ] **Step 3: Implement batch runner**

Implement portfolio config parsing with:

```yaml
portfolio:
  name: portfolio_algo5
  strategies:
    - configs/nnfx_crypto/algo5_fractal_rigidity_btc_1h.yml
    - configs/nnfx_crypto/algo5_fractal_rigidity_eth_4h.yml
    - configs/nnfx_crypto/algo5_fractal_rigidity_sol_1d.yml
```

Batch runner calls the single backtester for each config, then aggregates metrics by pair and timeframe.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_batch_runner.py -q
```

Expected: PASS.

---

### Task 8: Hummingbot V2 Adapter And Controller Wrapper

**Files:**
- Create: `src/nnfx_crypto/hummingbot/__init__.py`
- Create: `src/nnfx_crypto/hummingbot/controllers/__init__.py`
- Create: `src/nnfx_crypto/hummingbot/controllers/nnfx_algo5_controller.py`
- Create: `src/nnfx_crypto/hummingbot/adapters/__init__.py`
- Create: `src/nnfx_crypto/hummingbot/adapters/hummingbot_config_adapter.py`
- Create: `src/nnfx_crypto/hummingbot/adapters/executor_action_adapter.py`
- Create: `configs/nnfx_crypto/hummingbot_nnfx_algo5_controller.yml`
- Create: `tests/test_nnfx_hummingbot_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Tests should not import Hummingbot. They validate:

- Hummingbot-style YAML maps into `StrategyConfig`.
- Adapter converts a list of candle dicts into an OHLCV dataframe.
- Executor adapter maps a long `TradeIntent` into a plain action dict with connector, pair, side, amount, stop, and TP fields.
- Duplicate signal protection returns no action when an executor is already open for the pair.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/test_nnfx_hummingbot_adapter.py -q
```

Expected: FAIL with missing adapter modules.

- [ ] **Step 3: Implement adapter layer**

Implement pure-Python adapters first. The controller file may include guarded imports:

```python
try:
    from hummingbot.strategy_v2.controllers.directional_trading_controller_base import DirectionalTradingControllerBase
except ImportError:
    DirectionalTradingControllerBase = object
```

Controller business logic must delegate to:

- `hummingbot_config_adapter`
- `NNFXSignalEngine`
- `executor_action_adapter`

Do not hardcode Algo 5 parameters inside the controller.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/test_nnfx_hummingbot_adapter.py -q
```

Expected: PASS.

---

### Task 9: README, Lint, Type Check, And Sample Run

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update README**

Add:

- NNFX package purpose.
- No-profitability caveat.
- Single backtest command.
- Batch command.
- Hummingbot controller wrapper location.
- Placeholder indicator caveat for Reflex and StableFX.

- [ ] **Step 2: Run full tests**

Run:

```powershell
pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run Ruff**

Run:

```powershell
ruff check .
```

Expected: PASS.

- [ ] **Step 4: Run mypy**

Run:

```powershell
mypy src
```

Expected: PASS, or if mypy is not installed, add it to `pyproject.toml` dependencies and run again.

- [ ] **Step 5: Run sample backtest**

Run:

```powershell
python -m nnfx_crypto.backtest.run --config configs/nnfx_crypto/algo5_fractal_rigidity_btc_1h.yml
```

Expected: prints the created `results/nnfx_crypto/backtests/<run_id>/` path and writes all required files.

