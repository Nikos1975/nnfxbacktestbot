from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nnfx_crypto.risk.position_sizing import size_position


@dataclass(frozen=True)
class EntryPlan:
    side: Literal["long", "short"]
    entry_price: float
    stop_price: float
    tp1_price: float
    total_quantity: float
    first_half_quantity: float
    second_half_quantity: float
    stop_distance: float
    tp1_distance: float


@dataclass(frozen=True)
class ATRRiskModel:
    account_equity: float = 10_000.0
    risk_per_trade_pct: float = 0.005
    stop_loss_atr_multiplier: float = 1.25
    tp1_atr_multiplier: float = 1.0

    def plan_entry(self, side: Literal["long", "short"], entry_price: float, atr: float) -> EntryPlan:
        if atr <= 0:
            raise ValueError("atr must be positive")
        stop_distance = atr * self.stop_loss_atr_multiplier
        tp1_distance = atr * self.tp1_atr_multiplier
        quantity = size_position(self.account_equity, self.risk_per_trade_pct, stop_distance)
        if side == "long":
            stop_price = entry_price - stop_distance
            tp1_price = entry_price + tp1_distance
        else:
            stop_price = entry_price + stop_distance
            tp1_price = entry_price - tp1_distance
        return EntryPlan(
            side=side,
            entry_price=entry_price,
            stop_price=stop_price,
            tp1_price=tp1_price,
            total_quantity=quantity,
            first_half_quantity=quantity / 2.0,
            second_half_quantity=quantity / 2.0,
            stop_distance=stop_distance,
            tp1_distance=tp1_distance,
        )
