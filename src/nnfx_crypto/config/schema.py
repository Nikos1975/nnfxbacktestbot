from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


DirectionMode = Literal["long_only", "short_only", "both"]
StrategyMode = Literal["backtest", "paper", "live"]
Timeframe = Literal["1h", "4h", "1d"]
DataSource = Literal["csv"]
OrderType = Literal["market", "limit"]
IntrabarPriority = Literal["stop_loss", "take_profit"]


class StrategySection(StrictModel):
    name: str
    mode: StrategyMode = "backtest"
    direction_mode: DirectionMode = "both"
    allow_continuation_trades: bool = False


class MarketSection(StrictModel):
    connector: str = "binance_perpetual"
    trading_pair: str
    timeframe: Timeframe = "1h"
    quote_asset: str = "USDT"
    base_asset: str | None = None

    @field_validator("base_asset", mode="before")
    @classmethod
    def default_base_asset(cls, value: str | None, info: Any) -> str | None:
        if value:
            return value
        pair = info.data.get("trading_pair")
        if isinstance(pair, str) and "-" in pair:
            return pair.split("-", 1)[0]
        return value


class DataSection(StrictModel):
    source: DataSource = "csv"
    path: str
    start: str | None = None
    end: str | None = None


class IndicatorConfig(StrictModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class IndicatorsSection(StrictModel):
    baseline: IndicatorConfig
    c1: IndicatorConfig
    c2: IndicatorConfig
    volume_or_volatility_filter: IndicatorConfig
    exit: IndicatorConfig

    @field_validator("baseline", "c1", "c2", "volume_or_volatility_filter", "exit")
    @classmethod
    def indicator_must_be_registered(cls, value: IndicatorConfig) -> IndicatorConfig:
        known = {"frama", "reflex", "stablefx", "stiffness", "crossroads", "atr"}
        if value.name.lower() not in known:
            known_text = ", ".join(sorted(known))
            raise ValueError(f"Unknown indicator '{value.name}'. Known indicators: {known_text}")
        return value


class RiskSection(StrictModel):
    account_equity: float = 10_000.0
    risk_per_trade_pct: float = 0.005
    atr_length: int = 14
    stop_loss_atr_multiplier: float = 1.25
    tp1_atr_multiplier: float = 1.0
    use_two_half_positions: bool = True
    move_second_half_to_breakeven_after_tp1: bool = True
    max_open_positions_per_pair: int = 1
    max_total_open_positions: int = 3
    max_daily_loss_pct: float = 0.02
    max_total_drawdown_pct: float = 0.20


class ExecutionSection(StrictModel):
    order_type: OrderType = "market"
    fee_pct: float = 0.0006
    slippage_pct: float = 0.0005
    use_next_bar_open: bool = True
    intrabar_priority: IntrabarPriority = "stop_loss"
    leverage: float = 1.0
    position_mode: str = "ONEWAY"


class BacktestSection(StrictModel):
    warmup_bars: int = 300
    initial_capital: float = 10_000.0
    export_trades_csv: bool = True
    export_equity_curve_csv: bool = True
    export_metrics_json: bool = True
    export_html_report: bool = True
    export_chart_png: bool = True


class StrategyConfig(StrictModel):
    strategy: StrategySection
    market: MarketSection
    data: DataSection
    indicators: IndicatorsSection
    risk: RiskSection = Field(default_factory=RiskSection)
    execution: ExecutionSection = Field(default_factory=ExecutionSection)
    backtest: BacktestSection = Field(default_factory=BacktestSection)
    indicator_metadata: dict[str, dict[str, Any]] | None = None


class PortfolioConfig(StrictModel):
    name: str = "portfolio_algo5"
    strategies: list[str]


class PortfolioFile(StrictModel):
    portfolio: PortfolioConfig
