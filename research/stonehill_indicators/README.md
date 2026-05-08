# Stonehill Indicator Research Archive

Downloaded from Stonehill Forex Indicator Library on 2026-05-08:

- `FRAMA.zip` from `https://stonehillforex.com/indicator-library/`
- `Stiffness.zip` from `https://stonehillforex.com/indicator-library/`
- `reflex.zip` from `https://stonehillforex.com/indicator-library/`
- `Cross_Roads.zip` from `https://stonehillforex.com/indicator-library/`
- `Stable_nrp.zip` from `https://stonehillforex.com/indicator-library/`

`manifest.json` records file sizes and SHA-256 hashes for downloaded archives and extracted files.
Regenerate it with:

```powershell
python -m nnfx_crypto.tools.stonehill_manifest `
  --downloads-dir research/stonehill_indicators/downloads `
  --extracted-dir research/stonehill_indicators/extracted `
  --output research/stonehill_indicators/manifest.json
```

Findings:

- FRAMA includes `.mq4` source and `.ex4`.
- Stiffness includes `.mq4` source and `.ex4`.
- Reflex is `.ex4` only in the downloaded archive.
- Cross Roads is `.ex4` only in the downloaded archive.
- StableFX is `.ex4` only in the downloaded archive.

Implementation impact:

- `nnfx_crypto.indicators.stiffness` now follows the Stonehill MQ4 period structure:
  `period1`/`ma_length` for the SMA/stdev window, `period3`/`length` for summation,
  and `period2`/`signal_length` for signal smoothing.
- `nnfx_crypto.indicators.frama` now follows the Stonehill MQ4 two-window structure:
  `period_frama`/`length` controls both adjacent windows and warmup is `2 * period`.
  MQ4 `PriceType` values `0..6` are supported: close, open, high, low, median,
  typical, and weighted.
- Reflex, Cross Roads, and StableFX cannot be translated safely from `.ex4`; compiled
  MetaTrader binaries are not source. Current Reflex and StableFX remain documented
  deterministic placeholders. Cross Roads remains an EMA-cross approximation until MQ source
  is available.
- Every resolved backtest config exports `indicator_metadata` so reports preserve whether each
  module is a source port, approximation, placeholder, or standard formula.

Tooling:

```powershell
python -m nnfx_crypto.tools.mql4_scaffold `
  --source research/stonehill_indicators/extracted/FRAMA/frama-indicator.mq4 `
  --output research/stonehill_indicators/generated/frama_indicator_scaffold.py `
  --class-name StonehillFramaScaffold `
  --signal-column baseline_signal
```

The scaffold tool extracts `input`/`extern` parameters, declared buffers, and indicator
buffer count. It does not auto-translate formulas; generated code intentionally raises
`NotImplementedError` until a human ports the formula and adds no-lookahead tests.
