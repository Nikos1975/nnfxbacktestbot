from __future__ import annotations

import argparse
from pathlib import Path

from nnfx_crypto.backtest.event_backtester import EventBacktester
from nnfx_crypto.config.loader import load_strategy_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one NNFX crypto backtest.")
    parser.add_argument("--config", required=True, help="Path to strategy YAML config.")
    parser.add_argument(
        "--output-root",
        default="results/nnfx_crypto/backtests",
        help="Directory where run folders are written.",
    )
    args = parser.parse_args()
    config = load_strategy_config(args.config)
    result = EventBacktester(config, output_root=Path(args.output_root)).run()
    print(result.run_dir)


if __name__ == "__main__":
    main()
