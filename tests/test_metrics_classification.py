"""Tests for metrics.py — focused on PnL classification, breakeven handling,
profit_factor edge cases, and the NNFX two-half-position breakeven pattern."""
from __future__ import annotations

import pandas as pd
import pytest

from nnfx_crypto.backtest.metrics import calculate_metrics


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_equity(n: int = 10, start: float = 100_000.0) -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h"),
        "equity": [start] * n,
        "close": [50_000.0] * n,
        "open_position": [0] * n,
    })


def _make_trades(*pnl_values, sides=None) -> pd.DataFrame:
    n = len(pnl_values)
    if sides is None:
        sides = ["long"] * n
    return pd.DataFrame({
        "pair": ["BTC-USDT"] * n,
        "side": sides,
        "entry_time": ["2024-01-01 00:00"] * n,
        "exit_time": ["2024-01-02 00:00"] * n,
        "entry_price": [50_000.0] * n,
        "exit_price": [50_000.0] * n,
        "quantity": [1.0] * n,
        "pnl": list(pnl_values),
        "fees": [0.0] * n,
        "slippage": [0.0] * n,
        "close_reason": ["stop_loss"] * n,
    })


def _calc(trades: pd.DataFrame, capital: float = 100_000.0) -> dict:
    return calculate_metrics(_make_equity(), trades, capital, "BTC-USDT", "1h", 1)


# ---------------------------------------------------------------------------
# 1. No trades
# ---------------------------------------------------------------------------

def test_no_trades_safe():
    trades = pd.DataFrame(columns=["pair", "side", "entry_time", "exit_time",
                                   "entry_price", "exit_price", "quantity",
                                   "pnl", "fees", "slippage", "close_reason"])
    m = _calc(trades)
    assert m["total_trades"] == 0
    assert m["winning_trades"] == 0
    assert m["losing_trades"] == 0
    assert m["breakeven_trades"] == 0
    assert m["profit_factor"] == 0.0
    assert m["payoff_ratio"] == 0.0
    assert m["win_rate"] == 0.0
    assert m["loss_rate"] == 0.0
    assert m["breakeven_rate"] == 0.0
    assert m["gross_profit"] == 0.0
    assert m["gross_loss"] == 0.0
    assert m["consecutive_losses"] == 0
    assert m["median_trade_pnl"] == 0.0


# ---------------------------------------------------------------------------
# 2. All winning trades
# ---------------------------------------------------------------------------

def test_all_winning():
    trades = _make_trades(500.0, 1000.0, 200.0)
    m = _calc(trades)
    assert m["total_trades"] == 3
    assert m["winning_trades"] == 3
    assert m["losing_trades"] == 0
    assert m["breakeven_trades"] == 0
    assert m["gross_profit"] == 1700.0
    assert m["gross_loss"] == 0.0
    # profit_factor = None (infinity) when gross_loss == 0 and gross_profit > 0
    assert m["profit_factor"] is None
    assert m["payoff_ratio"] is None
    assert m["win_rate"] == pytest.approx(1.0)
    assert m["loss_rate"] == 0.0
    assert m["breakeven_rate"] == 0.0
    assert m["consecutive_losses"] == 0


# ---------------------------------------------------------------------------
# 3. All losing trades
# ---------------------------------------------------------------------------

def test_all_losing():
    trades = _make_trades(-400.0, -600.0)
    m = _calc(trades)
    assert m["total_trades"] == 2
    assert m["winning_trades"] == 0
    assert m["losing_trades"] == 2
    assert m["breakeven_trades"] == 0
    assert m["gross_profit"] == 0.0
    assert m["gross_loss"] == 1000.0
    assert m["profit_factor"] == 0.0
    assert m["win_rate"] == 0.0
    assert m["loss_rate"] == pytest.approx(1.0)
    assert m["consecutive_losses"] == 2


# ---------------------------------------------------------------------------
# 4. All breakeven trades (NNFX stop-at-breakeven pattern)
# ---------------------------------------------------------------------------

def test_all_breakeven():
    trades = _make_trades(0.0, 0.0, 0.0, 0.0)
    m = _calc(trades)
    assert m["total_trades"] == 4
    assert m["winning_trades"] == 0
    assert m["losing_trades"] == 0
    assert m["breakeven_trades"] == 4
    assert m["gross_profit"] == 0.0
    assert m["gross_loss"] == 0.0
    assert m["profit_factor"] == 0.0
    assert m["payoff_ratio"] == 0.0
    assert m["win_rate"] == 0.0
    assert m["loss_rate"] == 0.0
    assert m["breakeven_rate"] == pytest.approx(1.0)
    assert m["consecutive_losses"] == 0


# ---------------------------------------------------------------------------
# 5. Mixed wins, losses, breakeVens (NNFX typical pattern)
# ---------------------------------------------------------------------------

def test_mixed_wins_losses_breakevens():
    # 3 wins, 2 losses, 5 breakevens — mirrors the 1d pattern
    pnls = [800.0, 0.0, -300.0, 0.0, 1200.0, 0.0, -150.0, 0.0, 500.0, 0.0]
    trades = _make_trades(*pnls)
    m = _calc(trades)

    assert m["total_trades"] == 10
    assert m["winning_trades"] == 3
    assert m["losing_trades"] == 2
    assert m["breakeven_trades"] == 5

    assert m["gross_profit"] == pytest.approx(2500.0)
    assert m["gross_loss"] == pytest.approx(450.0)
    assert m["profit_factor"] == pytest.approx(2500.0 / 450.0)
    assert m["win_rate"] == pytest.approx(0.3)
    assert m["loss_rate"] == pytest.approx(0.2)
    assert m["breakeven_rate"] == pytest.approx(0.5)

    assert m["average_win"] == pytest.approx(2500.0 / 3)
    assert m["average_loss"] == pytest.approx(-450.0 / 2)
    assert m["largest_win"] == pytest.approx(1200.0)
    assert m["largest_loss"] == pytest.approx(-300.0)

    expected_payoff = (2500.0 / 3) / (450.0 / 2)
    assert m["payoff_ratio"] == pytest.approx(expected_payoff)


# ---------------------------------------------------------------------------
# 6. profit_factor = None (infinity) when gross_loss == 0 and gross_profit > 0
# ---------------------------------------------------------------------------

def test_profit_factor_infinity_when_no_losses():
    trades = _make_trades(1000.0, 0.0, 500.0)  # wins + breakevens, no losses
    m = _calc(trades)
    assert m["gross_loss"] == 0.0
    assert m["gross_profit"] == pytest.approx(1500.0)
    assert m["profit_factor"] is None   # serialises as JSON null → UI shows "∞ (no losses)"
    assert m["payoff_ratio"] is None


# ---------------------------------------------------------------------------
# 7. profit_factor = 0.0 when both gross_profit and gross_loss == 0
# ---------------------------------------------------------------------------

def test_profit_factor_zero_when_all_breakeven():
    trades = _make_trades(0.0, 0.0)
    m = _calc(trades)
    assert m["profit_factor"] == 0.0
    assert m["payoff_ratio"] == 0.0


# ---------------------------------------------------------------------------
# 8. Consecutive losses count correctly; breakevens do NOT count as losses
# ---------------------------------------------------------------------------

def test_consecutive_losses_ignores_breakevens():
    # lose, lose, breakeven, lose, breakeven — max streak is 2
    pnls = [-100.0, -200.0, 0.0, -50.0, 0.0]
    trades = _make_trades(*pnls)
    m = _calc(trades)
    assert m["consecutive_losses"] == 2


def test_consecutive_losses_streak():
    pnls = [100.0, -50.0, -60.0, -70.0, 200.0, -10.0]
    trades = _make_trades(*pnls)
    m = _calc(trades)
    assert m["consecutive_losses"] == 3


# ---------------------------------------------------------------------------
# 9. win/loss/breakeven rate sums to 1.0
# ---------------------------------------------------------------------------

def test_rates_sum_to_one():
    pnls = [500.0, -100.0, 0.0, 200.0, 0.0, -50.0]
    trades = _make_trades(*pnls)
    m = _calc(trades)
    total_rate = m["win_rate"] + m["loss_rate"] + m["breakeven_rate"]
    assert total_rate == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 10. breakeven_trades count matches close_reason stop_loss with quantity=0
#     (the real NNFX pattern: entry==exit, pnl==0)
# ---------------------------------------------------------------------------

def test_breakeven_trades_match_nnfx_stop_at_entry():
    """Simulates the actual 1d result: 59 stop_loss trades with pnl=0."""
    n_wins = 49
    n_breakeven = 59
    pnls = [780.0] * n_wins + [0.0] * n_breakeven
    trades = _make_trades(*pnls)
    m = _calc(trades)
    assert m["winning_trades"] == n_wins
    assert m["breakeven_trades"] == n_breakeven
    assert m["losing_trades"] == 0
    assert m["profit_factor"] is None  # no losses
    assert m["breakeven_rate"] == pytest.approx(n_breakeven / (n_wins + n_breakeven))
