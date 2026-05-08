from nnfx_crypto.risk.atr_risk_model import ATRRiskModel
from nnfx_crypto.risk.trade_state import OpenTrade


def test_atr_position_size_uses_equity_risk_and_stop_distance():
    model = ATRRiskModel(
        account_equity=10_000,
        risk_per_trade_pct=0.005,
        stop_loss_atr_multiplier=1.25,
        tp1_atr_multiplier=1.0,
    )

    plan = model.plan_entry(side="long", entry_price=100.0, atr=2.0)

    assert plan.stop_price == 97.5
    assert plan.tp1_price == 102.0
    assert plan.total_quantity == 20.0
    assert plan.first_half_quantity == 10.0
    assert plan.second_half_quantity == 10.0


def test_atr_position_size_supports_short_entries():
    model = ATRRiskModel(
        account_equity=10_000,
        risk_per_trade_pct=0.005,
        stop_loss_atr_multiplier=1.25,
        tp1_atr_multiplier=1.0,
    )

    plan = model.plan_entry(side="short", entry_price=100.0, atr=2.0)

    assert plan.stop_price == 102.5
    assert plan.tp1_price == 98.0
    assert plan.total_quantity == 20.0


def test_tp1_closes_half_and_moves_second_stop_to_breakeven():
    trade = OpenTrade.open_long(
        pair="BTC-USDT",
        entry_index=1,
        entry_price=100.0,
        quantity=20.0,
        stop_price=97.5,
        tp1_price=102.0,
    )

    events = trade.apply_high_low(high=102.1, low=99.5, move_stop_to_breakeven=True)

    assert "tp1" in events
    assert trade.first_half_closed is True
    assert trade.remaining_quantity == 10.0
    assert trade.stop_price == 100.0


def test_short_tp1_closes_half_and_moves_second_stop_to_breakeven():
    trade = OpenTrade.open_short(
        pair="BTC-USDT",
        entry_index=1,
        entry_price=100.0,
        quantity=20.0,
        stop_price=102.5,
        tp1_price=98.0,
    )

    events = trade.apply_high_low(high=100.5, low=97.9, move_stop_to_breakeven=True)

    assert "tp1" in events
    assert trade.first_half_closed is True
    assert trade.remaining_quantity == 10.0
    assert trade.stop_price == 100.0


def test_intrabar_priority_can_take_profit_before_stop():
    trade = OpenTrade.open_long(
        pair="BTC-USDT",
        entry_index=1,
        entry_price=100.0,
        quantity=20.0,
        stop_price=97.5,
        tp1_price=102.0,
    )

    events = trade.apply_high_low(
        high=102.1,
        low=97.4,
        move_stop_to_breakeven=True,
        intrabar_priority="take_profit",
    )

    assert events == ["tp1"]
    assert trade.first_half_closed is True
    assert trade.closed is False


def test_default_intrabar_priority_is_stop_loss():
    trade = OpenTrade.open_long(
        pair="BTC-USDT",
        entry_index=1,
        entry_price=100.0,
        quantity=20.0,
        stop_price=97.5,
        tp1_price=102.0,
    )

    events = trade.apply_high_low(high=102.1, low=97.4, move_stop_to_breakeven=True)

    assert events == ["stop"]
    assert trade.closed is True
