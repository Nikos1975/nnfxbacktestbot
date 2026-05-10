from pathlib import Path

from .metric_formatter import fmt_metric, human_label


def write_summary_md(metrics: dict, path: str | Path) -> None:
    output = Path(path)
    lines = ["# Backtest Summary\n"]
    # Key primary metrics for the summary file
    summary_keys = ["net_pnl", "net_pnl_pct", "max_drawdown", "max_drawdown_pct", "profit_factor", "sharpe_ratio", "total_trades"]
    for k in summary_keys:
        if k in metrics:
            lines.append(f"- {human_label(k)}: {fmt_metric(k, metrics[k])}")
    
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report_html(metrics: dict, path: str | Path, indicator_metadata: dict | None = None) -> None:
    run_dir = Path(path).parent
    settings_html = _render_run_settings_html(run_dir)
    
    rows = "\n".join(
        f"<tr><th>{human_label(key)}</th><td>{fmt_metric(key, value)}</td></tr>"
        for key, value in metrics.items()
        if not isinstance(value, (dict, list))
    )
    
    close_type_rows = _dict_rows(metrics.get("close_types", {}))
    # MA Distance Table
    ma_distance_table = ""
    dist_csv = run_dir / "ma_distance_analysis.csv"
    if dist_csv.exists():
        import pandas as pd
        try:
            df = pd.read_csv(dist_csv)
            # Only show buckets with trades
            df_filtered = df[df["trade_count"] > 0]
            if not df_filtered.empty:
                ma_distance_table = "<h2>MA Distance Analysis (Non-Zero Buckets)</h2>\n" + df_filtered.to_html(index=False)
        except Exception:
            pass

    Path(path).write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>NNFX Backtest</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;line-height:1.5;color:#333;}"
        "table{border-collapse:collapse;margin-bottom:24px;}th,td{border:1px solid #ccc;padding:8px 12px}"
        "th{text-align:left;background:#f6f6f6}h1,h2{color:#003366}</style></head><body>"
        "<h1>NNFX Backtest Report</h1>"
        "<h2>Summary Performance</h2>"
        f"<table>{rows}</table>"
        f"{settings_html}"
        "<h2>Close Types</h2>"
        f"<table><tr><th>Type</th><th>Count</th></tr>{close_type_rows}</table>"
        f"{ma_distance_table}"
        "<h2>Charts</h2>"
        "<div style='margin-bottom:20px;'><img src='chart_price_signals.png' alt='Price chart' style='max-width:100%; border:1px solid #eee;'></div>"
        "<div><img src='chart_equity_curve.png' alt='Equity chart' style='max-width:100%; border:1px solid #eee;'></div>"
        "</body></html>",
        encoding="utf-8",
    )


def _render_run_settings_html(result_dir: Path) -> str:
    """Load settings from JSON or YAML and return HTML string."""
    import json
    import yaml
    
    data = None
    json_path = result_dir / "run_settings_summary.json"
    config_path = result_dir / "resolved_config.yml"
    
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    if not data and config_path.exists():
        # Fallback: manually construct enough for the tables
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            data = {
                "identity": {
                    "run_id": result_dir.name,
                    "strategy_name": config.get("strategy", {}).get("name"),
                    "trading_pair": config.get("market", {}).get("trading_pair"),
                    "timeframe": config.get("market", {}).get("timeframe"),
                    "data_path": config.get("data", {}).get("path"),
                    "data_start": config.get("data", {}).get("start"),
                    "data_end": config.get("data", {}).get("end"),
                },
                "indicators": {
                    role: {"name": ind.get("name"), "params": ind.get("params", {})}
                    for role, ind in config.get("indicators", {}).items()
                    if isinstance(ind, dict)
                },
                "risk": config.get("risk", {}),
                "execution": config.get("execution", {}),
                "metadata": config.get("indicator_metadata", {})
            }
        except Exception:
            return "<!-- Error loading settings -->"

    if not data:
        return ""

    html = ["<h2>Run Settings</h2>"]
    
    # A. Identity
    id_data = data.get("identity", {})
    id_rows = "\n".join(f"<tr><th>{k.replace('_', ' ').title()}</th><td>{v}</td></tr>" for k, v in id_data.items() if v)
    html.append("<h3>A. Run Identity</h3>")
    html.append(f"<table>{id_rows}</table>")
    
    # B. Indicators
    html.append("<h3>B. Indicator Stack</h3>")
    ind_rows = []
    for role, ind in data.get("indicators", {}).items():
        params = ind.get("params", {})
        p_str = ", ".join(f"{pk}={pv}" for pk, pv in params.items()) if params else "none"
        ind_rows.append(f"<tr><td>{role.replace('_', ' ').title()}</td><td>{ind.get('name')}</td><td>{p_str}</td></tr>")
    html.append("<table><tr><th>Role</th><th>Indicator</th><th>Parameters</th></tr>" + "\n".join(ind_rows) + "</table>")
    
    # C. Risk
    risk_data = data.get("risk", {})
    risk_rows = "\n".join(f"<tr><th>{k.replace('_', ' ').title()}</th><td>{v}</td></tr>" for k, v in risk_data.items())
    html.append("<h3>C. Risk Settings</h3>")
    html.append(f"<table>{risk_rows}</table>")
    
    # D. Execution
    exec_data = data.get("execution", {})
    exec_rows = "\n".join(f"<tr><th>{k.replace('_', ' ').title()}</th><td>{v}</td></tr>" for k, v in exec_data.items())
    html.append("<h3>D. Execution Settings</h3>")
    html.append(f"<table>{exec_rows}</table>")
    
    # E. Metadata
    metadata = data.get("metadata", {})
    if metadata:
        html.append("<h3>E. Indicator Source Status</h3>")
        meta_rows = []
        for role, meta in metadata.items():
            meta_rows.append(
                f"<tr><td>{role}</td><td>{meta.get('status', '')}</td>"
                f"<td>{meta.get('source_type', '')}</td><td>{meta.get('source_path', '')}</td>"
                f"<td>{meta.get('notes', '')}</td></tr>"
            )
        html.append("<table><tr><th>Role</th><th>Status</th><th>Source Type</th><th>Source Path</th><th>Notes</th></tr>" + "\n".join(meta_rows) + "</table>")
        
    return "\n".join(html)


def _dict_rows(values: dict) -> str:
    if not values:
        return "<tr><td>none</td><td>0</td></tr>"
    return "\n".join(f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in values.items())

