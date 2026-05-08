from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nnfx_crypto.config.schema import PortfolioFile, StrategyConfig
from nnfx_crypto.indicators.registry import indicator_metadata_for_config


def load_strategy_config(path: str | Path) -> StrategyConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    return StrategyConfig.model_validate(raw)


def load_portfolio_config(path: str | Path) -> PortfolioFile:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    return PortfolioFile.model_validate(raw)


def dump_resolved_config(config: StrategyConfig, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    data["indicator_metadata"] = indicator_metadata_for_config(config)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
