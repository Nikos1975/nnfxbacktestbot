from __future__ import annotations

import numpy as np
import pandas as pd


class ReflexIndicator:
    """Reflex indicator by John Ehlers (TASC Feb 2020).
    
    Ported from public formula. Uses SuperSmoother filter and normalizes
    the sum of differences from a linear regression slope to get a low-lag oscillator.
    """

    name = "reflex"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        length = int(params.get("length", 20))
        
        close = output["close"].values
        n = len(close)
        
        filt = np.zeros(n)
        ms = np.zeros(n)
        reflex = np.zeros(n)
        
        if n <= length:
            output["reflex_value"] = reflex
            output["c1_signal"] = 0
            return output
            
        # SuperSmoother coefficients
        a1 = np.exp(-1.414 * np.pi / (0.5 * length))
        b1 = 2 * a1 * np.cos(1.414 * np.pi / (0.5 * length))
        c2 = b1
        c3 = -a1 * a1
        c1 = 1 - c2 - c3
        
        # SuperSmoother pass
        for i in range(2, n):
            filt[i] = c1 * (close[i] + close[i-1]) / 2.0 + c2 * filt[i-1] + c3 * filt[i-2]
            
        # Reflex calculation
        for i in range(length, n):
            slope = (filt[i-length] - filt[i]) / length
            
            sum_diff = 0.0
            for count in range(1, length + 1):
                sum_diff += (filt[i] + count * slope) - filt[i-count]
            sum_diff /= length
            
            ms[i] = 0.04 * (sum_diff * sum_diff) + 0.96 * ms[i-1]
            
            if ms[i] > 0:
                reflex[i] = sum_diff / np.sqrt(ms[i])
                
        # Fill Series and signals
        output["reflex_value"] = pd.Series(reflex, index=output.index)
        
        return output
