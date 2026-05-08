from pathlib import Path

import typer
from rich.console import Console

from trading_system.data.load_ohlcv import load_ohlcv_csv
from trading_system.reporting.tearsheet import write_grid_report
from trading_system.strategies.grid.grid_backtester import run_grid_backtest
from trading_system.strategies.grid.grid_config import GridConfig
from trading_system.utils.config import load_yaml

app = typer.Typer()
console = Console()


@app.command()
def main(
    data: Path = typer.Option(..., help="CSV with columns: timestamp,open,high,low,close,volume"),
    config: Path = typer.Option(..., help="Grid config YAML"),
    out: Path = typer.Option(Path("reports/backtests"), help="Output directory"),
):
    cfg = GridConfig.model_validate(load_yaml(config))
    df = load_ohlcv_csv(data)

    output = run_grid_backtest(df=df, cfg=cfg)
    report_path = write_grid_report(output=output, cfg=cfg, out_dir=out)

        console.print(f"[green]Report written:[/green] {report_path}")
    console.print(f"Trades: {len(output.trades)}")
    console.print(f"Equity rows: {len(output.equity)}")
    console.print(f"Total return: {output.result.total_return_pct:.2%}")
    console.print(f"Buy & hold return: {output.result.buy_and_hold_return_pct:.2%}")
    console.print(f"Strategy vs buy & hold: {output.result.strategy_vs_buy_and_hold_pct:.2%}")
    console.print(f"Max drawdown: {output.result.max_drawdown_pct:.2%}")
    console.print(f"Buy & hold max drawdown: {output.result.buy_and_hold_max_drawdown_pct:.2%}")
    console.print(f"Strategy volatility annualized: {output.result.strategy_volatility_annualized_pct:.2%}")
    console.print(f"Buy & hold volatility annualized: {output.result.buy_and_hold_volatility_annualized_pct:.2%}")
    console.print(f"Avg exposure: {output.result.avg_exposure_pct:.2%}")
    console.print(f"Exposure-adjusted return: {output.result.exposure_adjusted_return:.2f}")
    console.print(f"Time underwater: {output.result.time_underwater_pct:.2%}")
    console.print(f"Buy & hold time underwater: {output.result.buy_and_hold_time_underwater_pct:.2%}")


if __name__ == "__main__":
    app()