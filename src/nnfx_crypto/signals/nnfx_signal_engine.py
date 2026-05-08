from __future__ import annotations

from typing import Literal

import pandas as pd

from nnfx_crypto.config.schema import StrategyConfig
from nnfx_crypto.indicators.registry import get_indicator
from nnfx_crypto.signals.continuation_filter import is_continuation_trade
from nnfx_crypto.signals.signal_types import ExitSignal, TradeIntent


class NNFXSignalEngine:
    def __init__(
        self,
        config: StrategyConfig | None = None,
        allow_continuation_trades: bool | None = None,
        direction_mode: Literal["long_only", "short_only", "both"] | None = None,
    ) -> None:
        self.config = config
        if allow_continuation_trades is None and config is not None:
            allow_continuation_trades = config.strategy.allow_continuation_trades
        if direction_mode is None and config is not None:
            direction_mode = config.strategy.direction_mode
        self.allow_continuation_trades = bool(allow_continuation_trades)
        self.direction_mode = direction_mode or "both"

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.config is None:
            raise ValueError("compute_indicators requires a StrategyConfig")

        output = df.copy()
        output = get_indicator("atr").compute(output, {"length": self.config.risk.atr_length})
        indicator_configs = [
            self.config.indicators.baseline,
            self.config.indicators.c1,
            self.config.indicators.c2,
            self.config.indicators.volume_or_volatility_filter,
            self.config.indicators.exit,
        ]
        for indicator_config in indicator_configs:
            output = get_indicator(indicator_config.name).compute(output, indicator_config.params)
        return output

    def evaluate_bar(
        self,
        df: pd.DataFrame,
        row_index: int,
        has_open_position: bool = False,
        open_position_side: Literal["long", "short"] | None = None,
    ) -> TradeIntent | None:
        row = df.iloc[row_index]
        timestamp = row.get("timestamp")
        if timestamp is not None:
            timestamp = pd.Timestamp(timestamp)

        if has_open_position:
            return self._evaluate_exit(row, row_index, timestamp, open_position_side)

        return self._evaluate_entry(df, row_index, timestamp)

    def _evaluate_exit(
        self,
        row: pd.Series,
        row_index: int,
        timestamp: pd.Timestamp | None,
        open_position_side: Literal["long", "short"] | None,
    ) -> TradeIntent | None:
        exit_signal = int(row.get("exit_signal", ExitSignal.NONE))
        if open_position_side == "long" and exit_signal == ExitSignal.EXIT_LONG:
            return TradeIntent("exit", "long", "crossroads_exit_long", row_index, timestamp)
        if open_position_side == "short" and exit_signal == ExitSignal.EXIT_SHORT:
            return TradeIntent("exit", "short", "crossroads_exit_short", row_index, timestamp)
        return None

    def _evaluate_entry(
        self,
        df: pd.DataFrame,
        row_index: int,
        timestamp: pd.Timestamp | None,
    ) -> TradeIntent | None:
        row = df.iloc[row_index]
        long_entry = (
            self.direction_mode in {"long_only", "both"}
            and int(row.get("baseline_signal", 0)) == 1
            and int(row.get("c1_signal", 0)) == 1
            and int(row.get("c2_signal", 0)) == 1
            and bool(row.get("filter_pass_long", False))
        )
        short_entry = (
            self.direction_mode in {"short_only", "both"}
            and int(row.get("baseline_signal", 0)) == -1
            and int(row.get("c1_signal", 0)) == -1
            and int(row.get("c2_signal", 0)) == -1
            and bool(row.get("filter_pass_short", False))
        )

        if long_entry:
            if not self.allow_continuation_trades and is_continuation_trade(df, row_index, "long"):
                return None
            return TradeIntent("entry", "long", "algo5_long_entry", row_index, timestamp)

        if short_entry:
            if not self.allow_continuation_trades and is_continuation_trade(df, row_index, "short"):
                return None
            return TradeIntent("entry", "short", "algo5_short_entry", row_index, timestamp)

        return None
