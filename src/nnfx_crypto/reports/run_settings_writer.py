import json
import yaml
from pathlib import Path
from typing import Any

def write_run_settings_summary(result_dir: Path) -> None:
    """Read resolved_config.yml and metrics.json from result_dir and write summary files."""
    config_path = result_dir / "resolved_config.yml"
    metrics_path = result_dir / "metrics.json"
    
    if not config_path.exists():
        return

    # 1. Load Data
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception:
        config = {}
        
    metrics = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f) or {}
        except Exception:
            pass

    # 2. Extract Sections
    run_id = result_dir.name
    strategy = config.get("strategy", {})
    market = config.get("market", {})
    data_section = config.get("data", {})
    indicators = config.get("indicators", {})
    risk = config.get("risk", {})
    execution = config.get("execution", {})
    indicator_metadata = config.get("indicator_metadata")

    # 3. Build Structured Data (JSON)
    summary_data = {
        "identity": {
            "run_id": run_id,
            "strategy_name": strategy.get("name"),
            "trading_pair": market.get("trading_pair"),
            "timeframe": market.get("timeframe"),
            "data_path": data_section.get("path"),
            "data_start": data_section.get("start"),
            "data_end": data_section.get("end"),
        },
        "indicators": {},
        "risk": risk,
        "execution": execution,
        "metrics": {},
        "metadata": indicator_metadata if indicator_metadata else {}
    }

    # Indicators mapping
    roles = ["baseline", "c1", "c2", "volume_or_volatility_filter", "exit"]
    for role in roles:
        ind = indicators.get(role, {})
        summary_data["indicators"][role] = {
            "name": ind.get("name", "none"),
            "params": ind.get("params", {})
        }

    # Metrics selection
    metric_keys = [
        "net_pnl", "net_pnl_pct", "max_drawdown", "max_drawdown_pct",
        "profit_factor", "expectancy", "sharpe_ratio", "sortino_ratio",
        "win_rate", "total_trades", "time_in_market", "time_underwater",
        "positive_month_rate", "buy_and_hold_return", "recovery_factor",
        "payoff_ratio", "cost_drag_pct_of_profit", "pnl_skew",
        "pnl_kurtosis", "largest_win_to_avg_win"
    ]
    for k in metric_keys:
        if k in metrics:
            summary_data["metrics"][k] = metrics[k]

    # Write JSON
    json_path = result_dir / "run_settings_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=4)

    # 4. Build Markdown
    md_lines = [
        f"# Run Settings Summary - {run_id}",
        "\n## A. Run Identity",
        f"- **Strategy**: {summary_data['identity']['strategy_name']}",
        f"- **Pair**: {summary_data['identity']['trading_pair']}",
        f"- **Timeframe**: {summary_data['identity']['timeframe']}",
        f"- **Data Path**: {summary_data['identity']['data_path']}",
        f"- **Date Range**: {summary_data['identity']['data_start']} to {summary_data['identity']['data_end']}",
        
        "\n## B. Indicator Settings"
    ]
    
    for role in roles:
        ind = summary_data["indicators"][role]
        name = ind["name"]
        params = ind["params"]
        if params:
            p_str = ", ".join(f"{k}={v}" for k, v in params.items())
            md_lines.append(f"{role}: {name}({p_str})")
            md_lines.append(f"- **{role}**: {name}({p_str})")
        else:
            md_lines.append(f"{role}: {name}")
            md_lines.append(f"- **{role}**: {name}")

    md_lines.append("\n## C. ATR / Risk Settings")
    for k, v in risk.items():
        md_lines.append(f"- **{k}**: {v}")

    md_lines.append("\n## D. Execution Settings")
    for k, v in execution.items():
        md_lines.append(f"- **{k}**: {v}")

    if summary_data["metrics"]:
        md_lines.append("\n## E. Key Metrics")
        
        # Add compact plain lines for specific metrics as requested by tests
        if "net_pnl" in metrics:
            md_lines.append(f"Net PnL: {metrics['net_pnl']:,.2f}")
        if "net_pnl_pct" in metrics:
            md_lines.append(f"Net PnL %: {metrics['net_pnl_pct'] * 100:.2f}%")
        if "total_trades" in metrics:
            md_lines.append(f"Total Trades: {int(metrics['total_trades'])}")

        from nnfx_crypto.reports.metric_formatter import fmt_metric, human_label
        for k in metric_keys:
            if k in metrics:
                md_lines.append(f"- **{human_label(k)}**: {fmt_metric(k, metrics[k])}")

    if summary_data["metadata"]:
        md_lines.append("\n## F. Indicator Metadata")
        for k, meta in summary_data["metadata"].items():
            md_lines.append(f"### {k}")
            for mk, mv in meta.items():
                md_lines.append(f"- **{mk}**: {mv}")

    md_path = result_dir / "run_settings_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
