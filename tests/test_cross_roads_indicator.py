import numpy as np
import pandas as pd
import pytest

from nnfx_crypto.indicators.crossroads import CrossRoadsIndicator


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "close": np.linspace(100, 150, 50),
        }
    )


def first_valid_index(series: pd.Series) -> int:
    valid = series.dropna()
    assert not valid.empty
    return int(valid.index[0])


def test_crossroads_validation(sample_data):
    indicator = CrossRoadsIndicator()

    with pytest.raises(ValueError, match="start_len must be >= 0"):
        indicator.compute(sample_data, {"start_len": -1, "lookback_period": 24})

    with pytest.raises(ValueError, match="lookback_period must be >= 2"):
        indicator.compute(sample_data, {"start_len": 0, "lookback_period": 1})

    with pytest.raises(ValueError, match="start_len .* must be less than lookback_period"):
        indicator.compute(sample_data, {"start_len": 24, "lookback_period": 24})


def test_crossroads_insufficient_warmup(sample_data):
    indicator = CrossRoadsIndicator()

    start_len = 2
    lookback_period = 10

    result = indicator.compute(
        sample_data,
        {
            "start_len": start_len,
            "lookback_period": lookback_period,
        },
    )

    # Current implementation uses rolling highest/lowest and then WMA over that
    # rolling series, so two rolling windows are involved.
    expected_first_valid = start_len + (2 * lookback_period) - 2

    assert first_valid_index(result["crossroads_green"]) == expected_first_valid
    assert first_valid_index(result["crossroads_magenta"]) == expected_first_valid

    assert pd.isna(result["crossroads_green"].iloc[expected_first_valid - 1])
    assert pd.notna(result["crossroads_green"].iloc[expected_first_valid])

    assert pd.isna(result["crossroads_magenta"].iloc[expected_first_valid - 1])
    assert pd.notna(result["crossroads_magenta"].iloc[expected_first_valid])

    # Signals should remain neutral during warmup.
    assert result["crossroads_signal"].iloc[expected_first_valid - 1] == 0
    assert result["crossroads_trend"].iloc[expected_first_valid - 1] == 0


def test_crossroads_signals_and_columns():
    indicator = CrossRoadsIndicator()

    df = pd.DataFrame(
        {
            "close": [
                10,
                10,
                10,
                20,
                20,
                20,
                5,
                5,
                5,
                25,
                25,
                25,
                8,
                8,
                8,
            ]
        }
    )

    result = indicator.compute(
        df,
        {
            "start_len": 0,
            "lookback_period": 3,
        },
    )

    expected_columns = {
        "crossroads_green",
        "crossroads_magenta",
        "crossroads_fast",
        "crossroads_slow",
        "crossroads_signal",
        "crossroads_trend",
    }

    assert expected_columns.issubset(set(result.columns))

    # Aliases must match the primary line outputs.
    pd.testing.assert_series_equal(
        result["crossroads_fast"],
        result["crossroads_green"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        result["crossroads_slow"],
        result["crossroads_magenta"],
        check_names=False,
    )

    # Signal outputs must use the engine convention.
    assert set(result["crossroads_signal"].dropna().unique()).issubset({-1, 0, 1})
    assert set(result["crossroads_trend"].dropna().unique()).issubset({-1, 0, 1})
    
    # There should be at least one valid calculated line value after warmup.
    assert result["crossroads_green"].notna().any()
    assert result["crossroads_magenta"].notna().any()