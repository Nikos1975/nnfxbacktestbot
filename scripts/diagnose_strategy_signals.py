import argparse
import sys
from pathlib import Path
import pandas as pd

# Add src to path so we can import backtest logic
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.config.loader import load_strategy_config
from nnfx_crypto.data.ohlcv_loader import load_ohlcv_csv
from nnfx_crypto.signals.nnfx_signal_engine import NNFXSignalEngine


def diagnose(config_path: str):
    config = load_strategy_config(config_path)
    print(f"Diagnosing config: {config.strategy.name}")
    
    df = load_ohlcv_csv(config.data.path)
    print(f"Loaded {len(df)} rows from {config.data.path}")
    
    if df.empty:
        print("Error: DataFrame is empty. Check data path and dates.")
        return
        
    engine = NNFXSignalEngine(config)
    
    # Process indicators
    try:
        df_ind = engine.compute_indicators(df)
    except Exception as e:
        print(f"Error computing indicators: {e}")
        return
        
    print("\n--- Indicator Signal Counts ---")
    
    def print_counts(col_name: str, desc: str):
        if col_name in df_ind.columns:
            counts = df_ind[col_name].value_counts().to_dict()
            print(f"{desc} ({col_name}):")
            for k, v in sorted(counts.items()):
                print(f"  {k}: {v}")
        else:
            print(f"{desc} ({col_name}): NOT FOUND")

    print_counts("baseline_signal", "Baseline")
    print_counts("c1_signal", "C1 Confirmation")
    print_counts("c2_signal", "C2 Confirmation")
    print_counts("volume_or_volatility_filter_pass_long", "Volume/Vol Long Pass")
    print_counts("volume_or_volatility_filter_pass_short", "Volume/Vol Short Pass")
    print_counts("exit_signal", "Exit Signal")
    
    print("\n--- Entry Agreement Diagnosis ---")
    
    # Baseline direction (-1, 1)
    baseline_long = df_ind.get("baseline_signal", pd.Series(0, index=df_ind.index)) == 1
    baseline_short = df_ind.get("baseline_signal", pd.Series(0, index=df_ind.index)) == -1
    
    # C1 / C2 Agreement
    c1_long = df_ind.get("c1_signal", pd.Series(0, index=df_ind.index)) == 1
    c1_short = df_ind.get("c1_signal", pd.Series(0, index=df_ind.index)) == -1
    
    c2_long = df_ind.get("c2_signal", pd.Series(0, index=df_ind.index)) == 1
    c2_short = df_ind.get("c2_signal", pd.Series(0, index=df_ind.index)) == -1
    
    # Vol Filter
    vol_long = df_ind.get("volume_or_volatility_filter_pass_long", pd.Series(True, index=df_ind.index)) == True
    vol_short = df_ind.get("volume_or_volatility_filter_pass_short", pd.Series(True, index=df_ind.index)) == True

    # Baseline cross event (usually we enter on the bar the baseline crosses or C1 crosses)
    # This is a simplified check to see if all conditions align AT ALL.
    long_agreement = baseline_long & c1_long & c2_long & vol_long
    short_agreement = baseline_short & c1_short & c2_short & vol_short
    
    print(f"Total rows where ALL Long conditions agree: {long_agreement.sum()}")
    print(f"Total rows where ALL Short conditions agree: {short_agreement.sum()}")
    
    if long_agreement.sum() == 0 and short_agreement.sum() == 0:
        print("\nWARNING: Your indicators NEVER align to create an entry signal.")
        print("Check if C1 and C2 are producing sparse crossover signals (+1/-1) instead of sustained trend signals.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose NNFX strategy signals.")
    parser.add_argument("--config", type=str, required=True, help="Path to the config file.")
    args = parser.parse_args()
    
    diagnose(args.config)
