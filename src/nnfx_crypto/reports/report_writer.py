from __future__ import annotations

from pathlib import Path


def write_summary_md(metrics: dict, path: str | Path) -> None:
    output = Path(path)
    output.write_text(
        "# Backtest Summary\n\n"
        f"- Net PnL: {metrics['net_pnl']:.2f}\n"
        f"- Net PnL %: {metrics['net_pnl_pct']:.4f}\n"
        f"- Max Drawdown: {metrics['max_drawdown']:.2f}\n"
        f"- Max Drawdown %: {metrics['max_drawdown_pct']:.4f}\n"
        f"- Profit Factor: {metrics['profit_factor']:.4f}\n"
        f"- Sharpe Ratio: {metrics['sharpe_ratio']:.4f}\n"
        f"- Total Trades: {metrics['total_trades']}\n",
        encoding="utf-8",
    )


def write_report_html(metrics: dict, path: str | Path, indicator_metadata: dict | None = None) -> None:
    rows = "\n".join(
        f"<tr><th>{key}</th><td>{value}</td></tr>"
        for key, value in metrics.items()
        if not isinstance(value, dict)
    )
    indicator_rows = _indicator_rows(indicator_metadata or {})
    close_type_rows = _dict_rows(metrics.get("close_types", {}))
    Path(path).write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>NNFX Backtest</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px}"
        "table{border-collapse:collapse}th,td{border:1px solid #ccc;padding:6px 10px}"
        "th{text-align:left;background:#f6f6f6}</style></head><body>"
        "<h1>NNFX Backtest Report</h1>"
        f"<table>{rows}</table>"
        "<h2>Indicator Source Status</h2>"
        f"<table><tr><th>Role</th><th>Name</th><th>Status</th><th>Source</th><th>Notes</th></tr>{indicator_rows}</table>"
        "<h2>Close Types</h2>"
        f"<table><tr><th>Type</th><th>Count</th></tr>{close_type_rows}</table>"
        "<h2>Charts</h2>"
        "<img src='chart_price_signals.png' alt='Price chart' style='max-width:100%'>"
        "<img src='chart_equity_curve.png' alt='Equity chart' style='max-width:100%'>"
        "</body></html>",
        encoding="utf-8",
    )


def _indicator_rows(indicator_metadata: dict) -> str:
    rows = []
    for role, metadata in indicator_metadata.items():
        rows.append(
            "<tr>"
            f"<td>{role}</td>"
            f"<td>{metadata.get('name', '')}</td>"
            f"<td>{metadata.get('status', '')}</td>"
            f"<td>{metadata.get('source_type', '')}</td>"
            f"<td>{metadata.get('notes', '')}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _dict_rows(values: dict) -> str:
    if not values:
        return "<tr><td>none</td><td>0</td></tr>"
    return "\n".join(f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in values.items())
