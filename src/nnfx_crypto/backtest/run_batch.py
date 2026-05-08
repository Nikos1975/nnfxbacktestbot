from __future__ import annotations

import argparse
from pathlib import Path

from nnfx_crypto.backtest.portfolio_backtester import PortfolioBacktester


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NNFX crypto portfolio backtests.")
    parser.add_argument("--config", required=True, help="Path to portfolio YAML config.")
    parser.add_argument(
        "--output-root",
        default="results/nnfx_crypto/backtests",
        help="Directory where batch run folders are written.",
    )
    args = parser.parse_args()
    result = PortfolioBacktester(args.config, output_root=Path(args.output_root)).run()
    print(result.run_dir)


if __name__ == "__main__":
    main()
