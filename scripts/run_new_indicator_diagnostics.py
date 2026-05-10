import yaml
import pandas as pd
from pathlib import Path
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.backtest.event_backtester import EventBacktester

def run_new_indicator_diagnostics():
    base_config_path = Path("configs/nnfx_crypto/algo5_cross_roads_btc_1d_robust_candidate.yml")
    output_root = Path("results/nnfx_crypto/new_indicator_diagnostics")
    output_root.mkdir(parents=True, exist_ok=True)
    
    generated_root = Path("configs/nnfx_crypto/generated/new_indicator_diagnostics")
    generated_root.mkdir(parents=True, exist_ok=True)

    with open(base_config_path, "r", encoding="utf-8") as f:
        base_data = yaml.safe_load(f)

    # 1D Variants
    variants_1d = {
        "A": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "B": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "rvol", "params": {"length": 20, "threshold": 0.8}}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "C": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "rvol", "params": {"length": 20, "threshold": 1.0}}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "D": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "perfect_trend_line", "params": {"period": 10, "atr_length": 14, "atr_multiplier": 2.0}}},
        "E": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 12, "slow_length": 26, "signal_length": 9}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "F": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 8, "slow_length": 21, "signal_length": 5}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "G": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 53, "slow_length": 3, "signal_length": 57}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "H": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 3, "slow_length": 53, "signal_length": 57}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "I": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "zero_lag_macd", "params": {"fast_length": 12, "slow_length": 26, "signal_length": 9}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "J": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "zero_lag_macd", "params": {"fast_length": 8, "slow_length": 21, "signal_length": 5}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "K": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "zero_lag_macd", "params": {"fast_length": 53, "slow_length": 3, "signal_length": 57}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "L": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "zero_lag_macd", "params": {"fast_length": 3, "slow_length": 53, "signal_length": 57}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "M": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "zero_lag_macd", "params": {"fast_length": 12, "slow_length": 26, "signal_length": 9}}, "filter": {"name": "rvol", "params": {"length": 20, "threshold": 0.8}}, "exit": {"name": "perfect_trend_line", "params": {"period": 10, "atr_length": 14, "atr_multiplier": 2.0}}},
        "N": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 8, "slow_length": 21, "signal_length": 5}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "rvol", "params": {"length": 20, "threshold": 0.8}}, "exit": {"name": "perfect_trend_line", "params": {"period": 10, "atr_length": 14, "atr_multiplier": 2.0}}},
        "O": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 53, "slow_length": 3, "signal_length": 57}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "rvol", "params": {"length": 20, "threshold": 0.8}}, "exit": {"name": "perfect_trend_line", "params": {"period": 10, "atr_length": 14, "atr_multiplier": 2.0}}},
        "P": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 3, "slow_length": 53, "signal_length": 57}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "rvol", "params": {"length": 20, "threshold": 0.8}}, "exit": {"name": "perfect_trend_line", "params": {"period": 10, "atr_length": 14, "atr_multiplier": 2.0}}}
    }

    # 4H Variants
    variants_4h = {
        "4H-A": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "4H-B": {"c1": {"name": "zero_lag_macd", "params": {"fast_length": 2, "slow_length": 86, "signal_length": 85}}, "c2": {"name": "crossroads", "params": {"lookback_period": 24}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}},
        "4H-C": {"c1": {"name": "reflex", "params": {"length": 16}}, "c2": {"name": "zero_lag_macd", "params": {"fast_length": 2, "slow_length": 86, "signal_length": 85}}, "filter": {"name": "none"}, "exit": {"name": "crossroads", "params": {"lookback_period": 24}}}
    }

    results = []

    def run_variant(label, v_conf, tf):
        print(f"Running Variant {label} ({tf})...")
        config_data = yaml.safe_load(yaml.safe_dump(base_data))
        config_data["market"]["timeframe"] = tf
        config_data["data"]["path"] = f"data/nnfx_crypto/processed/BTC-USDT_{tf}.csv"
        
        config_data["indicators"]["c1"] = v_conf["c1"]
        config_data["indicators"]["c2"] = v_conf["c2"]
        config_data["indicators"]["volume_or_volatility_filter"] = v_conf["filter"]
        config_data["indicators"]["exit"] = v_conf["exit"]
        
        config_filename = f"variant_{label}.yml"
        config_path = generated_root / config_filename
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)
            
        config = load_strategy_config(config_path)
        tester = EventBacktester(config, output_root=output_root)
        backtest_result = tester.run()
        
        metrics = backtest_result.metrics
        metrics["Variant"] = label
        metrics["Run ID"] = backtest_result.run_dir.name
        metrics["Timeframe"] = tf
        metrics["c1"] = f"{v_conf['c1']['name']}({v_conf['c1']['params']})"
        metrics["c2"] = f"{v_conf['c2']['name']}({v_conf['c2']['params']})"
        metrics["volume_filter"] = f"{v_conf['filter']['name']}({v_conf['filter']['params']})"
        metrics["exit"] = f"{v_conf['exit']['name']}({v_conf['exit']['params']})"
        metrics["Report path"] = f"./{backtest_result.run_dir.name}/report.html"
        metrics["Run settings path"] = f"./{backtest_result.run_dir.name}/run_settings_summary.md"
        
        # Robustness Score Calculation
        score = 0
        score -= metrics.get("max_drawdown_pct", 0) * 100
        score -= metrics.get("time_underwater", 0) * 100
        score -= metrics.get("pnl_kurtosis", 0)
        score -= metrics.get("largest_win_to_avg_win", 0)
        score += metrics.get("positive_month_rate", 0) * 100
        score += metrics.get("recovery_factor", 0) * 10
        metrics["Robustness Score"] = score
        
        results.append(metrics)

    # Run all
    for label, conf in variants_1d.items():
        run_variant(label, conf, "1d")
    for label, conf in variants_4h.items():
        run_variant(label, conf, "4h")

    # Aggregate & Summarize
    df = pd.DataFrame(results)
    df.to_csv(output_root / "new_indicator_diagnostic_summary.csv", index=False)

    md_lines = [
        "# New Indicator Diagnostic Summary",
        "\n## Comparison Table",
        df.drop(columns=["Report path", "Run settings path", "Robustness Score"]).to_markdown(index=False),
        "\n## Top 5 by Net PnL %",
        df.sort_values("net_pnl_pct", ascending=False).head(5)[["Variant", "net_pnl_pct", "Robustness Score"]].to_markdown(index=False),
        "\n## Top 5 by Robustness Score",
        df.sort_values("Robustness Score", ascending=False).head(5)[["Variant", "net_pnl_pct", "Robustness Score"]].to_markdown(index=False)
    ]
    with open(output_root / "new_indicator_diagnostic_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    run_new_indicator_diagnostics()
