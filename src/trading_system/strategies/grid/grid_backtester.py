from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from trading_system.backtesting.fees import fee
from trading_system.backtesting.slippage import apply_slippage
from trading_system.indicators.adx import adx
from trading_system.indicators.chop import chop
from trading_system.regimes.grid_regime import GridRegime, classify_grid_regime
from trading_system.strategies.grid.grid_builder import build_grid_levels
from trading_system.strategies.grid.grid_config import GridConfig


TRADING_DAYS_PER_YEAR = 365.0


@dataclass
class TradeEvent:
    timestamp: str
    side: str
    price: float
    quantity: float
    gross_quote: float
    fee: float
    cash_after: float
    base_after: float
    realized_pnl: float
    regime: str
    grid_level: float


@dataclass
class EquityPoint:
    timestamp: str
    close: float
    cash: float
    base: float
    equity: float
    drawdown_pct: float
    regime: str
    unrealized_pnl: float
    exposure_pct: float
    buy_and_hold_equity: float
    buy_and_hold_drawdown_pct: float


@dataclass
class GridBacktestResult:
    symbol: str
    rows: int
    start: str
    end: str
    initial_cash: float
    final_equity: float
    total_pnl: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    fees_paid: float
    buy_count: int
    sell_count: int
    final_base_inventory: float
    max_base_inventory: float
    final_cash: float

    max_drawdown_pct: float
    buy_and_hold_final_equity: float
    buy_and_hold_return_pct: float
    buy_and_hold_max_drawdown_pct: float
    strategy_vs_buy_and_hold_pct: float

    strategy_volatility_annualized_pct: float
    buy_and_hold_volatility_annualized_pct: float

    active_bars: int
    hold_only_bars: int
    paused_bars: int
    active_pct: float
    hold_only_pct: float
    paused_pct: float

    max_exposure_pct: float
    avg_exposure_pct: float
    exposure_adjusted_return: float

    time_underwater_bars: int
    time_underwater_pct: float
    buy_and_hold_time_underwater_bars: int
    buy_and_hold_time_underwater_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GridBacktestOutput:
    result: GridBacktestResult
    trades: pd.DataFrame
    equity: pd.DataFrame


def _bars_per_year(timeframe: str) -> float:
    mapping = {
        "1m": 365 * 24 * 60,
        "3m": 365 * 24 * 20,
        "5m": 365 * 24 * 12,
        "15m": 365 * 24 * 4,
        "30m": 365 * 24 * 2,
        "1h": 365 * 24,
        "2h": 365 * 12,
        "4h": 365 * 6,
        "6h": 365 * 4,
        "8h": 365 * 3,
        "12h": 365 * 2,
        "1d": 365,
    }
    if timeframe not in mapping:
        raise ValueError(f"Unsupported timeframe for volatility annualization: {timeframe}")
    return float(mapping[timeframe])


def _annualized_volatility(equity: pd.Series, timeframe: str) -> float:
    returns = equity.pct_change().dropna()
    if returns.empty:
        return 0.0
    return float(returns.std() * (_bars_per_year(timeframe) ** 0.5))


def _empty_trades_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "timestamp",
            "side",
            "price",
            "quantity",
            "gross_quote",
            "fee",
            "cash_after",
            "base_after",
            "realized_pnl",
            "regime",
            "grid_level",
        ]
    )


def _empty_equity_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "timestamp",
            "close",
            "cash",
            "base",
            "equity",
            "drawdown_pct",
            "regime",
            "unrealized_pnl",
            "exposure_pct",
            "buy_and_hold_equity",
            "buy_and_hold_drawdown_pct",
        ]
    )


def run_grid_backtest(df: pd.DataFrame, cfg: GridConfig) -> GridBacktestOutput:
    if df.empty:
        raise ValueError("Cannot run grid backtest on empty dataframe.")

    data = df.copy()
    data["adx"] = adx(data, cfg.regime.adx_period)
    data["chop"] = chop(data, cfg.regime.chop_period)
    data["regime"] = [
        classify_grid_regime(a, c) for a, c in zip(data["adx"], data["chop"], strict=False)
    ]

    levels = build_grid_levels(cfg)

    cash = cfg.initial_cash
    base = 0.0
    avg_cost = 0.0
    realized_pnl_total = 0.0
    fees_paid = 0.0
    buy_count = 0
    sell_count = 0
    max_base = 0.0
    last_buy_level: float | None = None

    trades: list[TradeEvent] = []
    equity_points: list[EquityPoint] = []

    peak_equity = cfg.initial_cash

    first_close = float(data.iloc[0]["close"])
    buy_and_hold_qty = cfg.initial_cash / first_close
    buy_and_hold_peak = cfg.initial_cash

    for _, row in data.iterrows():
        timestamp = str(row["timestamp"])
        close = float(row["close"])
        low = float(row["low"])
        high = float(row["high"])
        regime = row["regime"]

        if regime == GridRegime.ACTIVE:
            for level in levels:
                if low <= level <= high and close >= level and cash >= cfg.order_size_quote:
                    buy_price = apply_slippage(level, "buy", cfg.slippage_rate)
                    qty = cfg.order_size_quote / buy_price
                    trade_fee = fee(cfg.order_size_quote, cfg.fee_rate)
                    total_cost = cfg.order_size_quote + trade_fee

                    if cash >= total_cost:
                        old_cost_value = avg_cost * base
                        cash -= total_cost
                        base += qty
                        avg_cost = (old_cost_value + cfg.order_size_quote) / base

                        fees_paid += trade_fee
                        buy_count += 1
                        last_buy_level = level

                        trades.append(
                            TradeEvent(
                                timestamp=timestamp,
                                side="buy",
                                price=float(buy_price),
                                quantity=float(qty),
                                gross_quote=float(cfg.order_size_quote),
                                fee=float(trade_fee),
                                cash_after=float(cash),
                                base_after=float(base),
                                realized_pnl=0.0,
                                regime=str(regime),
                                grid_level=float(level),
                            )
                        )
                        break

        if regime in {GridRegime.ACTIVE, GridRegime.HOLD_ONLY} and base > 0:
            if last_buy_level is not None:
                upper_levels = [x for x in levels if x > last_buy_level]
                if upper_levels:
                    target = upper_levels[0]
                    if high >= target:
                        sell_price = apply_slippage(target, "sell", cfg.slippage_rate)
                        qty_to_sell = min(base, cfg.order_size_quote / sell_price)
                        gross = qty_to_sell * sell_price
                        trade_fee = fee(gross, cfg.fee_rate)
                        pnl = gross - trade_fee - (qty_to_sell * avg_cost)

                        cash += gross - trade_fee
                        base -= qty_to_sell
                        realized_pnl_total += pnl
                        fees_paid += trade_fee
                        sell_count += 1

                        if base <= 1e-12:
                            base = 0.0
                            avg_cost = 0.0

                        trades.append(
                            TradeEvent(
                                timestamp=timestamp,
                                side="sell",
                                price=float(sell_price),
                                quantity=float(qty_to_sell),
                                gross_quote=float(gross),
                                fee=float(trade_fee),
                                cash_after=float(cash),
                                base_after=float(base),
                                realized_pnl=float(pnl),
                                regime=str(regime),
                                grid_level=float(target),
                            )
                        )

                        last_buy_level = None

        strategy_equity = cash + base * close
        peak_equity = max(peak_equity, strategy_equity)
        strategy_drawdown_pct = 0.0 if peak_equity <= 0 else abs(strategy_equity / peak_equity - 1.0)

        unrealized_pnl = base * (close - avg_cost) if base > 0 else 0.0
        exposure_value = base * close
        exposure_pct = 0.0 if strategy_equity <= 0 else exposure_value / strategy_equity

        buy_and_hold_equity = buy_and_hold_qty * close
        buy_and_hold_peak = max(buy_and_hold_peak, buy_and_hold_equity)
        buy_and_hold_drawdown_pct = (
            0.0
            if buy_and_hold_peak <= 0
            else abs(buy_and_hold_equity / buy_and_hold_peak - 1.0)
        )

        equity_points.append(
            EquityPoint(
                timestamp=timestamp,
                close=float(close),
                cash=float(cash),
                base=float(base),
                equity=float(strategy_equity),
                drawdown_pct=float(strategy_drawdown_pct),
                regime=str(regime),
                unrealized_pnl=float(unrealized_pnl),
                exposure_pct=float(exposure_pct),
                buy_and_hold_equity=float(buy_and_hold_equity),
                buy_and_hold_drawdown_pct=float(buy_and_hold_drawdown_pct),
            )
        )

        max_base = max(max_base, base)

    trades_df = pd.DataFrame([asdict(t) for t in trades]) if trades else _empty_trades_df()
    equity_df = (
        pd.DataFrame([asdict(e) for e in equity_points]) if equity_points else _empty_equity_df()
    )

    final_close = float(data.iloc[-1]["close"])
    final_equity = float(equity_df.iloc[-1]["equity"])
    total_pnl = final_equity - cfg.initial_cash
    total_return_pct = total_pnl / cfg.initial_cash

    unrealized_pnl_final = base * (final_close - avg_cost) if base > 0 else 0.0

    buy_and_hold_final_equity = float(equity_df.iloc[-1]["buy_and_hold_equity"])
    buy_and_hold_return_pct = (buy_and_hold_final_equity - cfg.initial_cash) / cfg.initial_cash
    strategy_vs_buy_and_hold_pct = total_return_pct - buy_and_hold_return_pct

    active_bars = int((data["regime"] == GridRegime.ACTIVE).sum())
    hold_only_bars = int((data["regime"] == GridRegime.HOLD_ONLY).sum())
    paused_bars = int((data["regime"] == GridRegime.PAUSED).sum())
    rows = len(data)

    max_drawdown_pct = float(equity_df["drawdown_pct"].max()) if not equity_df.empty else 0.0
    buy_and_hold_max_drawdown_pct = (
        float(equity_df["buy_and_hold_drawdown_pct"].max()) if not equity_df.empty else 0.0
    )

    strategy_volatility_annualized_pct = _annualized_volatility(equity_df["equity"], cfg.timeframe)
    buy_and_hold_volatility_annualized_pct = _annualized_volatility(
        equity_df["buy_and_hold_equity"], cfg.timeframe
    )

    max_exposure_pct = float(equity_df["exposure_pct"].max()) if not equity_df.empty else 0.0
    avg_exposure_pct = float(equity_df["exposure_pct"].mean()) if not equity_df.empty else 0.0

    exposure_adjusted_return = (
        float(total_return_pct / avg_exposure_pct) if avg_exposure_pct > 0 else 0.0
    )

    time_underwater_bars = int((equity_df["drawdown_pct"] > 0).sum()) if not equity_df.empty else 0
    time_underwater_pct = time_underwater_bars / rows if rows else 0.0

    buy_and_hold_time_underwater_bars = (
        int((equity_df["buy_and_hold_drawdown_pct"] > 0).sum()) if not equity_df.empty else 0
    )
    buy_and_hold_time_underwater_pct = buy_and_hold_time_underwater_bars / rows if rows else 0.0

    result = GridBacktestResult(
        symbol=cfg.symbol,
        rows=rows,
        start=str(data.iloc[0]["timestamp"]),
        end=str(data.iloc[-1]["timestamp"]),
        initial_cash=float(cfg.initial_cash),
        final_equity=float(final_equity),
        total_pnl=float(total_pnl),
        total_return_pct=float(total_return_pct),
        realized_pnl=float(realized_pnl_total),
        unrealized_pnl=float(unrealized_pnl_final),
        fees_paid=float(fees_paid),
        buy_count=buy_count,
        sell_count=sell_count,
        final_base_inventory=float(base),
        max_base_inventory=float(max_base),
        final_cash=float(cash),
        max_drawdown_pct=max_drawdown_pct,
        buy_and_hold_final_equity=float(buy_and_hold_final_equity),
        buy_and_hold_return_pct=float(buy_and_hold_return_pct),
        buy_and_hold_max_drawdown_pct=float(buy_and_hold_max_drawdown_pct),
        strategy_vs_buy_and_hold_pct=float(strategy_vs_buy_and_hold_pct),
        strategy_volatility_annualized_pct=float(strategy_volatility_annualized_pct),
        buy_and_hold_volatility_annualized_pct=float(buy_and_hold_volatility_annualized_pct),
        active_bars=active_bars,
        hold_only_bars=hold_only_bars,
        paused_bars=paused_bars,
        active_pct=active_bars / rows,
        hold_only_pct=hold_only_bars / rows,
        paused_pct=paused_bars / rows,
        max_exposure_pct=max_exposure_pct,
        avg_exposure_pct=avg_exposure_pct,
        exposure_adjusted_return=exposure_adjusted_return,
        time_underwater_bars=time_underwater_bars,
        time_underwater_pct=float(time_underwater_pct),
        buy_and_hold_time_underwater_bars=buy_and_hold_time_underwater_bars,
        buy_and_hold_time_underwater_pct=float(buy_and_hold_time_underwater_pct),
    )

    return GridBacktestOutput(result=result, trades=trades_df, equity=equity_df)