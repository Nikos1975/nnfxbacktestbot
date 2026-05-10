import pandas as pd

class PassIndicator:
    """An 'always-pass' filter for bypassing volume/volatility constraints."""
    name = "none"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
        output["filter_pass_long"] = True
        output["filter_pass_short"] = True
        return output
