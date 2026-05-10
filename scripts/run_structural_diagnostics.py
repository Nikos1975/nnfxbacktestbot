import yaml
import pandas as pd
from pathlib import Path
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.backtest.event_backtester import EventBacktester

def run_diagnostics():
    base_config_path = Path("configs/nnfx_crypto/algo5_cross_roads_btc_1d_best_current.yml")
    output_root = Path("results/nnfx_crypto/structural_diagnostics")
    output_root.mkdir(parents=True, exist_ok=True)
    
    generated_root = Path("configs/nnfx_crypto/generated/structural_diagnostics")
    generated_root.mkdir(parents=True, exist_ok=True)

    with open(base_config_path, "r", encoding="utf-8") as f:
        base_data = yaml.safe_load(f)

    variants = [
        ("A", "both", False, True),
        ("B", "both", False, False),
        ("C", "long_only", False, True),
        ("D", "long_only", False, False),
        ("E", "long_only", True, True),
        ("F", "long_only", True, False),
    ]

    results = []

    for label, dir_mode, allow_cont, filter_enabled in variants:
        print(f"Running Variant {label}...")
        config_data = yaml.safe_load(yaml.safe_dump(base_data)) # Deep copy
        
        config_data["strategy"]["direction_mode"] = dir_mode
        config_data["strategy"]["allow_continuation_trades"] = allow_cont
        
        if not filter_enabled:
            config_data["indicators"]["volume_or_volatility_filter"] = {"name": "none", "params": {}}
        
        config_filename = f"variant_{label}.yml"
        config_path = generated_root / config_filename
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)
            
        # Run Backtest
        config = load_strategy_config(config_path)
        tester = EventBacktester(config, output_root=output_root)
        backtest_result = tester.run()
        
        metrics = backtest_result.metrics
        metrics["Variant"] = label
        metrics["Run ID"] = backtest_result.run_dir.name
        metrics["direction_mode"] = dir_mode
        metrics["allow_continuation_trades"] = allow_cont
        metrics["volume_filter_enabled"] = filter_enabled
        metrics["Report path"] = f"./{backtest_result.run_dir.name}/report.html"
        metrics["Run settings path"] = f"./{backtest_result.run_dir.name}/run_settings_summary.md"
        results.append(metrics)

    # 1. Create CSV
    df = pd.DataFrame(results)
    cols = [
        "Variant", "Run ID", "direction_mode", "allow_continuation_trades", "volume_filter_enabled",
        "net_pnl_pct", "max_drawdown_pct", "profit_factor", "sharpe_ratio", "sortino_ratio", 
        "win_rate", "total_trades", "time_in_market", "time_underwater", "positive_month_rate",
        "largest_win_to_avg_win", "pnl_kurtosis", "buy_and_hold_return",
        "Report path", "Run settings path"
    ]
    summary_df = df[cols]
    summary_df.to_csv(output_root / "structural_diagnostic_summary.csv", index=False)

    # 2. Create Markdown
    md_lines = [
        "# Structural Diagnostic Summary",
        "\nThis report compares 6 structural variants of the NNFX strategy to isolate the impact of filters and entry logic.",
        "\n## Ranking & Robustness Rule",
        "- Prefer Trades >= 50",
        "- Net PnL % > 100",
        "- Profit Factor > 3",
        "- Max DD % > -25",
        "- Positive Month Rate > 35",
        "- Time Underwater < 90",
        "\n## Comparison Table",
        summary_df.drop(columns=["Report path", "Run settings path"]).to_markdown(index=False),
        "\n## Detailed Variant Links",
    ]
    for res in results:
        md_lines.append(f"- **Variant {res['Variant']}**: [Report]({res['Report path']}) | [Settings]({res['Run settings path']})")

    with open(output_root / "structural_diagnostic_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    run_diagnostics()
