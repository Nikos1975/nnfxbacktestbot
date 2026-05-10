import yaml
import pandas as pd
from pathlib import Path
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.backtest.event_backtester import EventBacktester

def run_eth_4h_diagnostic():
    template_path = Path("configs/nnfx_crypto/algo5_cross_roads_btc_4h.yml")
    output_root = Path("results/nnfx_crypto/eth_4h_zlmacd_diagnostic")
    output_root.mkdir(parents=True, exist_ok=True)
    
    generated_root = Path("configs/nnfx_crypto/generated/eth_4h_zlmacd_diagnostic")
    generated_root.mkdir(parents=True, exist_ok=True)

    with open(template_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    # Corrected Settings for ETH-USDT 4h ZL-MACD
    # Fast 86, Slow 85, Signal 2
    zlmacd_params = {
        "fast_length": 86,
        "slow_length": 85,
        "signal_length": 2,
        "source": "close"
    }

    variants = [
        ("A", "none", {}),
        ("B", "rvol", {"length": 20, "threshold": 1.0})
    ]

    results = []

    for label, filter_name, filter_params in variants:
        print(f"Running ETH-USDT 4h Variant {label}...")
        v_data = yaml.safe_load(yaml.safe_dump(config_data))
        
        v_data["strategy"]["name"] = f"eth_4h_zlmacd_diag_{label}"
        v_data["market"]["trading_pair"] = "ETH-USDT"
        v_data["market"]["timeframe"] = "4h"
        v_data["data"]["path"] = "data/nnfx_crypto/processed/ETH-USDT_4h.csv"
        v_data["data"]["start"] = "2018-01-01"
        v_data["data"]["end"] = "2026-05-09"
        
        v_data["indicators"]["c1"] = {"name": "zero_lag_macd", "params": zlmacd_params}
        v_data["indicators"]["c2"] = {"name": "crossroads", "params": {"lookback_period": 24, "source": "close"}}
        v_data["indicators"]["volume_or_volatility_filter"] = {"name": filter_name, "params": filter_params}
        v_data["indicators"]["exit"] = {"name": "crossroads", "params": {"lookback_period": 24, "source": "close"}}
        
        # Risk settings from robust candidate style (1.25 SL)
        v_data["risk"]["stop_loss_atr_multiplier"] = 1.25
        v_data["risk"]["tp1_atr_multiplier"] = 1.0
        
        config_filename = f"eth_4h_zlmacd_{label}.yml"
        config_path = generated_root / config_filename
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(v_data, f)
            
        config = load_strategy_config(config_path)
        tester = EventBacktester(config, output_root=output_root)
        backtest_result = tester.run()
        
        metrics = backtest_result.metrics
        metrics["Variant"] = label
        metrics["Filter"] = filter_name
        metrics["Run ID"] = backtest_result.run_dir.name
        metrics["Report path"] = f"./{backtest_result.run_dir.name}/report.html"
        
        results.append(metrics)

    # Summary
    df = pd.DataFrame(results)
    df.to_csv(output_root / "eth_4h_zlmacd_diagnostic_summary.csv", index=False)
    
    md_content = "# ETH-USDT 4h Zero-Lag MACD Diagnostic\n\n"
    md_content += "## Summary Table\n"
    md_content += df[["Variant", "Filter", "net_pnl_pct", "max_drawdown_pct", "profit_factor", "total_trades"]].to_markdown(index=False)
    md_content += "\n\n## Details\n"
    for res in results:
        md_content += f"- **Variant {res['Variant']}**: [Report]({res['Report path']})\n"
        
    with open(output_root / "eth_4h_zlmacd_diagnostic_summary.md", "w", encoding="utf-8") as f:
        f.write(md_content)

if __name__ == "__main__":
    run_eth_4h_diagnostic()
