from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

import pandas as pd


class SignalState(IntEnum):
    SHORT = -1
    NEUTRAL = 0
    LONG = 1


class ExitSignal(IntEnum):
    EXIT_LONG = -1
    NONE = 0
    EXIT_SHORT = 1


@dataclass(frozen=True)
class TradeIntent:
    action: Literal["entry", "exit"]
    side: Literal["long", "short"]
    reason: str
    index: int
    timestamp: pd.Timestamp | None = None
