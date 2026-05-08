from __future__ import annotations

from pathlib import Path

import pandas as pd

from nnfx_crypto.data.validation import validate_ohlcv


def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"OHLCV CSV not found: {csv_path}")
    return validate_ohlcv(pd.read_csv(csv_path))
