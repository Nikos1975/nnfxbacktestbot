"""Parameter sweep runner for NNFX crypto backtests.

Generates config permutations from a base YAML, runs each backtest,
and calls summarize_backtest_results.py at the end.

Supports --timeframes to run the same strategy across multiple timeframes.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Default parameter grid
# ---------------------------------------------------------------------------
DEFAULT_GRID = {
    "indicators.c2.params.start_len": [1, 2, 3],
    "indicators.c2.params.lookback_period": [14, 18, 24, 30],
    "risk.risk_per_trade_pct": [0.01, 0.02],
    "risk.atr_length": [10, 14, 20],
    "risk.stop_loss_atr_multiplier": [1.0, 1.25, 1.5, 2.0],
    "risk.tp1_atr_multiplier": [0.5, 1.0, 1.5, 2.0],
}

# Canonical data-path pattern: {pair}_{timeframe}.csv
# When --timeframes is used, data.path is derived automatically.
DATA_PATH_TEMPLATE = "data/nnfx_crypto/processed/{pair}_{timeframe}.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def deep_set(cfg: dict, dotpath: str, value) -> None:
    keys = dotpath.split(".")
    obj = cfg
    for key in keys[:-1]:
        obj = obj.setdefault(key, {})
    obj[keys[-1]] = value


def deep_get(cfg: dict, dotpath: str, default=None):
    keys = dotpath.split(".")
    obj = cfg
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key, default)
    return obj


def build_grid(grid_spec: dict) -> list[dict]:
    keys = list(grid_spec.keys())
    values = [grid_spec[k] for k in keys]
    combos = []
    for combo in itertools.product(*values):
        combos.append(dict(zip(keys, combo)))
    return combos


def write_config(base: dict, overrides: dict, out_path: Path) -> Path:
    cfg = copy.deepcopy(base)
    for dotpath, value in overrides.items():
        deep_set(cfg, dotpath, value)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)
    return out_path


def resolve_data_path(base_config: dict, timeframe: str) -> str:
    """Derive the data CSV path for a given timeframe from the base config's pair."""
    pair = (
        deep_get(base_config, "market.trading_pair", "BTC-USDT")
        .replace("/", "-")
    )
    return DATA_PATH_TEMPLATE.format(pair=pair, timeframe=timeframe)


def run_one(python: str, config_path: Path) -> tuple[str, bool, str]:
    """Run a single backtest. Returns (run_dir, success, error_message)."""
    try:
        result = subprocess.run(
            [python, "-m", "nnfx_crypto.backtest.run", "--config", str(config_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        run_dir = ""
        success = result.returncode == 0
        error_msg = ""

        if success:
            # The run script prints the run_dir as the last line of stdout
            lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
            if lines:
                run_dir = lines[-1]
            print(f"  OK -> {run_dir}")
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            print(f"  FAILED: {error_msg[:200]}...")
            
        return run_dir, success, error_msg
    except Exception as exc:
        print(f"  EXCEPTION: {exc}")
        return "", False, str(exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a parameter sweep over an NNFX backtest config."
    )
    parser.add_argument("--base-config", required=True,
                        help="Path to base strategy YAML config.")
    parser.add_argument("--grid", nargs="*",
                        help="Parameter overrides: key=v1,v2,v3 ...")
    parser.add_argument("--timeframes", nargs="*",
                        help="Timeframes to sweep, e.g. 1h 4h 1d. "
                             "Overrides market.timeframe and data.path automatically.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print configs without running backtests.")
    args = parser.parse_args()

    base_path = Path(args.base_config)
    if not base_path.exists():
        print(f"Base config not found: {base_path}")
        sys.exit(1)

    with open(base_path, "r", encoding="utf-8") as fh:
        base_config = yaml.safe_load(fh) or {}

    # Build parameter grid (may be empty — just one combo with no overrides)
    if args.grid:
        grid_spec: dict[str, list] = {}
        for item in args.grid:
            key, vals_str = item.split("=", 1)
            values: list = []
            for v in vals_str.split(","):
                v = v.strip()
                try:
                    values.append(int(v))
                except ValueError:
                    try:
                        values.append(float(v))
                    except ValueError:
                        values.append(v)
            grid_spec[key] = values
    else:
        grid_spec = {}  # no param grid — just timeframe sweep

    combos = build_grid(grid_spec) if grid_spec else [{}]

    # Timeframes list — default to single timeframe from base config
    timeframes: list[str] = args.timeframes or [
        deep_get(base_config, "market.timeframe", "1h")
    ]

    total = len(combos) * len(timeframes)
    sweep_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    configs_dir = PROJECT_ROOT / "configs" / "nnfx_crypto" / "generated" / "sweeps" / sweep_id
    manifest_dir = PROJECT_ROOT / "results" / "nnfx_crypto" / "sweeps" / sweep_id
    manifest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Sweep {sweep_id}: {len(combos)} param combo(s) × {len(timeframes)} timeframe(s) = {total} run(s)")
    print(f"Timeframes: {timeframes}")
    if grid_spec:
        for k, v in grid_spec.items():
            print(f"  {k}: {v}")

    if args.dry_run:
        n = 0
        for tf in timeframes:
            for combo in combos:
                n += 1
                print(f"\n--- Run {n}/{total} | timeframe={tf} ---")
                for k, v in combo.items():
                    print(f"  {k} = {v}")
        print(f"\nTotal: {total} configs (dry run, nothing executed)")
        return

    python = sys.executable
    manifest_rows: list[dict] = []
    n = 0

    for tf in timeframes:
        for i, combo in enumerate(combos):
            n += 1
            # Build overrides: timeframe + data path + any param grid overrides
            overrides = dict(combo)
            overrides["market.timeframe"] = tf
            overrides["data.path"] = resolve_data_path(base_config, tf)

            # Task: Patch c2 and exit Cross Roads consistently.
            # If we are patching C2 parameters, we should apply them to Exit as well
            # if Exit is also a crossroads indicator in the base config.
            sync_params = ["start_len", "lookback_period", "source"]
            for p in sync_params:
                c2_key = f"indicators.c2.params.{p}"
                exit_key = f"indicators.exit.params.{p}"
                if c2_key in overrides and exit_key not in overrides:
                    if deep_get(base_config, "indicators.exit.name") == "crossroads":
                        overrides[exit_key] = overrides[c2_key]
                elif exit_key in overrides and c2_key not in overrides:
                    if deep_get(base_config, "indicators.c2.name") == "crossroads":
                        overrides[c2_key] = overrides[exit_key]

            # Verify data file exists before running
            data_file = PROJECT_ROOT / overrides["data.path"]
            if not data_file.exists():
                print(f"\n[{n}/{total}] SKIP — data file not found: {data_file}")
                manifest_rows.append({
                    "combo_index": i, "timeframe": tf,
                    "generated_config_path": "", "result_folder": "", 
                    "status": "SKIPPED",
                    "error_message": "data_file_missing",
                    **combo,
                })
                continue

            tf_tag = tf.replace("/", "")
            combo_tag = "_".join(f"{k.split('.')[-1]}-{v}" for k, v in combo.items()) if combo else "base"
            config_name = f"sweep_{n:04d}_{tf_tag}_{combo_tag}.yml"
            config_path = write_config(base_config, overrides, configs_dir / config_name)

            print(f"\n[{n}/{total}] timeframe={tf} | {config_name}")
            for k, v in combo.items():
                print(f"  {k} = {v}")

            result_folder, success, error_message = run_one(python, config_path)

            row = {
                "combo_index": i,
                "timeframe": tf,
                "generated_config_path": str(config_path),
                "result_folder": result_folder,
                "status": "OK" if success else "FAILED",
                "error_message": error_message,
            }
            # Include all parameters from the combo
            row.update(combo)
            manifest_rows.append(row)

    # Write manifest
    import pandas as pd
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_df.to_csv(manifest_dir / "manifest.csv", index=False)
    print(f"\nManifest written: {manifest_dir / 'manifest.csv'}")

    # Summarize
    print("\nRunning summarize_backtest_results.py...")
    subprocess.run(
        [python, str(PROJECT_ROOT / "scripts" / "summarize_backtest_results.py")],
        cwd=str(PROJECT_ROOT),
    )
    print("Sweep complete.")


if __name__ == "__main__":
    main()
