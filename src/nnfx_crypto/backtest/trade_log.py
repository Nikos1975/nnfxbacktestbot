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
    
    # Entry Context
    entry_sma_9: float = 0.0
    entry_sma_20: float = 0.0
    entry_sma_50: float = 0.0
    entry_sma_200: float = 0.0
    entry_atr_14: float = 0.0
    entry_atr_pct: float = 0.0
    entry_distance_sma_9_pct: float = 0.0
    entry_distance_sma_20_pct: float = 0.0
    entry_distance_sma_50_pct: float = 0.0
    entry_distance_sma_200_pct: float = 0.0
    entry_distance_sma_9_atr: float = 0.0
    entry_distance_sma_20_atr: float = 0.0
    entry_distance_sma_50_atr: float = 0.0
    entry_distance_sma_200_atr: float = 0.0
    entry_ma_stack_state: str = ""

    # Exit Context
    exit_sma_9: float = 0.0
    exit_sma_20: float = 0.0
    exit_sma_50: float = 0.0
    exit_sma_200: float = 0.0
    exit_atr_14: float = 0.0
    exit_atr_pct: float = 0.0
    exit_distance_sma_9_pct: float = 0.0
    exit_distance_sma_20_pct: float = 0.0
    exit_distance_sma_50_pct: float = 0.0
    exit_distance_sma_200_pct: float = 0.0
    exit_distance_sma_9_atr: float = 0.0
    exit_distance_sma_20_atr: float = 0.0
    exit_distance_sma_50_atr: float = 0.0
    exit_distance_sma_200_atr: float = 0.0
    exit_ma_stack_state: str = ""


TRADE_COLUMNS = [
    "pair", "side", "entry_time", "exit_time", "entry_price", "exit_price",
    "quantity", "pnl", "fees", "slippage", "close_reason",
    "entry_sma_9", "entry_sma_20", "entry_sma_50", "entry_sma_200",
    "entry_atr_14", "entry_atr_pct", 
    "entry_distance_sma_9_pct", "entry_distance_sma_20_pct", "entry_distance_sma_50_pct", "entry_distance_sma_200_pct",
    "entry_distance_sma_9_atr", "entry_distance_sma_20_atr", "entry_distance_sma_50_atr", "entry_distance_sma_200_atr",
    "entry_ma_stack_state",
    "exit_sma_9", "exit_sma_20", "exit_sma_50", "exit_sma_200",
    "exit_atr_14", "exit_atr_pct",
    "exit_distance_sma_9_pct", "exit_distance_sma_20_pct", "exit_distance_sma_50_pct", "exit_distance_sma_200_pct",
    "exit_distance_sma_9_atr", "exit_distance_sma_20_atr", "exit_distance_sma_50_atr", "exit_distance_sma_200_atr",
    "exit_ma_stack_state"
]


def trades_to_frame(trades: list[TradeRecord]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=TRADE_COLUMNS)
    df = pd.DataFrame([asdict(trade) for trade in trades])
    # Reorder columns to match TRADE_COLUMNS exactly
    return df[TRADE_COLUMNS]
