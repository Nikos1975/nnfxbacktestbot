import numpy as np
import pandas as pd
import pytest

from nnfx_crypto.indicators.registry import get_indicator


EXPECTED_COLUMNS = {
    "atr": ["atr"],
    "frama": ["baseline_value"],
    "reflex": ["reflex_value"],
    "stablefx": ["stablefx_value"],
    "stiffness": ["stiffness_value", "filter_pass_long", "filter_pass_short"],
    "crossroads": ["crossroads_green", "crossroads_magenta", "crossroads_signal", "crossroads_trend"],
}


PARAMS = {
    "atr": {"length": 14},
    "frama": {"length": 10, "fc": 1, "sc": 198},
    "reflex": {"length": 20},
    "stablefx": {"length": 14, "signal_length": 5},
    "stiffness": {"length": 20, "threshold": 50.0},
    "crossroads": {"start_len": 2, "lookback_period": 24},
}


def make_ohlcv(rows: int = 120) -> pd.DataFrame:
    idx = np.arange(rows, dtype=float)
    close = 100 + idx * 0.2 + np.sin(idx / 4.0)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=rows, freq="h"),
            "open": close - 0.1,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000 + idx,
        }
    )


@pytest.mark.parametrize("indicator_name,columns", EXPECTED_COLUMNS.items())
def test_indicator_outputs_required_columns(indicator_name: str, columns: list[str]):
    output = get_indicator(indicator_name).compute(make_ohlcv(), PARAMS[indicator_name])

    for column in columns:
        assert column in output.columns


@pytest.mark.parametrize("indicator_name,columns", EXPECTED_COLUMNS.items())
def test_indicator_has_no_lookahead(indicator_name: str, columns: list[str]):
    df = make_ohlcv(120)
    first = get_indicator(indicator_name).compute(df.iloc[:80].copy(), PARAMS[indicator_name])
    second = get_indicator(indicator_name).compute(df.copy(), PARAMS[indicator_name]).iloc[:80]

    for column in columns:
        pd.testing.assert_series_equal(
            first[column].reset_index(drop=True),
            second[column].reset_index(drop=True),
            check_names=False,
        )


def test_unknown_indicator_raises_clear_error():
    with pytest.raises(KeyError, match="Unknown indicator 'not_real'"):
        get_indicator("not_real")


def test_stiffness_supports_stonehill_period_names():
    output = get_indicator("stiffness").compute(
        make_ohlcv(180),
        {"period1": 100, "period3": 60, "period2": 3, "threshold": 50.0},
    )

    assert output["stiffness_value"].max() <= 100.0
    assert output["stiffness_signal"].notna().any()


def test_frama_supports_stonehill_period_name_and_warmup():
    output = get_indicator("frama").compute(
        make_ohlcv(80),
        {"period_frama": 10, "price_type": 0},
    )

    assert output["baseline_value"].iloc[:20].isna().all()
    assert output["baseline_value"].iloc[21:].notna().any()


def test_frama_price_type_changes_source_price():
    df = make_ohlcv(80)
    df["high"] = df["close"] + 2.0
    df["low"] = df["close"] - 0.5
    close_output = get_indicator("frama").compute(df, {"period_frama": 10, "price_type": 0})
    median_output = get_indicator("frama").compute(df, {"period_frama": 10, "price_type": 4})
    weighted_output = get_indicator("frama").compute(df, {"period_frama": 10, "price_type": 6})

    assert not close_output["baseline_value"].equals(median_output["baseline_value"])
    assert not median_output["baseline_value"].equals(weighted_output["baseline_value"])
