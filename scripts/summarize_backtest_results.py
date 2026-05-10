import argparse
import json
from pathlib import Path
import pandas as pd
import yaml

def compute_robustness_score(metrics: dict) -> float:
    trades = metrics.get("total_trades", 0)
    if trades < 30:
        return -9999.0  # Heavily penalize statistically insignificant samples
        
    net_pnl_pct = metrics.get("net_pnl_pct", 0.0)
    profit_factor = metrics.get("profit_factor", 0.0)
    recovery_factor = metrics.get("recovery_factor", 0.0)
    max_drawdown_pct = abs(metrics.get("max_drawdown_pct", 0.0))
    time_underwater = metrics.get("time_underwater", 0.0)
    cost_drag_pct = metrics.get("cost_drag_pct_of_profit", 0.0)
    
    score = (
        (net_pnl_pct * 10.0) +
        (profit_factor * 2.0) +
        (recovery_factor * 2.0) -
        (max_drawdown_pct * 20.0) -
        (time_underwater * 5.0) -
        (cost_drag_pct * 5.0)
    )
    return float(score)

def get_indicator_summary(config: dict, role: str) -> str:
    inds = config.get("indicators", {})
    ind = inds.get(role, {})
    name = ind.get("name", "none")
    params = ind.get("params", {})
    if not params:
        return name
    param_str = ",".join(f"{k}={v}" for k, v in params.items())
    return f"{name}({param_str})"

def main():
    parser = argparse.ArgumentParser(description="Summarize backtest runs and generate top-20 lists.")
    parser.add_argument("--results-dir", default="results/nnfx_crypto/backtests", help="Path to backtest results directory")
    parser.add_argument("--output-dir", default="results/nnfx_crypto/summary", help="Path to output summary directory")
    args = parser.parse_args()
    
    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not results_dir.exists():
        print(f"Directory {results_dir} does not exist. No runs to summarize.")
        return
        
    runs = []
    
    for run_path in results_dir.iterdir():
        if not run_path.is_dir():
            continue
            
        metrics_file = run_path / "metrics.json"
        config_file = run_path / "resolved_config.yml"
        
        if not metrics_file.exists():
            continue
            
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception as e:
            print(f"Error reading metrics for {run_path.name}: {e}")
            continue
            
        config = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            except Exception:
                pass
                
        row = {
            "run_id": run_path.name,
            "strategy_name": config.get("strategy", {}).get("name", "unknown"),
            "trading_pair": config.get("market", {}).get("trading_pair", "unknown"),
            "timeframe": config.get("market", {}).get("timeframe", "unknown"),
            "baseline": get_indicator_summary(config, "baseline"),
            "c1": get_indicator_summary(config, "c1"),
            "c2": get_indicator_summary(config, "c2"),
            "volume_filter": get_indicator_summary(config, "volume_or_volatility_filter"),
            "exit": get_indicator_summary(config, "exit"),
            "atr_length": config.get("risk", {}).get("atr_length", 0),
            
            "net_pnl": metrics.get("net_pnl", 0.0),
            "net_pnl_pct": metrics.get("net_pnl_pct", 0.0),
            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0.0),
            "profit_factor": metrics.get("profit_factor", 0.0),
            "expectancy": metrics.get("expectancy", 0.0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
            "sortino_ratio": metrics.get("sortino_ratio", 0.0),
            "win_rate": metrics.get("win_rate", 0.0),
            "total_trades": metrics.get("total_trades", 0),
            "time_in_market": metrics.get("time_in_market", 0.0),
            "time_underwater": metrics.get("time_underwater", 0.0),
            "fees_paid": metrics.get("fees_paid", 0.0),
            "slippage_cost": metrics.get("slippage_cost", 0.0),
            "recovery_factor": metrics.get("recovery_factor", 0.0),
            "payoff_ratio": metrics.get("payoff_ratio", 0.0),
            "exposure_adjusted_return": metrics.get("exposure_adjusted_return", 0.0),
            "robustness_score": compute_robustness_score(metrics)
        }
        runs.append(row)
        
    if not runs:
        print("No valid runs found.")
        return
        
    df = pd.DataFrame(runs)
    df.to_csv(output_dir / "all_runs_summary.csv", index=False)
    
    # Generate Top 20 lists
    df_robust = df.sort_values("robustness_score", ascending=False).head(20)
    df_robust.to_csv(output_dir / "top_20_by_robustness.csv", index=False)
    
    df_pnl = df.sort_values("net_pnl", ascending=False).head(20)
    df_pnl.to_csv(output_dir / "top_20_by_net_pnl.csv", index=False)
    
    df_pf = df.sort_values("profit_factor", ascending=False).head(20)
    df_pf.to_csv(output_dir / "top_20_by_profit_factor.csv", index=False)
    
    df_rf = df.sort_values("recovery_factor", ascending=False).head(20)
    df_rf.to_csv(output_dir / "top_20_by_recovery_factor.csv", index=False)
    
    print(f"Summarized {len(runs)} runs.")
    print(f"Output saved to {output_dir}")

if __name__ == "__main__":
    main()
