import yaml
import pandas as pd
from pathlib import Path
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.backtest.event_backtester import EventBacktester

def run_risk_diagnostic():
    base_config_path = Path("configs/nnfx_crypto/generated/eth_4h_zlmacd_diagnostic/eth_4h_zlmacd_A.yml")
    output_root = Path("results/nnfx_crypto/eth_4h_zlmacd_86_85_2_risk_diagnostic")
    output_root.mkdir(parents=True, exist_ok=True)
    
    generated_root = Path("configs/nnfx_crypto/generated/eth_4h_zlmacd_86_85_2_risk_diagnostic")
    generated_root.mkdir(parents=True, exist_ok=True)

    with open(base_config_path, "r", encoding="utf-8") as f:
        base_data = yaml.safe_load(f)

    # 1. Update strategy settings to match current requirement
    # c2 Crossroads lookback 24, source close (already there)
    # volume filter: none (already there)
    
    sl_multipliers = [2.0, 2.5, 3.0]
    tp_multipliers = [1.5, 2.0]
    breakeven_settings = [True, False]

    results = []

    for sl in sl_multipliers:
        for tp in tp_multipliers:
            for be in breakeven_settings:
                label = f"SL{sl}_TP{tp}_BE{str(be).lower()}"
                print(f"Running Risk Variant: {label}...")
                
                config_data = yaml.safe_load(yaml.safe_dump(base_data))
                config_data["strategy"]["name"] = f"eth_risk_diag_{label}"
                config_data["risk"]["stop_loss_atr_multiplier"] = sl
                config_data["risk"]["tp1_atr_multiplier"] = tp
                config_data["risk"]["move_second_half_to_breakeven_after_tp1"] = be
                
                config_filename = f"risk_diag_{label}.yml"
                config_path = generated_root / config_filename
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(config_data, f)
                    
                config = load_strategy_config(config_path)
                tester = EventBacktester(config, output_root=output_root)
                backtest_result = tester.run()
                
                metrics = backtest_result.metrics
                metrics["Run ID"] = backtest_result.run_dir.name
                metrics["stop_loss_atr_multiplier"] = sl
                metrics["tp1_atr_multiplier"] = tp
                metrics["move_second_half_to_breakeven_after_tp1"] = be
                
                # Load trades from CSV for extra fields if available
                trades_path = backtest_result.run_dir / "trades.csv"
                if trades_path.exists():
                    trades_df = pd.read_csv(trades_path)
                    metrics["Long Trades"] = len(trades_df[trades_df["side"] == "long"]) if not trades_df.empty else 0
                    metrics["Short Trades"] = len(trades_df[trades_df["side"] == "short"]) if not trades_df.empty else 0
                else:
                    metrics["Long Trades"] = 0
                    metrics["Short Trades"] = 0
                
                # Close types from metrics
                metrics["Close types"] = str(metrics.get("close_types", {}))

                metrics["Fees Paid"] = metrics.get("total_fees", 0)
                metrics["Slippage Cost"] = metrics.get("total_slippage", 0)
                metrics["Total Cost Drag"] = metrics["Fees Paid"] + metrics["Slippage Cost"]
                
                net_pnl = metrics.get("net_pnl", 0)
                metrics["Cost Drag % of Profit"] = (metrics["Total Cost Drag"] / net_pnl * 100) if net_pnl != 0 else 0
                
                metrics["Report path"] = f"./{backtest_result.run_dir.name}/report.html"
                metrics["Run settings path"] = f"./{backtest_result.run_dir.name}/run_settings_summary.md"
                
                results.append(metrics)

    # Aggregate & Summarize
    df = pd.DataFrame(results)
    df.to_csv(output_root / "eth_4h_zlmacd_86_85_2_risk_summary.csv", index=False)

    md_lines = [
        "# ETH-USDT 4h Risk Diagnostic Summary",
        "\n## Baseline (Old Variant A)",
        "- SL Multiplier: 1.25",
        "- TP1 Multiplier: 1.0",
        "- BE after TP1: True",
        "- Net PnL: 68.71%",
        "- Max DD: -37.48%",
        "- PF: 1.10",
        "- Trades: 1045",
        "- Time Underwater: 98.70%",
        "\n## Comparison Table",
        df[["Run ID", "stop_loss_atr_multiplier", "tp1_atr_multiplier", "move_second_half_to_breakeven_after_tp1", "net_pnl_pct", "max_drawdown_pct", "profit_factor", "total_trades"]].to_markdown(index=False),
        "\n## Robustness Check",
        "Prefer PF > 1.5, Max DD > -30%, Positive Month Rate > 50%.",
        "\n## Details",
    ]
    for res in results:
        md_lines.append(f"- **{res['Run ID']}**: [Report]({res['Report path']})")

    with open(output_root / "eth_4h_zlmacd_86_85_2_risk_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    run_risk_diagnostic()
