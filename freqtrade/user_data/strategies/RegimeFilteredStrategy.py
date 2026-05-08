from __future__ import annotations

import numpy as np
import pandas as pd
import talib.abstract as ta

from freqtrade.strategy import IStrategy
from pandas import DataFrame


class RegimeFilteredStrategy(IStrategy):
    """
    Simple dry-run strategy for BTC/USDT spot.

    Purpose:
    - Test Freqtrade dry-run + FreqUI workflow.
    - Validate EMA baseline + ADX/CHOP regime filter.
    - Not intended for live trading without deeper testing.
    """

    timeframe = "1h"

    can_short = False

    startup_candle_count = 250

    process_only_new_candles = True

    minimal_roi = {
        "0": 0.05,
        "240": 0.03,
        "720": 0.01,
    }

    stoploss = -0.10

    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    ema_period = 200
    adx_period = 14
    chop_period = 14
    ema_slope_period = 5

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_baseline"] = ta.EMA(dataframe, timeperiod=self.ema_period)
        dataframe["ema_slope"] = dataframe["ema_baseline"].diff(self.ema_slope_period)

        dataframe["adx"] = ta.ADX(
            dataframe,
            timeperiod=self.adx_period,
        )

        dataframe["chop"] = self._choppiness_index(
            dataframe=dataframe,
            period=self.chop_period,
        )

        dataframe["regime"] = "HOLD_ONLY"

        active_condition_1 = dataframe["adx"] < 20

        active_condition_2 = (
            (dataframe["adx"] >= 20)
            & (dataframe["adx"] <= 25)
            & (dataframe["chop"] > 61.8)
        )

        paused_condition_1 = dataframe["adx"] > 25

        paused_condition_2 = (
            (dataframe["adx"] >= 20)
            & (dataframe["adx"] <= 25)
            & (dataframe["chop"] < 38.2)
        )

        dataframe.loc[active_condition_1 | active_condition_2, "regime"] = "ACTIVE"
        dataframe.loc[paused_condition_1 | paused_condition_2, "regime"] = "PAUSED"

        dataframe["entry_regime_ok"] = dataframe["regime"] == "ACTIVE"
        dataframe["exit_regime_pause"] = dataframe["regime"] == "PAUSED"

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["volume"] > 0)
                & (dataframe["close"] > dataframe["ema_baseline"])
                & (dataframe["ema_slope"] > 0)
                & (dataframe["entry_regime_ok"])
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["volume"] > 0)
                & (
                    (dataframe["close"] < dataframe["ema_baseline"])
                    | (dataframe["exit_regime_pause"])
                )
            ),
            "exit_long",
        ] = 1

        return dataframe

    @staticmethod
    def _choppiness_index(dataframe: DataFrame, period: int = 14) -> pd.Series:
        high = dataframe["high"]
        low = dataframe["low"]
        close = dataframe["close"]

        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr_sum = true_range.rolling(period, min_periods=period).sum()
        high_max = high.rolling(period, min_periods=period).max()
        low_min = low.rolling(period, min_periods=period).min()

        range_ = (high_max - low_min).replace(0, np.nan)

        chop = 100 * np.log10(atr_sum / range_) / np.log10(period)

        return chop