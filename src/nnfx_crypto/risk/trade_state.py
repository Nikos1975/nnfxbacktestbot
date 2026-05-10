from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class OpenTrade:
    pair: str
    side: Literal["long", "short"]
    entry_index: int
    entry_price: float
    quantity: float
    stop_price: float
    tp1_price: float
    entry_time: str | None = None
    first_half_closed: bool = False
    closed: bool = False
    entry_context: dict | None = None

    @classmethod
    def open_long(
        cls,
        pair: str,
        entry_index: int,
        entry_price: float,
        quantity: float,
        stop_price: float,
        tp1_price: float,
        entry_time: str | None = None,
        entry_context: dict | None = None,
    ) -> "OpenTrade":
        return cls(pair, "long", entry_index, entry_price, quantity, stop_price, tp1_price, entry_time, False, False, entry_context)

    @classmethod
    def open_short(
        cls,
        pair: str,
        entry_index: int,
        entry_price: float,
        quantity: float,
        stop_price: float,
        tp1_price: float,
        entry_time: str | None = None,
        entry_context: dict | None = None,
    ) -> "OpenTrade":
        return cls(pair, "short", entry_index, entry_price, quantity, stop_price, tp1_price, entry_time, False, False, entry_context)

    @property
    def remaining_quantity(self) -> float:
        if self.first_half_closed:
            return self.quantity / 2.0
        return self.quantity

    def apply_high_low(
        self,
        high: float,
        low: float,
        move_stop_to_breakeven: bool,
        intrabar_priority: Literal["stop_loss", "take_profit"] = "stop_loss",
    ) -> list[str]:
        events: list[str] = []
        if self.closed:
            return events

        stop_hit = low <= self.stop_price if self.side == "long" else high >= self.stop_price
        tp1_hit = high >= self.tp1_price if self.side == "long" else low <= self.tp1_price
        if stop_hit and tp1_hit and intrabar_priority == "take_profit":
            stop_hit = False

        if stop_hit:
            self.closed = True
            events.append("stop")
            return events

        if tp1_hit and not self.first_half_closed:
            self.first_half_closed = True
            events.append("tp1")
            if move_stop_to_breakeven:
                self.stop_price = self.entry_price
        return events
