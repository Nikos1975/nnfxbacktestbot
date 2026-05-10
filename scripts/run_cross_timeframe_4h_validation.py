import yaml
import pandas as pd
from pathlib import Path
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.backtest.event_backtester import EventBacktester

def run_4h_validation():
    candidate_configs = {
        "ptl_exit_robust": "configs/nnfx_crypto/algo5_btc_1d_ptl_exit_robust.yml",
        "zlmacd_c1_balanced": "configs/nnfx_crypto/algo5_btc_1d_zlmacd_c1_balanced.yml",
        "zlmacd_c2_aggressive": "configs/nnfx_crypto/algo5_btc_1d_zlmacd_c2_aggressive.yml"
    }
    
    pairs = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    timeframe = "4h"
    
    output_root = Path("results/nnfx_crypto/cross_timeframe_4h_validation")
    output_root.mkdir(parents=True, exist_ok=True)
    
    generated_root = Path("configs/nnfx_crypto/generated/cross_timeframe_4h_validation")
    generated_root.mkdir(parents=True, exist_ok=True)

    results = []

    for strat_label, base_path in candidate_configs.items():
        with open(base_path, "r", encoding="utf-8") as f:
            base_data = yaml.safe_load(f)
            
        for pair in pairs:
            print(f"Validating {strat_label} on {pair} {timeframe}...")
            
            config_data = yaml.safe_load(yaml.safe_dump(base_data))
            config_data["strategy"]["name"] = f"{strat_label}_4h"
            config_data["market"]["trading_pair"] = pair
            config_data["market"]["timeframe"] = timeframe
            
            data_path = f"data/nnfx_crypto/processed/{pair}_{timeframe}.csv"
            config_data["data"]["path"] = data_path
            
            # Check file for actual start date
            actual_path = Path(r"D:\_projects\trading") / data_path
            if actual_path.exists():
                df_temp = pd.read_csv(actual_path, nrows=1)
                if not df_temp.empty:
                    file_start = df_temp["timestamp"].iloc[0].split(" ")[0] # Just the date
                    # Ensure we don't start before the file
                    if file_start > config_data["data"]["start"]:
                         config_data["data"]["start"] = file_start

            config_filename = f"{strat_label}_{pair}_{timeframe}.yml"
            config_path = generated_root / config_filename
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_data, f)
                
            # Run Backtest
            config = load_strategy_config(config_path)
            tester = EventBacktester(config, output_root=output_root)
            backtest_result = tester.run()
            
            metrics = backtest_result.metrics
            metrics["Strategy Label"] = strat_label
            metrics["Trading Pair"] = pair
            metrics["Timeframe"] = timeframe
            metrics["Run ID"] = backtest_result.run_dir.name
            
            # Extract indicators for summary
            metrics["C1"] = f"{config.indicators.c1.name}({config.indicators.c1.params})"
            metrics["C2"] = f"{config.indicators.c2.name}({config.indicators.c2.params})"
            metrics["Volume Filter"] = f"{config.indicators.volume_or_volatility_filter.name}({config.indicators.volume_or_volatility_filter.params})"
            metrics["Exit"] = f"{config.indicators.exit.name}({config.indicators.exit.params})"
            
            # Additional metrics
            metrics["Fees Paid"] = metrics.get("total_fees", 0)
            metrics["Slippage Cost"] = metrics.get("total_slippage", 0)
            metrics["Total Cost Drag"] = metrics.get("cost_drag_pct_of_profit", 0)
            metrics["Report path"] = f"./{backtest_result.run_dir.name}/report.html"
            metrics["Run settings path"] = f"./{backtest_result.run_dir.name}/run_settings_summary.md"
            
            results.append(metrics)

    # Aggregate & Summarize
    df = pd.DataFrame(results)
    df.to_csv(output_root / "cross_timeframe_4h_validation_summary.csv", index=False)

    md_lines = [
        "# Cross-Timeframe 4h Validation Summary",
        "\n## Comparison Table",
        df.drop(columns=["Report path", "Run settings path", "C1", "C2", "Volume Filter", "Exit"]).to_markdown(index=False),
        "\n## Detailed Results",
    ]
    for res in results:
        md_lines.append(f"- **{res['Strategy Label']} - {res['Trading Pair']}**: [Report]({res['Report path']})")

    with open(output_root / "cross_timeframe_4h_validation_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    run_4h_validation()
