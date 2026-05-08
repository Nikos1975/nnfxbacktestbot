from enum import StrEnum
import pandas as pd

class GridRegime(StrEnum):
    ACTIVE = "ACTIVE"
    HOLD_ONLY = "HOLD ONLY"
    PAUSED = "PAUSED"

def classify_grid_regime(adx_value: float, chop_value: float) -> GridRegime:
    if pd.isna(adx_value) or pd.isna(chop_value):
        return GridRegime.HOLD_ONLY

    if adx_value < 20:
        return GridRegime.ACTIVE

    if 20 <= adx_value <= 25:
        if chop_value > 61.8:
            return GridRegime.ACTIVE
        if 38.2 <= chop_value <= 61.8:
            return GridRegime.HOLD_ONLY
        if chop_value < 38.2:
            return GridRegime.PAUSED

    if adx_value > 25:
        return GridRegime.PAUSED

    return GridRegime.HOLD_ONLY
