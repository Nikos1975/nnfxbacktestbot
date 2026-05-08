from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class TradeRecord:
    pair: str
    side: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    fees: float
    slippage: float
    close_reason: str


TRADE_COLUMNS = [
    "pair",
    "side",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "quantity",
    "pnl",
    "fees",
    "slippage",
    "close_reason",
]


def trades_to_frame(trades: list[TradeRecord]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=TRADE_COLUMNS)
    return pd.DataFrame([asdict(trade) for trade in trades], columns=TRADE_COLUMNS)
