# Auto-generated signal-exit-only variant.
# Purpose: remove Freqtrade ROI-table exits to test indicator exit logic.
# Mechanical change: minimal_roi = {"0": 100}

from __future__ import annotations

import numpy as np
import pandas as pd
import talib.abstract as ta

from freqtrade.strategy import IStrategy
from pandas import DataFrame


class NnfxCoreJmaTdfiKijunVoxiChandelierSignalExitOnly(IStrategy):
    """
    Baseline JMA proxy + C1 TDFI proxy + C2 Kijun state + VOXI proxy + Chandelier Exit.
    These are dry-run/backtest hypotheses, not live strategies.
    Several TradingView-only indicators are implemented as codeable proxies.
    """

    timeframe = "1d"
    can_short = False
    startup_candle_count = 400
    process_only_new_candles = True

    minimal_roi = {"0": 100}
    stoploss = -0.15
    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    jma_period = 21
    kijun_period = 26
    atr_period = 22
    chandelier_mult = 3.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        close = dataframe["close"]
        dataframe["baseline"] = close.ewm(span=self.jma_period, adjust=False, min_periods=self.jma_period).mean()
        dataframe["baseline_slope"] = dataframe["baseline"].diff(3)
        dataframe["tdfi"] = self._tdfi_proxy(close)
        dataframe["kijun"] = self._kijun(dataframe, self.kijun_period)
        dataframe["voxi"] = self._voxi_proxy(dataframe)
        atr = self._atr_rma(dataframe, self.atr_period)
        dataframe["chandelier_long"] = dataframe["high"].rolling(self.atr_period, min_periods=self.atr_period).max() - self.chandelier_mult * atr
        dataframe["baseline_signal"] = (close > dataframe["baseline"]) & (dataframe["baseline_slope"] > 0)
        dataframe["c1_signal"] = dataframe["tdfi"] > 0.05
        dataframe["c2_signal"] = close > dataframe["kijun"]
        dataframe["volume_filter"] = dataframe["voxi"] > 1.0
        dataframe["exit_signal"] = (close < dataframe["chandelier_long"]) | (dataframe["tdfi"] < 0)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["volume"] > 0) & dataframe["baseline_signal"] & dataframe["c1_signal"] & dataframe["c2_signal"] & dataframe["volume_filter"], "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["volume"] > 0) & dataframe["exit_signal"], "exit_long"] = 1
        return dataframe

    @staticmethod
    def _rma(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    @staticmethod
    def _true_range(dataframe: DataFrame) -> pd.Series:
        high = dataframe["high"]
        low = dataframe["low"]
        prev_close = dataframe["close"].shift(1)
        return pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)

    @classmethod
    def _atr_rma(cls, dataframe: DataFrame, period: int) -> pd.Series:
        return cls._rma(cls._true_range(dataframe), period)

    @staticmethod
    def _kijun(dataframe: DataFrame, period: int = 26) -> pd.Series:
        high_max = dataframe["high"].rolling(period, min_periods=period).max()
        low_min = dataframe["low"].rolling(period, min_periods=period).min()
        return (high_max + low_min) / 2

    @staticmethod
    def _chop(dataframe: DataFrame, period: int = 14) -> pd.Series:
        high = dataframe["high"]
        low = dataframe["low"]
        close = dataframe["close"]
        previous_close = close.shift(1)
        true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
        atr_sum = true_range.rolling(period, min_periods=period).sum()
        high_max = high.rolling(period, min_periods=period).max()
        low_min = low.rolling(period, min_periods=period).min()
        range_ = (high_max - low_min).replace(0, np.nan)
        return 100 * np.log10(atr_sum / range_) / np.log10(period)

    @staticmethod
    def _rsx_proxy(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.ewm(span=5, adjust=False, min_periods=5).mean()

    @staticmethod
    def _tdfi_proxy(close: pd.Series, fast: int = 8, slow: int = 21) -> pd.Series:
        ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
        spread = ema_fast - ema_slow
        norm = close.rolling(slow, min_periods=slow).std().replace(0, np.nan)
        return (spread / norm).clip(-5, 5) / 5

    @staticmethod
    def _mcginley(close: pd.Series, period: int = 10) -> pd.Series:
        out = pd.Series(index=close.index, dtype=float)
        out.iloc[0] = close.iloc[0]
        for i in range(1, len(close)):
            prev = out.iloc[i - 1]
            price = close.iloc[i]
            if not np.isfinite(prev) or prev == 0 or not np.isfinite(price):
                out.iloc[i] = price
                continue
            ratio = price / prev
            denom = period * (ratio ** 4)
            out.iloc[i] = prev + (price - prev) / denom if denom != 0 else prev
        return out

    @staticmethod
    def _ott_proxy(close: pd.Series, period: int = 2, multiplier: float = 1.4) -> tuple[pd.Series, pd.Series]:
        support = close.ewm(span=period + 1, adjust=False, min_periods=period).mean()
        ott_line = support.shift(1) * (1 - multiplier / 100)
        return support, ott_line

    @classmethod
    def _alphatrend_proxy(cls, dataframe: DataFrame, period: int = 14, multiplier: float = 1.0) -> pd.Series:
        atr = cls._atr_rma(dataframe, period)
        mfi = ta.MFI(dataframe, timeperiod=period)
        up_line = dataframe["low"] - atr * multiplier
        down_line = dataframe["high"] + atr * multiplier
        line = pd.Series(index=dataframe.index, dtype=float)
        line.iloc[0] = np.nan
        for i in range(1, len(dataframe)):
            prev = line.iloc[i - 1]
            if not np.isfinite(prev):
                prev = dataframe["close"].iloc[i - 1]
            line.iloc[i] = max(up_line.iloc[i], prev) if mfi.iloc[i] >= 50 else min(down_line.iloc[i], prev)
        return line

    @classmethod
    def _halftrend_proxy(cls, dataframe: DataFrame, period: int = 6) -> pd.Series:
        midpoint = (dataframe["high"].rolling(period, min_periods=period).max() + dataframe["low"].rolling(period, min_periods=period).min()) / 2
        return midpoint.ewm(span=3, adjust=False, min_periods=3).mean()

    @staticmethod
    def _stc_proxy(close: pd.Series, fast: int = 23, slow: int = 50, cycle: int = 10) -> pd.Series:
        ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
        macd = ema_fast - ema_slow
        lowest = macd.rolling(cycle, min_periods=cycle).min()
        highest = macd.rolling(cycle, min_periods=cycle).max()
        stoch = 100 * (macd - lowest) / (highest - lowest).replace(0, np.nan)
        return stoch.ewm(span=3, adjust=False, min_periods=3).mean()

    @staticmethod
    def _mac_z_vwap_proxy(dataframe: DataFrame, fast: int = 12, slow: int = 26) -> pd.Series:
        close = dataframe["close"]
        ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        hist = macd - signal
        typical = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        pv = typical * dataframe["volume"]
        vwap = pv.rolling(30, min_periods=30).sum() / dataframe["volume"].rolling(30, min_periods=30).sum().replace(0, np.nan)
        z = (close - vwap) / close.rolling(30, min_periods=30).std().replace(0, np.nan)
        return hist + z

    @staticmethod
    def _smi_mfi_proxy(dataframe: DataFrame, period: int = 14) -> pd.Series:
        mfi = ta.MFI(dataframe, timeperiod=period)
        return (mfi - 50).ewm(span=5, adjust=False, min_periods=5).mean()

    @staticmethod
    def _voxi_proxy(dataframe: DataFrame, lookback: int = 365, smoothing: int = 10) -> pd.Series:
        vol_ma = dataframe["volume"].rolling(lookback, min_periods=min(lookback, 60)).mean()
        ratio = dataframe["volume"] / vol_ma.replace(0, np.nan)
        return ratio.ewm(span=smoothing, adjust=False, min_periods=smoothing).mean()

    @staticmethod
    def _keltner_outside(dataframe: DataFrame, period: int = 20, mult: float = 1.5) -> pd.Series:
        typical = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        mid = typical.ewm(span=period, adjust=False, min_periods=period).mean()
        tr = pd.concat([dataframe["high"] - dataframe["low"], (dataframe["high"] - dataframe["close"].shift(1)).abs(), (dataframe["low"] - dataframe["close"].shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        upper = mid + mult * atr
        lower = mid - mult * atr
        return (typical > upper) | (typical < lower)

    @staticmethod
    def _wae_proxy(dataframe: DataFrame) -> tuple[pd.Series, pd.Series]:
        close = dataframe["close"]
        ema_fast = close.ewm(span=20, adjust=False, min_periods=20).mean()
        ema_slow = close.ewm(span=40, adjust=False, min_periods=40).mean()
        hist = ema_fast - ema_slow
        bb_mid = close.rolling(20, min_periods=20).mean()
        bb_std = close.rolling(20, min_periods=20).std()
        explosion = (bb_std * 2 / bb_mid.replace(0, np.nan)).abs()
        strength = (hist / close.replace(0, np.nan)).abs()
        return strength, explosion

