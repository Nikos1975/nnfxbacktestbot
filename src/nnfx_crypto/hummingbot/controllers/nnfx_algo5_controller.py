from __future__ import annotations

from nnfx_crypto.hummingbot.adapters.executor_action_adapter import intent_to_executor_action
from nnfx_crypto.hummingbot.adapters.hummingbot_config_adapter import candles_to_dataframe
from nnfx_crypto.risk.atr_risk_model import ATRRiskModel
from nnfx_crypto.signals.nnfx_signal_engine import NNFXSignalEngine

try:
    from hummingbot.strategy_v2.controllers.directional_trading_controller_base import (
        DirectionalTradingControllerBase,
    )
except ImportError:  # pragma: no cover - Hummingbot not installed in research env.
    DirectionalTradingControllerBase = object


class NNFXAlgo5Controller(DirectionalTradingControllerBase):
    """Thin Hummingbot V2 wrapper around portable NNFX signal engine."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.signal_engine = NNFXSignalEngine(config)

    def process_candles(self, candles: list[dict], existing_executor_pairs: set[str]) -> dict | None:
        frame = candles_to_dataframe(candles)
        frame = self.signal_engine.compute_indicators(frame)
        row_index = len(frame) - 1
        intent = self.signal_engine.evaluate_bar(frame, row_index, bool(existing_executor_pairs))
        if intent is None:
            return None
        row = frame.iloc[row_index]
        risk = ATRRiskModel(
            account_equity=self.config.risk.account_equity,
            risk_per_trade_pct=self.config.risk.risk_per_trade_pct,
            stop_loss_atr_multiplier=self.config.risk.stop_loss_atr_multiplier,
            tp1_atr_multiplier=self.config.risk.tp1_atr_multiplier,
        )
        plan = risk.plan_entry(intent.side, float(row["close"]), float(row["atr"]))
        return intent_to_executor_action(
            intent=intent,
            connector_name=self.config.market.connector,
            trading_pair=self.config.market.trading_pair,
            amount=plan.total_quantity,
            entry_price=plan.entry_price,
            stop_price=plan.stop_price,
            tp1_price=plan.tp1_price,
            existing_executor_pairs=existing_executor_pairs,
        )
