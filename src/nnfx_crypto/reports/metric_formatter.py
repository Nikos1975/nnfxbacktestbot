"""Shared metric formatting for report_writer and Streamlit UI.

Rules:
- Counts     → integer with comma separators
- Money/PnL  → 2 dp with comma separators
- Percent    → multiply by 100, show 2 dp + %  (stored as decimal, e.g. 0.45 → 45.00%)
- Ratio      → 2 dp
- None       → "∞" (profit_factor/payoff_ratio with no losses)
- str/dict   → passed through unchanged
"""
from __future__ import annotations

_INT_KEYS: frozenset[str] = frozenset({
    "total_trades", "long_trades", "short_trades", "consecutive_losses",
    "total_executors_with_positions", "max_open_positions_per_pair",
    "max_drawdown_duration_bars", "winning_trades", "losing_trades",
    "breakeven_trades",
})

_MONEY_KEYS: frozenset[str] = frozenset({
    "net_pnl", "max_drawdown", "gross_profit", "gross_loss", "expectancy",
    "average_win", "average_loss", "largest_win", "largest_loss",
    "fees_paid", "slippage_cost", "cost_drag_total",
    "median_trade_pnl", "median_win", "median_loss", "pnl_std",
    "total_volume", "average_trade_duration",
})

_PCT_KEYS: frozenset[str] = frozenset({
    "net_pnl_pct", "max_drawdown_pct", "win_rate", "loss_rate",
    "breakeven_rate", "accuracy",
    "time_in_market", "time_underwater", "buy_and_hold_return",
    "fee_drag_pct", "slippage_drag_pct", "cost_drag_pct_of_profit",
    "monthly_return_mean", "monthly_return_std",
    "positive_month_rate", "worst_month", "best_month",
    "atr_pct",
    "distance_sma_9_pct", "distance_sma_20_pct",
    "distance_sma_50_pct", "distance_sma_200_pct",
    "entry_atr_pct",
    "entry_distance_sma_9_pct", "entry_distance_sma_20_pct",
    "entry_distance_sma_50_pct", "entry_distance_sma_200_pct",
    "exit_atr_pct",
    "exit_distance_sma_9_pct", "exit_distance_sma_20_pct",
    "exit_distance_sma_50_pct", "exit_distance_sma_200_pct",
})

_RATIO_KEYS: frozenset[str] = frozenset({
    "profit_factor", "sharpe_ratio", "sortino_ratio", "payoff_ratio",
    "recovery_factor", "return_over_max_drawdown",
    "exposure_adjusted_return", "underwater_adjusted_return",
    "largest_loss_to_avg_loss", "largest_win_to_avg_win",
    "average_r_multiple", "median_r_multiple",
    "pnl_skew", "pnl_kurtosis",
    "distance_sma_9_atr", "distance_sma_20_atr",
    "distance_sma_50_atr", "distance_sma_200_atr",
    "entry_distance_sma_9_atr", "entry_distance_sma_20_atr",
    "entry_distance_sma_50_atr", "entry_distance_sma_200_atr",
    "exit_distance_sma_9_atr", "exit_distance_sma_20_atr",
    "exit_distance_sma_50_atr", "exit_distance_sma_200_atr",
    "average_pnl",
})

# Keys to completely exclude from human-readable tables (internal/nested)
_SKIP_KEYS: frozenset[str] = frozenset({
    "close_types", "exposure_by_pair", "performance_by_pair",
    "performance_by_timeframe", "breakeven_note",
})

# Human-readable label overrides (fallback is title-cased snake_case)
_LABELS: dict[str, str] = {
    "net_pnl": "Net PnL",
    "net_pnl_pct": "Net PnL %",
    "max_drawdown": "Max Drawdown",
    "max_drawdown_pct": "Max Drawdown %",
    "profit_factor": "Profit Factor",
    "sharpe_ratio": "Sharpe Ratio",
    "sortino_ratio": "Sortino Ratio",
    "win_rate": "Win Rate",
    "loss_rate": "Loss Rate",
    "breakeven_rate": "Breakeven Rate",
    "accuracy": "Accuracy",
    "total_trades": "Total Trades",
    "winning_trades": "Winning Trades",
    "losing_trades": "Losing Trades",
    "breakeven_trades": "Breakeven Trades",
    "long_trades": "Long Trades",
    "short_trades": "Short Trades",
    "consecutive_losses": "Consecutive Losses",
    "time_in_market": "Time in Market",
    "time_underwater": "Time Underwater",
    "average_trade_duration": "Avg Trade Duration (h)",
    "fees_paid": "Fees Paid",
    "slippage_cost": "Slippage Cost",
    "buy_and_hold_return": "Buy & Hold Return",
    "gross_profit": "Gross Profit",
    "gross_loss": "Gross Loss",
    "payoff_ratio": "Payoff Ratio",
    "recovery_factor": "Recovery Factor",
    "return_over_max_drawdown": "Return / Max DD",
    "fee_drag_pct": "Fee Drag %",
    "slippage_drag_pct": "Slippage Drag %",
    "cost_drag_total": "Total Cost Drag",
    "cost_drag_pct_of_profit": "Cost Drag % of Profit",
    "median_trade_pnl": "Median Trade PnL",
    "median_win": "Median Win",
    "median_loss": "Median Loss",
    "pnl_std": "PnL Std Dev",
    "pnl_skew": "PnL Skew",
    "pnl_kurtosis": "PnL Kurtosis",
    "largest_win": "Largest Win",
    "largest_loss": "Largest Loss",
    "largest_win_to_avg_win": "Largest Win / Avg Win",
    "largest_loss_to_avg_loss": "Largest Loss / Avg Loss",
    "average_r_multiple": "Avg R-Multiple",
    "median_r_multiple": "Median R-Multiple",
    "max_drawdown_duration_bars": "Max DD Duration (bars)",
    "exposure_adjusted_return": "Exposure-Adj Return",
    "underwater_adjusted_return": "Underwater-Adj Return",
    "monthly_return_mean": "Monthly Return (mean)",
    "monthly_return_std": "Monthly Return (std)",
    "positive_month_rate": "Positive Month Rate",
    "worst_month": "Worst Month",
    "best_month": "Best Month",
    "total_volume": "Total Volume",
    "expectancy": "Expectancy",
    "max_open_positions_per_pair": "Max Open Positions",
    "total_executors_with_positions": "Total Executors",
    "average_win": "Avg Win",
    "average_loss": "Avg Loss",
}


def human_label(key: str) -> str:
    """Convert a metric key to a human-readable label."""
    return _LABELS.get(key, key.replace("_", " ").title())


def fmt_metric(key: str, value) -> str:
    """Format a single metric value for human-readable display.

    Raw files (JSON/CSV) are never affected — only call this for display output.
    """
    if value is None:
        return "∞"
    if isinstance(value, (dict, list, bool)):
        return str(value)
    if isinstance(value, str):
        return value
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    if key in _INT_KEYS:
        return f"{int(v):,}"
    if key in _MONEY_KEYS:
        return f"{v:,.2f}"
    if key in _PCT_KEYS:
        return f"{v * 100:.2f}%"
    if key in _RATIO_KEYS:
        return f"{v:.2f}"
    # fallback
    if abs(v) >= 1:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def fmt_metrics_dict(metrics: dict) -> list[tuple[str, str]]:
    """Return a list of (human_label, formatted_value) pairs, skipping internal keys."""
    result = []
    for key, value in metrics.items():
        if key in _SKIP_KEYS:
            continue
        if isinstance(value, (dict, list)):
            continue
        result.append((human_label(key), fmt_metric(key, value)))
    return result
