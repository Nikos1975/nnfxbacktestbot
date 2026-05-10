from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(r"D:\_projects\trading")

BASE_CONFIG = ROOT / "configs/nnfx_crypto/eth_4h_zlmacd_86_85_2_working_candidate.yml"

GENERATED_CONFIG_DIR = ROOT / "configs/nnfx_crypto/generated/eth_4h_zlmacd_86_85_2_exit_diagnostic"
RESULT_DIR = ROOT / "results/nnfx_crypto/eth_4h_zlmacd_86_85_2_exit_diagnostic"

EXIT_LOOKBACKS = [18, 24, 30, 36]
EXIT_START_LENS = [1, 2, 3]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def run_backtest(config_path: Path) -> Path:
    cmd = [
        str(ROOT / ".venv/Scripts/python.exe"),
        "-m",
        "nnfx_crypto.backtest.run",
        "--config",
        str(config_path),
    ]

    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    print(completed.stdout)
    if completed.returncode != 0:
        print(completed.stderr, file=sys.stderr)
        raise RuntimeError(f"Backtest failed for {config_path}")

    # The runner prints the result folder path on stdout.
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    candidate = None

    for line in reversed(lines):
        if "results" in line and "nnfx_crypto" in line:
            candidate = line
            break

    if candidate is None:
        raise RuntimeError(f"Could not find result path in output for {config_path}")

    run_dir = ROOT / candidate if not Path(candidate).is_absolute() else Path(candidate)

    if not run_dir.exists():
        raise FileNotFoundError(f"Parsed run dir does not exist: {run_dir}")

    return run_dir


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pct(value) -> float:
    if value is None:
        return 0.0
    return round(float(value) * 100.0, 2)


def num(value, digits: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def main() -> None:
    if not BASE_CONFIG.exists():
        raise FileNotFoundError(
            f"Base config not found: {BASE_CONFIG}\n"
            "Create it first from the best ETH 4h risk diagnostic run."
        )

    GENERATED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    base = load_yaml(BASE_CONFIG)

    rows = []

    for lookback in EXIT_LOOKBACKS:
        for start_len in EXIT_START_LENS:
            label = f"exit_LB{lookback}_SLEN{start_len}"
            config_name = f"eth_4h_zlmacd_86_85_2_{label}.yml"
            config_path = GENERATED_CONFIG_DIR / config_name

            cfg = copy.deepcopy(base)

            cfg["strategy"]["name"] = f"eth_4h_zlmacd_exit_{label}"

            # Keep working risk setup fixed.
            cfg["risk"]["stop_loss_atr_multiplier"] = 2.0
            cfg["risk"]["tp1_atr_multiplier"] = 1.5
            cfg["risk"]["move_second_half_to_breakeven_after_tp1"] = False

            # Keep filter disabled.
            cfg["indicators"]["volume_or_volatility_filter"] = {
                "name": "none",
                "params": {},
            }

            # Ensure corrected 4h ZL-MACD C1 remains fixed.
            cfg["indicators"]["c1"] = {
                "name": "zero_lag_macd",
                "params": {
                    "fast_length": 86,
                    "slow_length": 85,
                    "signal_length": 2,
                    "source": "close",
                },
            }

            # Keep C2 fixed.
            cfg["indicators"]["c2"] = {
                "name": "crossroads",
                "params": {
                    "start_len": 1,
                    "lookback_period": 24,
                    "source": "close",
                },
            }

            # Sweep exit only.
            cfg["indicators"]["exit"] = {
                "name": "crossroads",
                "params": {
                    "start_len": start_len,
                    "lookback_period": lookback,
                    "source": "close",
                },
            }

            write_yaml(config_path, cfg)

            print("=" * 90)
            print(f"Running {label}")
            print(f"Config: {config_path}")
            print("=" * 90)

            run_dir = run_backtest(config_path)

            metrics_path = run_dir / "metrics.json"
            settings_path = run_dir / "run_settings_summary.md"
            report_path = run_dir / "report.html"

            metrics = read_json(metrics_path)
            close_types = metrics.get("close_types", {})

            rows.append(
                {
                    "Run ID": run_dir.name,
                    "exit_lookback_period": lookback,
                    "exit_start_len": start_len,
                    "Net PnL %": pct(metrics.get("net_pnl_pct")),
                    "Max DD %": pct(metrics.get("max_drawdown_pct")),
                    "Profit Factor": num(metrics.get("profit_factor")),
                    "Sharpe": num(metrics.get("sharpe_ratio")),
                    "Sortino": num(metrics.get("sortino_ratio")),
                    "Win Rate %": pct(metrics.get("win_rate")),
                    "Total Trades": metrics.get("total_trades"),
                    "Long Trades": metrics.get("long_trades"),
                    "Short Trades": metrics.get("short_trades"),
                    "Time In Market %": pct(metrics.get("time_in_market")),
                    "Time Underwater %": pct(metrics.get("time_underwater")),
                    "Positive Month Rate %": pct(metrics.get("positive_month_rate")),
                    "Largest Win / Avg Win": num(metrics.get("largest_win_to_avg_win")),
                    "Largest Loss / Avg Loss": num(metrics.get("largest_loss_to_avg_loss")),
                    "PnL Kurtosis": num(metrics.get("pnl_kurtosis")),
                    "Recovery Factor": num(metrics.get("recovery_factor")),
                    "Payoff Ratio": num(metrics.get("payoff_ratio")),
                    "Fees Paid": num(metrics.get("fees_paid")),
                    "Slippage Cost": num(metrics.get("slippage_cost")),
                    "Total Cost Drag": num(metrics.get("cost_drag_total")),
                    "Cost Drag % of Profit": pct(metrics.get("cost_drag_pct_of_profit")),
                    "Stop Loss Exits": close_types.get("stop_loss", 0),
                    "TP1 Exits": close_types.get("tp1", 0),
                    "CrossRoads Exit Long": close_types.get("crossroads_exit_long", 0),
                    "CrossRoads Exit Short": close_types.get("crossroads_exit_short", 0),
                    "Daily Loss Limit Exits": close_types.get("daily_loss_limit", 0),
                    "Close types": close_types,
                    "Buy & Hold Return %": pct(metrics.get("buy_and_hold_return")),
                    "Report path": str(report_path),
                    "Run settings path": str(settings_path),
                }
            )

    df = pd.DataFrame(rows)

    csv_path = RESULT_DIR / "eth_4h_zlmacd_86_85_2_exit_summary.csv"
    md_path = RESULT_DIR / "eth_4h_zlmacd_86_85_2_exit_summary.md"

    df_sorted = df.sort_values(
        by=["Profit Factor", "Net PnL %", "Recovery Factor"],
        ascending=[False, False, False],
    )

    df_sorted.to_csv(csv_path, index=False)

    with md_path.open("w", encoding="utf-8") as f:
        f.write("# ETH-USDT 4h ZL-MACD 86/85/2 Exit Diagnostic\n\n")
        f.write("Base fixed settings:\n\n")
        f.write("- C1: zero_lag_macd fast=86 slow=85 signal=2\n")
        f.write("- C2: Cross Roads start_len=1 lookback=24\n")
        f.write("- Volume filter: none\n")
        f.write("- Stop ATR: 2.0\n")
        f.write("- TP1 ATR: 1.5\n")
        f.write("- Move BE: false\n\n")
        f.write("Sweep:\n\n")
        f.write("- exit.crossroads.lookback_period: 18, 24, 30, 36\n")
        f.write("- exit.crossroads.start_len: 1, 2, 3\n\n")
        f.write(df_sorted.to_markdown(index=False))

    print()
    print("=" * 90)
    print("DONE")
    print(f"Generated configs: {GENERATED_CONFIG_DIR}")
    print(f"Summary CSV:       {csv_path}")
    print(f"Summary MD:        {md_path}")
    print("=" * 90)
    print()
    print(df_sorted.to_string(index=False))


if __name__ == "__main__":
    main()
