from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from nnfx_crypto.backtest.event_backtester import EventBacktester
from nnfx_crypto.config.loader import load_portfolio_config, load_strategy_config


@dataclass(frozen=True)
class PortfolioBacktestResult:
    run_dir: Path
    metrics: dict


class PortfolioBacktester:
    def __init__(self, config_path: str | Path, output_root: str | Path = "results/nnfx_crypto/backtests"):
        self.config_path = Path(config_path)
        self.output_root = Path(output_root)

    def run(self) -> PortfolioBacktestResult:
        portfolio_file = load_portfolio_config(self.config_path)
        run_dir = self._create_run_dir(portfolio_file.portfolio.name)
        rows: list[dict] = []
        for strategy_path in portfolio_file.portfolio.strategies:
            strategy_config = load_strategy_config(strategy_path)
            result = EventBacktester(strategy_config, output_root=run_dir).run()
            rows.append(
                {
                    "config": strategy_path,
                    "run_dir": str(result.run_dir),
                    "pair": strategy_config.market.trading_pair,
                    "timeframe": strategy_config.market.timeframe,
                    **result.metrics,
                }
            )

        summary = pd.DataFrame(rows)
        summary.to_csv(run_dir / "portfolio_summary.csv", index=False)
        metrics = {
            "name": portfolio_file.portfolio.name,
            "strategy_count": len(rows),
            "net_pnl": float(summary["net_pnl"].sum()) if not summary.empty else 0.0,
            "total_trades": int(summary["total_trades"].sum()) if not summary.empty else 0,
        }
        (run_dir / "portfolio_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return PortfolioBacktestResult(run_dir=run_dir, metrics=metrics)

    def _create_run_dir(self, name: str) -> Path:
        run_dir = self.output_root / f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
