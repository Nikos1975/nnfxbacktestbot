from __future__ import annotations

from nnfx_crypto.signals.signal_types import TradeIntent


def intent_to_executor_action(
    intent: TradeIntent,
    connector_name: str,
    trading_pair: str,
    amount: float,
    entry_price: float,
    stop_price: float,
    tp1_price: float,
    existing_executor_pairs: set[str],
) -> dict | None:
    if trading_pair in existing_executor_pairs:
        return None
    if intent.action != "entry":
        return {
            "action": "stop_executor",
            "connector_name": connector_name,
            "trading_pair": trading_pair,
            "side": intent.side,
            "reason": intent.reason,
        }
    return {
        "action": "create_executor",
        "executor_type": "position",
        "connector_name": connector_name,
        "trading_pair": trading_pair,
        "side": intent.side,
        "amount": amount,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "tp1_price": tp1_price,
        "reason": intent.reason,
    }
