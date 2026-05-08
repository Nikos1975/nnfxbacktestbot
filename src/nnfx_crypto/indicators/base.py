from __future__ import annotations

from typing import Protocol

import pandas as pd


class Indicator(Protocol):
    name: str

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Return a dataframe with this indicator's output columns appended."""
        ...
