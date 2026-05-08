from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from nnfx_crypto.backtest.metrics import calculate_metrics
from nnfx_crypto.backtest.trade_log import TradeRecord, trades_to_frame
from nnfx_crypto.config.loader import dump_resolved_config
from nnfx_crypto.config.schema import StrategyConfig
from nnfx_crypto.data.ohlcv_loader import load_ohlcv_csv
from nnfx_crypto.indicators.registry import indicator_metadata_for_config
from nnfx_crypto.risk.atr_risk_model import ATRRiskModel, EntryPlan
from nnfx_crypto.risk.trade_state import OpenTrade
from nnfx_crypto.reports.chart_writer import write_equity_curve_chart, write_price_signal_chart
from nnfx_crypto.reports.report_writer import write_report_html, write_summary_md
from nnfx_crypto.signals.nnfx_signal_engine import NNFXSignalEngine


@dataclass(frozen=True)
class BacktestResult:
    run_dir: Path
    metrics: dict


class EventBacktester:
    def __init__(self, config: StrategyConfig, output_root: str | Path = "results/nnfx_crypto/backtests"):
        self.config = config
        self.output_root = Path(output_root)

    def run(self) -> BacktestResult:
        run_dir = self._create_run_dir()
        dump_resolved_config(self.config, run_dir / "resolved_config.yml")

        raw = self._apply_data_window(load_ohlcv_csv(self.config.data.path))
        frame = NNFXSignalEngine(self.config).compute_indicators(raw)
        equity_curve, trades = self._run_loop(frame)
        trades_df = trades_to_frame(trades)
        metrics = calculate_metrics(
            equity_curve,
            trades_df,
            self.config.backtest.initial_capital,
            self.config.market.trading_pair,
            self.config.market.timeframe,
            self.config.risk.max_open_positions_per_pair,
        )

        trades_df.to_csv(run_dir / "trades.csv", index=False)
        equity_curve.to_csv(run_dir / "equity_curve.csv", index=False)
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_summary_md(metrics, run_dir / "summary.md")
        if self.config.backtest.export_chart_png:
            write_price_signal_chart(frame, run_dir / "chart_price_signals.png", trades=trades_df)
            write_equity_curve_chart(equity_curve, run_dir / "chart_equity_curve.png")
        if self.config.backtest.export_html_report:
            write_report_html(
                metrics,
                run_dir / "report.html",
                indicator_metadata_for_config(self.config),
            )
        return BacktestResult(run_dir=run_dir, metrics=metrics)

    def _apply_data_window(self, frame: pd.DataFrame) -> pd.DataFrame:
        output = frame
        if self.config.data.start:
            output = output[output["timestamp"] >= self._coerce_boundary(self.config.data.start, output)]
        if self.config.data.end:
            output = output[output["timestamp"] <= self._coerce_boundary(self.config.data.end, output)]
        if output.empty:
            raise ValueError("No OHLCV rows remain after applying data start/end filters")
        return output.reset_index(drop=True)

    def _coerce_boundary(self, value: str, frame: pd.DataFrame) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        timezone = getattr(frame["timestamp"].dt, "tz", None)
        if timezone is not None and timestamp.tzinfo is None:
            return timestamp.tz_localize(timezone)
        if timezone is None and timestamp.tzinfo is not None:
            return timestamp.tz_localize(None)
        return timestamp

    def _run_loop(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, list[TradeRecord]]:
        engine = NNFXSignalEngine(self.config)
        risk_model = ATRRiskModel(
            account_equity=self.config.risk.account_equity,
            risk_per_trade_pct=self.config.risk.risk_per_trade_pct,
            stop_loss_atr_multiplier=self.config.risk.stop_loss_atr_multiplier,
            tp1_atr_multiplier=self.config.risk.tp1_atr_multiplier,
        )
        cash = self.config.backtest.initial_capital
        open_trade: OpenTrade | None = None
        entry_plan: EntryPlan | None = None
        trades: list[TradeRecord] = []
        equity_rows: list[dict] = []
        warmup = min(self.config.backtest.warmup_bars, max(0, len(frame) - 2))
        trading_halted = False

        for index in range(warmup, len(frame) - 1):
            row = frame.iloc[index]
            next_row = frame.iloc[index + 1]
            marked_equity = cash + self._unrealized_pnl(open_trade, float(row["close"]))
            drawdown_limit = self.config.backtest.initial_capital * (
                1.0 - self.config.risk.max_total_drawdown_pct
            )
            if open_trade is not None and marked_equity <= drawdown_limit:
                exit_price = float(row["close"])
                cash += self._close_pnl(open_trade, exit_price, open_trade.remaining_quantity)
                trades.append(self._record(open_trade, row, exit_price, "max_total_drawdown"))
                open_trade = None
                entry_plan = None
                trading_halted = True

            if open_trade is not None:
                events = open_trade.apply_high_low(
                    high=float(row["high"]),
                    low=float(row["low"]),
                    move_stop_to_breakeven=self.config.risk.move_second_half_to_breakeven_after_tp1,
                    intrabar_priority=self.config.execution.intrabar_priority,
                )
                if "tp1" in events:
                    half_quantity = open_trade.quantity / 2.0
                    cash += self._close_pnl(open_trade, open_trade.tp1_price, half_quantity)
                    trades.append(
                        self._record(open_trade, row, open_trade.tp1_price, "tp1", half_quantity)
                    )
                if "stop" in events:
                    cash += self._close_pnl(open_trade, open_trade.stop_price, open_trade.remaining_quantity)
                    trades.append(self._record(open_trade, row, open_trade.stop_price, "stop_loss"))
                    open_trade = None
                    entry_plan = None
                else:
                    intent = engine.evaluate_bar(
                        frame,
                        index,
                        has_open_position=True,
                        open_position_side=open_trade.side,
                    )
                    if intent is not None:
                        exit_price = float(next_row["open"]) if self.config.execution.use_next_bar_open else float(row["close"])
                        cash += self._close_pnl(open_trade, exit_price, open_trade.remaining_quantity)
                        trades.append(self._record(open_trade, next_row, exit_price, intent.reason))
                        open_trade = None
                        entry_plan = None

            if open_trade is None and not trading_halted:
                intent = engine.evaluate_bar(frame, index, has_open_position=False)
                atr = row.get("atr")
                if intent is not None and pd.notna(atr):
                    entry_price = float(next_row["open"]) if self.config.execution.use_next_bar_open else float(row["close"])
                    entry_price = self._slipped_price(entry_price, intent.side, is_entry=True)
                    entry_plan = risk_model.plan_entry(intent.side, entry_price, float(atr))
                    if intent.side == "long":
                        open_trade = OpenTrade.open_long(
                            self.config.market.trading_pair,
                            index + 1,
                            entry_plan.entry_price,
                            entry_plan.total_quantity,
                            entry_plan.stop_price,
                            entry_plan.tp1_price,
                            str(next_row["timestamp"]),
                        )
                    else:
                        open_trade = OpenTrade.open_short(
                            self.config.market.trading_pair,
                            index + 1,
                            entry_plan.entry_price,
                            entry_plan.total_quantity,
                            entry_plan.stop_price,
                            entry_plan.tp1_price,
                            str(next_row["timestamp"]),
                        )

            equity_rows.append(
                {
                    "timestamp": row["timestamp"],
                    "equity": cash + self._unrealized_pnl(open_trade, float(row["close"])),
                    "close": row["close"],
                    "open_position": int(open_trade is not None),
                }
            )

        if open_trade is not None and entry_plan is not None:
            final_row = frame.iloc[-1]
            exit_price = float(final_row["close"])
            cash += self._close_pnl(open_trade, exit_price, open_trade.remaining_quantity)
            trades.append(self._record(open_trade, final_row, exit_price, "end_of_data"))
            equity_rows.append(
                {
                    "timestamp": final_row["timestamp"],
                    "equity": cash,
                    "close": final_row["close"],
                    "open_position": 0,
                }
            )

        return pd.DataFrame(equity_rows), trades

    def _create_run_dir(self) -> Path:
        run_id = (
            f"{self.config.strategy.name}_{self.config.market.trading_pair}_"
            f"{self.config.market.timeframe}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        )
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def _close_pnl(self, trade: OpenTrade, exit_price: float, quantity: float) -> float:
        if trade.side == "long":
            gross = (exit_price - trade.entry_price) * quantity
        else:
            gross = (trade.entry_price - exit_price) * quantity
        fees = (trade.entry_price * quantity + exit_price * quantity) * self.config.execution.fee_pct
        return gross - fees

    def _unrealized_pnl(self, trade: OpenTrade | None, mark_price: float) -> float:
        if trade is None:
            return 0.0
        if trade.side == "long":
            return (mark_price - trade.entry_price) * trade.remaining_quantity
        return (trade.entry_price - mark_price) * trade.remaining_quantity

    def _record(
        self,
        trade: OpenTrade,
        row: pd.Series,
        exit_price: float,
        reason: str,
        quantity: float | None = None,
    ) -> TradeRecord:
        quantity = trade.remaining_quantity if quantity is None else quantity
        fees = (trade.entry_price * quantity + exit_price * quantity) * self.config.execution.fee_pct
        slippage = abs(exit_price * quantity * self.config.execution.slippage_pct)
        pnl = self._close_pnl(trade, exit_price, quantity)
        return TradeRecord(
            pair=trade.pair,
            side=trade.side,
            entry_time=trade.entry_time or str(trade.entry_index),
            exit_time=str(row["timestamp"]),
            entry_price=trade.entry_price,
            exit_price=exit_price,
            quantity=quantity,
            pnl=pnl,
            fees=fees,
            slippage=slippage,
            close_reason=reason,
        )

    def _slipped_price(self, price: float, side: str, is_entry: bool) -> float:
        pct = self.config.execution.slippage_pct
        if (side == "long" and is_entry) or (side == "short" and not is_entry):
            return price * (1.0 + pct)
        return price * (1.0 - pct)
