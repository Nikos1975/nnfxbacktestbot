# Cross Roads - Translation Notes

## Validation Needed
This indicator (`src/nnfx_crypto/indicators/crossroads.py`) is currently an **approximation (v0)**. It needs to be validated against actual MT4 output.

## Required MT4 Export Columns
To validate this indicator, please use the MT4 manual workflow to export a CSV containing the following columns:
- `Date` / `Datetime`
- `Open`, `High`, `Low`, `Close`, `Volume`
- `CrossRoads_Green` (Buffer 0)
- `CrossRoads_Magenta` (Buffer 1)

## How to Compare
Once exported to `research/indicators/exports/crossroads_mt4.csv`:

```bash
# Validate Green Line
python scripts/validate_indicator_against_mt4_export.py \
    --csv research/indicators/exports/crossroads_mt4.csv \
    --indicator crossroads \
    --params '{"start_len": 2, "lookback_period": 24}' \
    --py-col crossroads_green \
    --mt4-col CrossRoads_Green

# Validate Magenta Line
python scripts/validate_indicator_against_mt4_export.py \
    --csv research/indicators/exports/crossroads_mt4.csv \
    --indicator crossroads \
    --params '{"start_len": 2, "lookback_period": 24}' \
    --py-col crossroads_magenta \
    --mt4-col CrossRoads_Magenta
```

## Acceptance Thresholds
- **Exact Formula Target:** Correlation `> 0.99` with negligible MAE.
- **Approximation Target:** Directional signal agreement `> 90%` (i.e. if the crossovers happen within 1 bar of each other).
- **Mismatched Rows:** Any mismatched crossover rows must be reviewed manually to ensure the approximation captures the trading intent.
