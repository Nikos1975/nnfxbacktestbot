from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from nnfx_crypto.config.schema import StrategyConfig
from nnfx_crypto.data.validation import validate_ohlcv


def hummingbot_yaml_to_strategy_config(path: str | Path) -> StrategyConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    trading_pair = raw["trading_pair"]
    base, quote = trading_pair.split("-", 1)
    execution = raw.get("execution", {})
    order_type = str(execution.get("order_type", "market")).lower()
    data_path = raw.get("data", {}).get(
        "path",
        f"data/nnfx_crypto/processed/{trading_pair}_{raw.get('timeframe', '1h')}.csv",
    )
    strategy_raw = {
        "strategy": {
            "name": raw.get("controller_name", "nnfx_algo5_controller"),
            "mode": "paper",
            "direction_mode": raw.get("direction_mode", "both"),
            "allow_continuation_trades": raw.get("allow_continuation_trades", False),
        },
        "market": {
            "connector": raw.get("connector_name", "binance_perpetual"),
            "trading_pair": trading_pair,
            "timeframe": raw.get("timeframe", "1h"),
            "quote_asset": quote,
            "base_asset": base,
        },
        "data": {"source": "csv", "path": data_path},
        "indicators": {
            "baseline": raw["nnfx"]["baseline"],
            "c1": raw["nnfx"]["c1"],
            "c2": raw["nnfx"]["c2"],
            "volume_or_volatility_filter": raw["nnfx"]["volume_or_volatility_filter"],
            "exit": raw["nnfx"]["exit"],
        },
        "risk": raw.get("risk", {}),
        "execution": {**execution, "order_type": order_type},
    }
    return StrategyConfig.model_validate(strategy_raw)


def candles_to_dataframe(candles: list[dict[str, Any]]) -> pd.DataFrame:
    return validate_ohlcv(pd.DataFrame(candles)[["timestamp", "open", "high", "low", "close", "volume"]])
