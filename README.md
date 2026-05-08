# Trading System Scaffold

Self-hosted crypto research, backtesting, dry-run, and later live execution scaffold.

Core rule:
- Shared logic lives in `src/trading_system/`
- Freqtrade and Hummingbot are adapters/execution engines, not the source of truth.

Initial workflow:
1. Put OHLCV CSV files in `data/raw/`
2. Run grid backtest with `scripts/run_grid_backtest.ps1`
3. Review reports in `reports/backtests/`
4. Only after stable backtests, port strategy to Freqtrade or Hummingbot.

## NNFX Crypto Research Engine

`src/nnfx_crypto/` is a separate portable NNFX-style research engine. It does not depend on
Hummingbot. Hummingbot code lives only in `src/nnfx_crypto/hummingbot/` as an adapter/controller
wrapper.

Default strategy template: Algorithm 5 Fractal-Rigidity.

- Baseline: FRAMA
- C1: Reflex placeholder
- C2: StableFX placeholder
- Filter: Stiffness
- Exit: Cross Roads
- Risk: ATR(14), 1.25 ATR stop, TP1, breakeven, trailing remainder by exit signal

Reflex and StableFX are deterministic placeholders because exact formulas are not available in this
workspace. They preserve the interface and do not claim proprietary parity. No strategy here claims
profitability.

Indicator source status is exported into every `resolved_config.yml` under
`indicator_metadata`:

- FRAMA: Stonehill `.mq4` source port
- Stiffness: Stonehill `.mq4` source port
- Cross Roads: approximation because Stonehill download is `.ex4` only
- Reflex: placeholder because Stonehill download is `.ex4` only
- StableFX: placeholder because Stonehill download is `.ex4` only

Run one backtest:

```powershell
python -m nnfx_crypto.backtest.run --config configs/nnfx_crypto/algo5_fractal_rigidity_btc_1h.yml
```

Run batch:

```powershell
python -m nnfx_crypto.backtest.run_batch --config configs/nnfx_crypto/portfolio_algo5.yml
```

Outputs are written under `results/nnfx_crypto/backtests/<run_id>/`:

- `resolved_config.yml`
- `trades.csv`
- `equity_curve.csv`
- `metrics.json`
- `summary.md`
- `chart_price_signals.png`
- `chart_equity_curve.png`
- `report.html`

Hummingbot wrapper:

- Controller: `src/nnfx_crypto/hummingbot/controllers/nnfx_algo5_controller.py`
- Example config: `configs/nnfx_crypto/hummingbot_nnfx_algo5_controller.yml`
- Dry-run notes: `docs/nnfx_hummingbot_dry_run.md`

The controller delegates business logic to `NNFXSignalEngine`; it only adapts candles, config, and
executor actions.
