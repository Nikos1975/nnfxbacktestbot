import json
from pathlib import Path

from nnfx_crypto.backtest.portfolio_backtester import PortfolioBacktester

from tests.test_nnfx_backtester_basic import write_config, write_ohlcv_csv


def test_portfolio_backtester_writes_summary_files(tmp_path: Path):
    configs: list[Path] = []
    for pair in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
        csv_path = tmp_path / f"{pair}_1h.csv"
        config_path = tmp_path / f"{pair}.yml"
        write_ohlcv_csv(csv_path)
        write_config(config_path, csv_path, tmp_path / "unused")
        text = config_path.read_text(encoding="utf-8").replace("BTC-USDT", pair)
        config_path.write_text(text, encoding="utf-8")
        configs.append(config_path)

    portfolio_path = tmp_path / "portfolio.yml"
    portfolio_path.write_text(
        "portfolio:\n"
        "  name: portfolio_algo5\n"
        "  strategies:\n"
        + "".join(f"    - {path.as_posix()}\n" for path in configs),
        encoding="utf-8",
    )
    output_root = tmp_path / "batch"

    result = PortfolioBacktester(portfolio_path, output_root=output_root).run()

    assert (result.run_dir / "portfolio_summary.csv").exists()
    assert (result.run_dir / "portfolio_metrics.json").exists()
    metrics = json.loads((result.run_dir / "portfolio_metrics.json").read_text(encoding="utf-8"))
    assert metrics["strategy_count"] == 3
    child_dirs = [path for path in result.run_dir.iterdir() if path.is_dir()]
    assert len(child_dirs) == 3
