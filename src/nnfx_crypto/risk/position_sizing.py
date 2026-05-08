from __future__ import annotations


def size_position(account_equity: float, risk_per_trade_pct: float, stop_distance: float) -> float:
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")
    risk_amount = account_equity * risk_per_trade_pct
    return risk_amount / stop_distance
