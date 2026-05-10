from __future__ import annotations

from typing import Literal

import numpy as np
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
        
        # 1. Base Market Context Columns
        output["sma_9"] = output["close"].rolling(window=9).mean()
        output["sma_20"] = output["close"].rolling(window=20).mean()
        output["sma_50"] = output["close"].rolling(window=50).mean()
        output["sma_200"] = output["close"].rolling(window=200).mean()
        
        # ATR 14 for context (distinct from risk ATR)
        atr_14_df = get_indicator("atr").compute(output.copy(), {"length": 14})
        output["atr_14"] = atr_14_df["atr"]
        output["atr_pct"] = np.where(output["close"] > 0, output["atr_14"] / output["close"], np.nan)
        
        # Distance columns
        for n in [9, 20, 50, 200]:
            sma_col = f"sma_{n}"
            output[f"distance_sma_{n}_pct"] = np.where(output[sma_col] > 0, (output["close"] - output[sma_col]) / output[sma_col], np.nan)
            output[f"distance_sma_{n}_atr"] = np.where(output["atr_14"] > 0, (output["close"] - output[sma_col]) / output["atr_14"], np.nan)
            
        # Stack state classification
        bull_mask = (output["close"] > output["sma_9"]) & (output["sma_9"] > output["sma_20"]) & (output["sma_20"] > output["sma_50"]) & (output["sma_50"] > output["sma_200"])
        bear_mask = (output["close"] < output["sma_9"]) & (output["sma_9"] < output["sma_20"]) & (output["sma_20"] < output["sma_50"]) & (output["sma_50"] < output["sma_200"])
        output["ma_stack_state"] = np.where(bull_mask, "bull_stack", np.where(bear_mask, "bear_stack", "mixed_stack"))

        # 2. Risk Model ATR
        output = get_indicator("atr").compute(output, {"length": self.config.risk.atr_length})
        
        # 3. Strategy Indicators — Centralized Role Mapping
        # We compute indicators and then explicitly map their internal signal columns
        # to the NNFX role-based columns (baseline_signal, c1_signal, c2_signal, exit_signal).
        
        # Initialize signal columns if they don't exist
        for col in ["baseline_signal", "c1_signal", "c2_signal", "exit_signal"]:
            if col not in output.columns:
                output[col] = 0

        roles = [
            ("baseline", self.config.indicators.baseline),
            ("c1", self.config.indicators.c1),
            ("c2", self.config.indicators.c2),
            ("volume", self.config.indicators.volume_or_volatility_filter),
            ("exit", self.config.indicators.exit),
        ]
        
        for role, indicator_config in roles:
            output = get_indicator(indicator_config.name).compute(output, indicator_config.params)
            self._map_role_signals(output, role, indicator_config.name)
            
        return output

    def _map_role_signals(self, df: pd.DataFrame, role: str, indicator_name: str) -> None:
        """Map indicator-specific signal columns to NNFX role columns."""
        close = df["close"].astype(float)
        
        if role == "baseline":
            # Baseline: usually Price vs Baseline
            val_col = "baseline_value" if "baseline_value" in df.columns else f"{indicator_name}_value"
            if val_col in df.columns:
                val = df[val_col]
                df["baseline_signal"] = np.select(
                    [close > val, close < val], [1, -1], default=0
                ).astype(int)
                df.loc[val.isna(), "baseline_signal"] = 0

        elif role == "c1":
            if indicator_name == "crossroads":
                df["c1_signal"] = df["crossroads_trend"]
            elif indicator_name == "reflex":
                val = df["reflex_value"]
                prev = val.shift(1).fillna(0)
                df["c1_signal"] = np.select(
                    [(val > 0) & (prev <= 0), (val < 0) & (prev >= 0)], [1, -1], default=0
                ).astype(int)
            # Add other C1 mappings here if needed

        elif role == "c2":
            if indicator_name == "crossroads":
                df["c2_signal"] = df["crossroads_trend"]
            # Add other C2 mappings here

        elif role == "exit":
            if indicator_name == "crossroads":
                df["exit_signal"] = df["crossroads_signal"]
            # Add other Exit mappings here

        elif role == "volume":
            # Volume filter typically sets filter_pass_long/short directly
            # We preserve this but could also map from a 'volume_value' if needed.
            pass

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
            and bool(row.get("filter_pass_long", True))
        )
        short_entry = (
            self.direction_mode in {"short_only", "both"}
            and int(row.get("baseline_signal", 0)) == -1
            and int(row.get("c1_signal", 0)) == -1
            and int(row.get("c2_signal", 0)) == -1
            and bool(row.get("filter_pass_short", True))
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
