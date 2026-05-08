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
    return {
        "net_pnl": net_pnl,
        "net_pnl_pct": net_pnl / initial_capital if initial_capital else 0.0,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "profit_factor": gross_win / gross_loss if gross_loss else 0.0,
        "expectancy": float(trades["pnl"].mean()) if total_trades else 0.0,
        "sharpe_ratio": float(returns.mean() / returns.std() * np.sqrt(365)) if len(returns) > 1 and returns.std() else 0.0,
        "sortino_ratio": 0.0,
        "win_rate": float((trades["pnl"] > 0).mean()) if total_trades else 0.0,
        "accuracy": float((trades["pnl"] > 0).mean()) if total_trades else 0.0,
        "total_trades": total_trades,
        "total_executors_with_positions": total_trades,
        "long_trades": int((trades["side"] == "long").sum()) if total_trades else 0,
        "short_trades": int((trades["side"] == "short").sum()) if total_trades else 0,
        "average_win": float(wins.mean()) if not wins.empty else 0.0,
        "average_loss": float(losses.mean()) if not losses.empty else 0.0,
        "largest_win": float(wins.max()) if not wins.empty else 0.0,
        "largest_loss": float(losses.min()) if not losses.empty else 0.0,
        "consecutive_losses": _max_consecutive_losses(trades),
        "time_in_market": (
            float(equity_curve["open_position"].mean())
            if "open_position" in equity_curve.columns and not equity_curve.empty
            else 0.0
        ),
        "time_underwater": float((drawdown < 0).mean()) if not drawdown.empty else 0.0,
        "average_trade_duration": 0.0,
        "fees_paid": float(trades["fees"].sum()) if total_trades else 0.0,
        "slippage_cost": float(trades["slippage"].sum()) if total_trades else 0.0,
        "total_volume": total_volume,
        "close_types": close_types,
        "buy_and_hold_return": _buy_and_hold_return(equity_curve),
        "exposure_by_pair": {pair: 0.0},
        "performance_by_pair": {pair: net_pnl},
        "performance_by_timeframe": {timeframe: net_pnl},
        "max_open_positions_per_pair": max_open_positions_per_pair,
    }


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


def _buy_and_hold_return(equity_curve: pd.DataFrame) -> float:
    if "close" not in equity_curve.columns or equity_curve.empty:
        return 0.0
    first = float(equity_curve["close"].iloc[0])
    last = float(equity_curve["close"].iloc[-1])
    return (last - first) / first if first else 0.0
