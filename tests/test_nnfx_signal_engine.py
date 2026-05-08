import pandas as pd

from nnfx_crypto.signals.nnfx_signal_engine import NNFXSignalEngine
from nnfx_crypto.signals.signal_types import ExitSignal, TradeIntent


def make_frame(**overrides) -> pd.DataFrame:
    data = {
        "timestamp": pd.date_range("2024-01-01", periods=2, freq="h"),
        "close": [100.0, 101.0],
        "baseline_signal": [0, 1],
        "c1_signal": [0, 1],
        "c2_signal": [1, 1],
        "filter_pass_long": [True, True],
        "filter_pass_short": [True, True],
        "exit_signal": [0, 0],
        "atr": [2.0, 2.0],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_signal_engine_emits_long_entry():
    intent = NNFXSignalEngine(allow_continuation_trades=False).evaluate_bar(
        make_frame(),
        row_index=1,
        has_open_position=False,
    )

    assert intent == TradeIntent(
        action="entry",
        side="long",
        reason="algo5_long_entry",
        index=1,
        timestamp=pd.Timestamp("2024-01-01 01:00:00"),
    )


def test_signal_engine_emits_short_entry():
    df = make_frame(
        close=[100.0, 99.0],
        baseline_signal=[0, -1],
        c1_signal=[0, -1],
        c2_signal=[-1, -1],
    )

    intent = NNFXSignalEngine(allow_continuation_trades=False).evaluate_bar(
        df,
        row_index=1,
        has_open_position=False,
    )

    assert intent is not None
    assert intent.action == "entry"
    assert intent.side == "short"


def test_signal_engine_filter_blocks_entry():
    df = make_frame(filter_pass_long=[True, False])

    intent = NNFXSignalEngine(allow_continuation_trades=False).evaluate_bar(
        df,
        row_index=1,
        has_open_position=False,
    )

    assert intent is None


def test_signal_engine_blocks_continuation_when_disabled():
    df = make_frame(
        baseline_signal=[1, 1],
        c1_signal=[1, 1],
        c2_signal=[1, 1],
    )

    intent = NNFXSignalEngine(allow_continuation_trades=False).evaluate_bar(
        df,
        row_index=1,
        has_open_position=False,
    )

    assert intent is None


def test_signal_engine_allows_continuation_when_enabled():
    df = make_frame(
        baseline_signal=[1, 1],
        c1_signal=[1, 1],
        c2_signal=[1, 1],
    )

    intent = NNFXSignalEngine(allow_continuation_trades=True).evaluate_bar(
        df,
        row_index=1,
        has_open_position=False,
    )

    assert intent is not None
    assert intent.side == "long"


def test_signal_engine_emits_long_exit():
    df = make_frame(exit_signal=[0, int(ExitSignal.EXIT_LONG)])

    intent = NNFXSignalEngine().evaluate_bar(
        df,
        row_index=1,
        has_open_position=True,
        open_position_side="long",
    )

    assert intent is not None
    assert intent.action == "exit"
    assert intent.side == "long"
    assert intent.reason == "crossroads_exit_long"


def test_signal_engine_emits_short_exit():
    df = make_frame(exit_signal=[0, int(ExitSignal.EXIT_SHORT)])

    intent = NNFXSignalEngine().evaluate_bar(
        df,
        row_index=1,
        has_open_position=True,
        open_position_side="short",
    )

    assert intent is not None
    assert intent.action == "exit"
    assert intent.side == "short"
    assert intent.reason == "crossroads_exit_short"
