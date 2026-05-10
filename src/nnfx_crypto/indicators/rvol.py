import numpy as np
import pandas as pd

class RVOLIndicator:
    """Relative Volume participation filter."""
    name = "rvol"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        length = int(params.get("length", 20))
        threshold = float(params.get("threshold", 1.0))

        volume = output["volume"].astype(float)
        avg_volume = volume.rolling(window=length).mean()
        
        # rvol = volume / SMA(volume, length)
        rvol = volume / avg_volume
        
        output["rvol"] = rvol
        output["rvol_filter_signal"] = np.where(rvol >= threshold, 1, 0)
        
        return output
