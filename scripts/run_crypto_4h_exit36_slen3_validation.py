import yaml
import pandas as pd
from pathlib import Path
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.backtest.event_backtester import EventBacktester

def run_validation():
    base_config_path = Path("configs/nnfx_crypto/eth_4h_zlmacd_86_85_2_exit36_slen3_candidate.yml")
    output_root = Path("results/nnfx_crypto/crypto_4h_exit36_slen3_validation")
    output_root.mkdir(parents=True, exist_ok=True)
    
    generated_root = Path("configs/nnfx_crypto/generated/crypto_4h_exit36_slen3_validation")
    generated_root.mkdir(parents=True, exist_ok=True)

    with open(base_config_path, "r", encoding="utf-8") as f:
        base_data = yaml.safe_load(f)

    pairs = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    timeframe = "4h"

    results = []

    for pair in pairs:
        print(f"Validating Candidate on {pair} {timeframe}...")
        
        config_data = yaml.safe_load(yaml.safe_dump(base_data))
        config_data["strategy"]["name"] = f"val_exit36_slen3_{pair}"
        config_data["market"]["trading_pair"] = pair
        config_data["market"]["timeframe"] = timeframe
        
        data_path = f"data/nnfx_crypto/processed/{pair}_{timeframe}.csv"
        config_data["data"]["path"] = data_path
        
        config_filename = f"val_{pair}_{timeframe}.yml"
        config_path = generated_root / config_filename
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)
            
        config = load_strategy_config(config_path)
        tester = EventBacktester(config, output_root=output_root)
        backtest_result = tester.run()
        
        metrics = backtest_result.metrics
        metrics["Trading Pair"] = pair
        metrics["Run ID"] = backtest_result.run_dir.name
        
        # Load trades for extra fields
        trades_path = backtest_result.run_dir / "trades.csv"
        if trades_path.exists():
            trades_df = pd.read_csv(trades_path)
            metrics["Long Trades"] = len(trades_df[trades_df["side"] == "long"]) if not trades_df.empty else 0
            metrics["Short Trades"] = len(trades_df[trades_df["side"] == "short"]) if not trades_df.empty else 0
        else:
            metrics["Long Trades"] = 0
            metrics["Short Trades"] = 0
            
        # Exit breakdown from metrics
        close_types = metrics.get("close_types", {})
        metrics["Stop Loss Exits"] = close_types.get("stop_loss", 0)
        metrics["TP1 Exits"] = close_types.get("tp1", 0)
        metrics["CrossRoads Exit Long"] = close_types.get("crossroads_exit_long", 0)
        metrics["CrossRoads Exit Short"] = close_types.get("crossroads_exit_short", 0)
        metrics["Daily Loss Limit Exits"] = close_types.get("daily_loss_limit", 0)

        metrics["Fees Paid"] = metrics.get("total_fees", 0)
        metrics["Slippage Cost"] = metrics.get("total_slippage", 0)
        metrics["Total Cost Drag"] = metrics["Fees Paid"] + metrics["Slippage Cost"]
        
        # Pass/Fail Check
        passed = (
            metrics.get("net_pnl_pct", 0) > 0 and
            metrics.get("profit_factor", 0) >= 1.3 and
            metrics.get("max_drawdown_pct", 0) > -0.30 and # -30%
            metrics.get("positive_month_rate", 0) >= 0.45 and
            metrics.get("time_underwater", 0) <= 0.985
        )
        metrics["Status"] = "PASS" if passed else "FAIL"
        
        metrics["Report path"] = f"./{backtest_result.run_dir.name}/report.html"
        metrics["Run settings path"] = f"./{backtest_result.run_dir.name}/run_settings_summary.md"
        
        results.append(metrics)

    # Aggregate & Summarize
    df = pd.DataFrame(results)
    df.to_csv(output_root / "crypto_4h_exit36_slen3_validation_summary.csv", index=False)

    md_lines = [
        "# Crypto 4h Candidate Validation Summary",
        "\n## Validation Table",
        df[["Trading Pair", "Status", "net_pnl_pct", "max_drawdown_pct", "profit_factor", "total_trades", "win_rate"]].to_markdown(index=False),
        "\n## Pass/Fail Analysis",
        "Thresholds: PnL > 0, PF >= 1.3, DD > -30%, Positive Month > 45%, Time Underwater < 98.5%",
    ]
    for res in results:
        md_lines.append(f"- **{res['Trading Pair']}**: {res['Status']} | [Report]({res['Report path']})")

    with open(output_root / "crypto_4h_exit36_slen3_validation_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    run_validation()
