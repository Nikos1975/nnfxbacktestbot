from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trading_system.strategies.grid.grid_backtester import GridBacktestOutput
from trading_system.strategies.grid.grid_config import GridConfig


def write_grid_report(output: GridBacktestOutput, cfg: GridConfig, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"{cfg.symbol}_{cfg.timeframe}_grid_{stamp}"

    json_path = out_dir / f"{base_name}.json"
    trades_path = out_dir / f"{base_name}_trades.csv"
    equity_path = out_dir / f"{base_name}_equity.csv"

    payload = {
        "config": cfg.model_dump(),
        "result": output.result.to_dict(),
        "files": {
            "trades": str(trades_path),
            "equity": str(equity_path),
        },
    }

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    output.trades.to_csv(trades_path, index=False)
    output.equity.to_csv(equity_path, index=False)

    return json_path