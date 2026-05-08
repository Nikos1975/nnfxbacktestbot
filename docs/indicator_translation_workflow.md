# Indicator Translation and Recreation Workflow

This document outlines the safe, legal workflow for converting or recreating MetaTrader indicators into Python for the `nnfx_crypto` backtesting system.

## Important Constraints

**EX4 Decompilation is Strictly Prohibited.**
- We do not build, use, or support EX4 decompilers.
- We do not attempt to reverse-engineer compiled EX4 binaries.
- We do not bypass protections or recover proprietary source code.

## What is Supported
We support creating Python equivalents using:
1. MQ4 source files legally provided by the user.
2. Public indicator formulas.
3. User-provided screenshots, rules, and parameter descriptions.
4. Exported indicator output values (e.g., CSV) for validation.
5. Manually written Python equivalents.

## 1. Translating MQ4 Source

If you have a legal `.mq4` source file:

1. **Place the File**: Drop the `.mq4` file into the `research/indicators/mq4/` directory.
2. **Parse Metadata**: Use the parsing helper to extract useful metadata (parameters, buffers, built-in calls):
   ```bash
   python scripts/inspect_mq4_indicator.py --file research/indicators/mq4/my_indicator.mq4
   ```
   This generates a translation notes file (e.g., JSON/TXT) highlighting inputs, outputs, and formulas without compiling the MQ4 in `research/indicators/translation_notes/`.
3. **Generate Python Skeleton**: Generate a boilerplate indicator class that fits the `nnfx_crypto` API:
   ```bash
   python scripts/generate_indicator_skeleton.py --mq4 research/indicators/mq4/my_indicator.mq4 --name MyIndicator
   ```
   This will create `src/nnfx_crypto/indicators/my_indicator.py`.
4. **Translate Formula**: Open the generated python file and translate the logic using `pandas` / `numpy`, referencing the parser's notes.

## 2. Recreating EX4-Only Indicators Safely

If you only have an `.ex4` file, you must recreate the logic without decompiling:

1. **Document Parameters**: Open MetaTrader 4, load the indicator, and document all visible parameters.
2. **Analyze Visual Behavior**: Describe how the indicator behaves on the chart (e.g., "crosses zero", "changes color on trend change").
3. **Export Values**: Export the indicator's raw buffer values from MT4 to a CSV file. The CSV should contain `Datetime`, `Open`, `High`, `Low`, `Close`, and the indicator's outputs.
4. **Manual Recreation**: Create a new Python indicator (`src/nnfx_crypto/indicators/your_indicator.py`) and attempt to recreate the formula using standard mathematical combinations (e.g., MAs, RSI, ATR) that match the visual behavior.
5. **Validation**: Use the validation harness to compare your Python output against the exported MT4 CSV.

## 3. Validating the Output

To ensure your translated or recreated indicator matches the original MT4 indicator, use the validation harness:

```bash
python scripts/validate_indicator_against_mt4_export.py --csv research/indicators/exports/mt4_output.csv --indicator your_indicator_name --py-col Py_Out --mt4-col MT4_Out --params '{"period": 14}'
```

The harness will report:
- **Mean Absolute Error (MAE)**
- **Max Absolute Error**
- **Correlation**
- **Mismatched Signal Bars**
- **First Mismatched Rows**

Tweak your Python logic until the MAE is negligible or acceptable.

## 4. Registering the Indicator

Once the indicator logic is complete and validated:

1. Open `src/nnfx_crypto/indicators/registry.py`.
2. Import your new indicator class.
3. Add it to `INDICATOR_REGISTRY`.
4. Add its metadata entry to `INDICATOR_METADATA` with its status (`source_port` or `approximation`) and source type (`mq4` or `ex4_only`).

Your indicator is now ready to be used in the config files for `baseline_signal`, `c1_signal`, `c2_signal`, `volume_or_volatility_filter`, `exit_signal`, or `ATR risk model`.
