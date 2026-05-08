import json
import os
import sys
import tempfile
import textwrap
from pathlib import Path

import pandas as pd
import pytest

# Add the project root to sys.path so we can import from scripts and src
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.inspect_mq4_indicator import parse_mq4
import scripts.generate_indicator_skeleton as generate_indicator
import scripts.validate_indicator_against_mt4_export as validate_indicator


@pytest.fixture
def sample_mq4_content():
    return textwrap.dedent("""
    #property indicator_buffers 2
    extern double MyParam1 = 1.5;
    input int MyParam2 = 14;
    
    int start() {
        SetIndexBuffer(0, myBuffer);
        double val = iMA(NULL, 0, MyParam2, 0, MODE_SMA, PRICE_CLOSE, 0);
        return 0;
    }
    """)


def test_mq4_parser_extracts_metadata(sample_mq4_content):
    metadata = parse_mq4(sample_mq4_content)
    
    assert metadata["buffers"] == 2
    assert "iMA" in metadata["indicator_calls"]
    assert "Uses SetIndexBuffer" in metadata["sections"]
    assert "Has OnCalculate/start logic" in metadata["sections"]
    assert len(metadata["parameters"]) == 2
    
    params = {p["name"]: p for p in metadata["parameters"]}
    assert "MyParam1" in params
    assert params["MyParam1"]["type"] == "double"
    assert params["MyParam1"]["default"] == "1.5"
    
    assert "MyParam2" in params
    assert params["MyParam2"]["type"] == "int"
    assert params["MyParam2"]["default"] == "14"


def test_mq4_parser_rejects_ex4_content():
    # Simulate binary EX4
    content = "MZ\x00\x00\x00\x00"
    metadata = parse_mq4(content)
    assert any("compiled binary" in w for w in metadata["warnings"])


def test_generate_indicator_skeleton(sample_mq4_content, tmp_path):
    mq4_file = tmp_path / "test.mq4"
    mq4_file.write_text(sample_mq4_content)
    
    # Override args and run main
    test_args = ["generate_indicator_skeleton.py", "--mq4", str(mq4_file), "--name", "TestInd", "--outdir", str(tmp_path)]
    
    original_argv = sys.argv
    sys.argv = test_args
    try:
        generate_indicator.main()
    finally:
        sys.argv = original_argv
        
    out_file = tmp_path / "testind.py"
    assert out_file.exists()
    
    py_content = out_file.read_text()
    assert "class TestIndIndicator(Indicator):" in py_content
    assert "TestIndConfig" in py_content
    assert "MyParam1: float = 1.5" in py_content
    assert "MyParam2: int = 14" in py_content
    assert "Output Buffers expected: 2" in py_content


def test_validation_harness(tmp_path, capsys):
    # Create mock CSV
    df = pd.DataFrame({
        "Date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "Time": ["00:00", "00:00", "00:00"],
        "Open": [10, 11, 12],
        "High": [12, 13, 14],
        "Low": [9, 10, 11],
        "Close": [11, 12, 13],
        "Volume": [100, 110, 120],
        "MT4_Out": [1.1, 1.2, 1.3]
    })
    csv_path = tmp_path / "test.csv"
    df.to_csv(csv_path, index=False)
    
    # Mock Python indicator to return matching and mismatching values.
    class MockIndicator:
        def compute(self, input_df, params):
            out_df = input_df.copy()
            # Let's make one value mismatch
            out_df["Py_Out"] = [1.1, 1.2, 9.9]
            return out_df
            
    # Patch get_indicator
    original_get = validate_indicator.get_indicator
    validate_indicator.get_indicator = lambda name: MockIndicator()
    
    try:
        validate_indicator.validate(
            csv_path=str(csv_path),
            indicator_name="mock",
            params={},
            output_col="Py_Out",
            csv_output_col="MT4_Out"
        )
    finally:
        validate_indicator.get_indicator = original_get
        
    captured = capsys.readouterr()
    assert "Mismatches      : 1" in captured.out
    assert "MT4=1.300000, Python=9.900000" in captured.out
