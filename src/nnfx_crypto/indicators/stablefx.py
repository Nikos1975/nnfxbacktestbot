from __future__ import annotations

import numpy as np
import pandas as pd


class StableFXIndicator:
    """Deterministic StableFX placeholder.

    The exact StableFX formula is not available in this workspace. This placeholder keeps the
    stable C2 interface and emits oscillator/signal crossover states without claiming parity
    with any proprietary implementation.
    """

    name = "stablefx"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        length = int(params.get("length", 14))
        signal_length = int(params.get("signal_length", 5))
        ema = output["close"].ewm(span=length, adjust=False, min_periods=length).mean()
        oscillator = output["close"] - ema
        signal = oscillator.ewm(span=signal_length, adjust=False, min_periods=signal_length).mean()
        output["stablefx_value"] = oscillator - signal
        return output
