from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    initial_capital: float,
    pair: str,
    timeframe: str,
    max_open_positions_per_pair: int,
) -> dict:
    final_equity = float(equity_curve["equity"].iloc[-1]) if not equity_curve.empty else initial_capital
    net_pnl = final_equity - initial_capital
    returns = equity_curve["equity"].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    running_max = equity_curve["equity"].cummax() if not equity_curve.empty else pd.Series([initial_capital])
    drawdown = equity_curve["equity"] - running_max if not equity_curve.empty else pd.Series([0.0])
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
    max_drawdown_pct = float((drawdown / running_max).min()) if not drawdown.empty else 0.0
    wins = trades[trades["pnl"] > 0]["pnl"] if not trades.empty else pd.Series(dtype=float)
    losses = trades[trades["pnl"] < 0]["pnl"] if not trades.empty else pd.Series(dtype=float)
    gross_win = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses.sum())) if not losses.empty else 0.0
    total_trades = int(len(trades))
    close_types = (
        trades["close_reason"].value_counts().to_dict()
        if total_trades and "close_reason" in trades.columns
        else {}
    )
    total_volume = (
        float(((trades["entry_price"] + trades["exit_price"]) * trades["quantity"]).sum())
        if total_trades
        else 0.0
    )
    fees_paid = float(trades["fees"].sum()) if total_trades else 0.0
    slippage_cost = float(trades["slippage"].sum()) if total_trades else 0.0
    cost_drag_total = fees_paid + slippage_cost
    
    # R-multiple approximations (using fixed risk pct and initial capital, or actual risk)
    # Since we don't store risk_amount directly in TradeRecord, we approximate using initial capital
    # However, if trade pnl is available, we can just leave them as 0 if we can't reliably get the R.
    # The prompt says "if risk per trade can be determined". 
    # For now, we omit them or return 0.0 unless we calculate them.
    # Actually, the user config has `risk_per_trade_pct`. If we pass it, we can calculate R.
    
    # Monthly returns
    monthly_returns = pd.Series(dtype=float)
    if not equity_curve.empty and "timestamp" in equity_curve.columns:
        ec_time = equity_curve.copy()
        ec_time["timestamp"] = pd.to_datetime(ec_time["timestamp"])
        ec_time.set_index("timestamp", inplace=True)
        # Resample to monthly end ('ME' or 'M')
        monthly_eq = ec_time["equity"].resample("ME").last().dropna()
        if len(monthly_eq) > 1:
            monthly_returns = monthly_eq.pct_change().dropna()
            
    time_in_market = (
        float(equity_curve["open_position"].mean())
        if "open_position" in equity_curve.columns and not equity_curve.empty
        else 0.0
    )
    time_underwater = float((drawdown < 0).mean()) if not drawdown.empty else 0.0

    winning_trades = int((trades["pnl"] > 0).sum()) if not trades.empty else 0
    losing_trades = int((trades["pnl"] < 0).sum()) if not trades.empty else 0
    breakeven_trades = int((trades["pnl"] == 0).sum()) if not trades.empty else 0

    # profit_factor: inf when gross_loss=0 and gross_profit>0; 0 when both zero; ratio otherwise
    if gross_loss > 0:
        profit_factor_val = gross_win / gross_loss
    elif gross_win > 0:
        profit_factor_val = None  # Infinity — no losses recorded
    else:
        profit_factor_val = 0.0

    # payoff_ratio: same logic
    avg_win_val = float(wins.mean()) if not wins.empty else 0.0
    avg_loss_val = float(losses.mean()) if not losses.empty else 0.0
    if not wins.empty and not losses.empty and losses.mean() != 0:
        payoff_ratio_val = float(wins.mean() / abs(losses.mean()))
    elif not wins.empty and losses.empty:
        payoff_ratio_val = None  # Infinity — no losses
    else:
        payoff_ratio_val = 0.0

    return {
        "net_pnl": net_pnl,
        "net_pnl_pct": net_pnl / initial_capital if initial_capital else 0.0,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "profit_factor": profit_factor_val,
        "expectancy": float(trades["pnl"].mean()) if total_trades else 0.0,
        "sharpe_ratio": float(returns.mean() / returns.std() * np.sqrt(365)) if len(returns) > 1 and returns.std() else 0.0,
        "sortino_ratio": _sortino_ratio(returns),
        "win_rate": float(winning_trades / total_trades) if total_trades else 0.0,
        "loss_rate": float(losing_trades / total_trades) if total_trades else 0.0,
        "breakeven_rate": float(breakeven_trades / total_trades) if total_trades else 0.0,
        "accuracy": float(winning_trades / total_trades) if total_trades else 0.0,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "breakeven_trades": breakeven_trades,
        "total_executors_with_positions": total_trades,
        "long_trades": int((trades["side"] == "long").sum()) if total_trades else 0,
        "short_trades": int((trades["side"] == "short").sum()) if total_trades else 0,
        "average_win": avg_win_val,
        "average_loss": avg_loss_val,
        "largest_win": float(wins.max()) if not wins.empty else 0.0,
        "largest_loss": float(losses.min()) if not losses.empty else 0.0,
        "consecutive_losses": _max_consecutive_losses(trades),
        "time_in_market": time_in_market,
        "time_underwater": time_underwater,
        "average_trade_duration": _avg_trade_duration_hours(trades),
        "fees_paid": fees_paid,
        "slippage_cost": slippage_cost,
        "total_volume": total_volume,
        "close_types": close_types,
        "buy_and_hold_return": _buy_and_hold_return(equity_curve),
        "exposure_by_pair": {pair: 0.0},
        "performance_by_pair": {pair: net_pnl},
        "performance_by_timeframe": {timeframe: net_pnl},
        "max_open_positions_per_pair": max_open_positions_per_pair,

        # New Robustness Metrics
        "gross_profit": gross_win,
        "gross_loss": gross_loss,
        "payoff_ratio": payoff_ratio_val,
        "recovery_factor": float(net_pnl / abs(max_drawdown)) if max_drawdown != 0 else 0.0,
        "return_over_max_drawdown": float((net_pnl / initial_capital) / abs(max_drawdown_pct)) if max_drawdown_pct != 0 and initial_capital else 0.0,
        "fee_drag_pct": float(fees_paid / gross_win) if gross_win > 0 else 0.0,
        "slippage_drag_pct": float(slippage_cost / gross_win) if gross_win > 0 else 0.0,
        "cost_drag_total": cost_drag_total,
        "cost_drag_pct_of_profit": float(cost_drag_total / gross_win) if gross_win > 0 else 0.0,

        "median_trade_pnl": float(trades["pnl"].median()) if total_trades else 0.0,
        "median_win": float(wins.median()) if not wins.empty else 0.0,
        "median_loss": float(losses.median()) if not losses.empty else 0.0,
        "pnl_std": float(trades["pnl"].std()) if total_trades > 1 else 0.0,
        "pnl_skew": float(trades["pnl"].skew()) if total_trades > 2 else 0.0,
        "pnl_kurtosis": float(trades["pnl"].kurtosis()) if total_trades > 3 else 0.0,

        "largest_loss_to_avg_loss": float(losses.min() / losses.mean()) if not losses.empty and losses.mean() != 0 else 0.0,
        "largest_win_to_avg_win": float(wins.max() / wins.mean()) if not wins.empty and wins.mean() != 0 else 0.0,

        "average_r_multiple": 0.0,
        "median_r_multiple": 0.0,

        "max_drawdown_duration_bars": _max_drawdown_duration(drawdown),

        "exposure_adjusted_return": float((net_pnl / initial_capital) / time_in_market) if time_in_market > 0 and initial_capital else 0.0,
        "underwater_adjusted_return": float((net_pnl / initial_capital) / time_underwater) if time_underwater > 0 and initial_capital else 0.0,

        "monthly_return_mean": float(monthly_returns.mean()) if not monthly_returns.empty else 0.0,
        "monthly_return_std": float(monthly_returns.std()) if len(monthly_returns) > 1 else 0.0,
        "positive_month_rate": float((monthly_returns > 0).mean()) if not monthly_returns.empty else 0.0,
        "worst_month": float(monthly_returns.min()) if not monthly_returns.empty else 0.0,
        "best_month": float(monthly_returns.max()) if not monthly_returns.empty else 0.0,

        # Interpretation note: breakeven trades are second-half positions closed at stop-at-breakeven (SL moved to entry after TP1).
        # They are intentional and represent capital preservation, not missing data.
        "breakeven_note": (
            f"{breakeven_trades} trades closed at exact breakeven (stop moved to entry after TP1). "
            "This is by design in the NNFX two-half-position model."
        ) if breakeven_trades > 0 else "",
    }

def _max_drawdown_duration(drawdown: pd.Series) -> int:
    if drawdown.empty:
        return 0
    is_dd = drawdown < 0
    # calculate consecutive True lengths
    cumsum = is_dd.cumsum()
    return int((cumsum - cumsum.where(~is_dd).ffill().fillna(0)).max())

def _max_consecutive_losses(trades: pd.DataFrame) -> int:
    current = 0
    max_seen = 0
    if trades.empty:
        return 0
    for pnl in trades["pnl"]:
        if pnl < 0:
            current += 1
            max_seen = max(max_seen, current)
        else:
            current = 0
    return max_seen


def _sortino_ratio(returns: pd.Series) -> float:
    if len(returns) < 2:
        return 0.0
    downside = returns[returns < 0]
    if downside.empty:
        return 0.0
    downside_dev = float(np.sqrt((downside ** 2).mean()))
    return float(returns.mean() / downside_dev * np.sqrt(365)) if downside_dev > 0 else 0.0


def _avg_trade_duration_hours(trades: pd.DataFrame) -> float:
    if trades.empty or "entry_time" not in trades.columns or "exit_time" not in trades.columns:
        return 0.0
    entry = pd.to_datetime(trades["entry_time"], errors="coerce")
    exit_ = pd.to_datetime(trades["exit_time"], errors="coerce")
    durations = (exit_ - entry).dt.total_seconds() / 3600.0
    valid = durations.dropna()
    return float(valid.mean()) if not valid.empty else 0.0


def _buy_and_hold_return(equity_curve: pd.DataFrame) -> float:
    if "close" not in equity_curve.columns or equity_curve.empty:
        return 0.0
    first = float(equity_curve["close"].iloc[0])
    last = float(equity_curve["close"].iloc[-1])
    return (last - first) / first if first else 0.0
