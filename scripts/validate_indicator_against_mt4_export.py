import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path so we can import nnfx_crypto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
try:
    from nnfx_crypto.indicators.registry import get_indicator
except ImportError:
    # Fallback/mock if imported in a weird environment
    def get_indicator(name):
        raise ValueError("Could not import get_indicator from src.nnfx_crypto.indicators.registry")


def validate(csv_path: str, indicator_name: str, params: dict, output_col: str, csv_output_col: str):
    """
    Validates a Python indicator against a CSV exported from MT4.
    """
    df = pd.read_csv(csv_path)
    
    # Ensure standard column names
    rename_map = {
        'Date': 'Date', 'Time': 'Time',
        '<DATE>': 'Date', '<TIME>': 'Time',
        '<OPEN>': 'Open', '<HIGH>': 'High', '<LOW>': 'Low', '<CLOSE>': 'Close', '<TICKVOL>': 'Volume', '<VOL>': 'Volume'
    }
    df.rename(columns=lambda x: rename_map.get(x.strip(), x.strip()), inplace=True)
    
    if 'Datetime' not in df.columns:
        if 'Date' in df.columns and 'Time' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        elif 'Date' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Date'])
    
    if csv_output_col not in df.columns:
        print(f"Error: Expected MT4 output column '{csv_output_col}' not found in CSV. Available: {list(df.columns)}")
        return

    # Run Python indicator
    try:
        indicator = get_indicator(indicator_name)
        df_out = indicator.compute(df, params)
    except Exception as e:
        print(f"Error running indicator '{indicator_name}': {e}")
        return
        
    if output_col not in df_out.columns:
        print(f"Error: Python indicator did not produce expected column '{output_col}'. Available: {list(df_out.columns)}")
        return

    # Compare
    mt4_series = df[csv_output_col].astype(float)
    py_series = df_out[output_col].astype(float)
    
    # Align where neither is NaN
    valid_idx = mt4_series.notna() & py_series.notna()
    
    if not valid_idx.any():
        print("No valid overlapping data points found to compare.")
        return
        
    mt4_valid = mt4_series[valid_idx]
    py_valid = py_series[valid_idx]
    
    mae = np.mean(np.abs(mt4_valid - py_valid))
    max_ae = np.max(np.abs(mt4_valid - py_valid))
    
    try:
        corr = np.corrcoef(mt4_valid, py_valid)[0, 1]
    except Exception:
        corr = np.nan
        
    mismatches = np.sum(np.abs(mt4_valid - py_valid) > 1e-5)
    
    print(f"--- Validation Results for {indicator_name} ---")
    print(f"Points compared : {valid_idx.sum()}")
    print(f"MAE             : {mae:.6f}")
    print(f"Max AE          : {max_ae:.6f}")
    print(f"Correlation     : {corr:.6f}")
    print(f"Mismatches      : {mismatches} (diff > 1e-5)")
    
    if mismatches > 0:
        print("\nFirst 5 mismatches:")
        diff = np.abs(mt4_valid - py_valid)
        mismatch_idx = diff[diff > 1e-5].head(5).index
        for idx in mismatch_idx:
            dt = df['Datetime'].iloc[idx] if 'Datetime' in df.columns else idx
            print(f"  Row {idx} ({dt}): MT4={mt4_series.iloc[idx]:.6f}, Python={py_series.iloc[idx]:.6f}, Diff={diff.loc[idx]:.6f}")


def main():
    parser = argparse.ArgumentParser(description="Validate Python indicator vs MT4 CSV export.")
    parser.add_argument("--csv", type=str, required=True, help="Path to MT4 CSV export.")
    parser.add_argument("--indicator", type=str, required=True, help="Name of Python indicator in registry.")
    parser.add_argument("--params", type=str, default="{}", help="JSON string of parameters for the python indicator.")
    parser.add_argument("--py-col", type=str, required=True, help="The output column produced by the Python indicator.")
    parser.add_argument("--mt4-col", type=str, required=True, help="The output column in the MT4 CSV.")
    
    args = parser.parse_args()
    
    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"Error parsing params JSON: {e}")
        return
        
    validate(args.csv, args.indicator, params, args.py_col, args.mt4_col)


if __name__ == "__main__":
    main()
