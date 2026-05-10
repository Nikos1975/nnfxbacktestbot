import json
from pathlib import Path
import pandas as pd
import numpy as np

def generate_distance_analysis(trades_df: pd.DataFrame, run_dir: Path) -> None:
    if trades_df.empty:
        return
        
    buckets = []
    
    # Analyze Percentage Distances
    pct_cols = [c for c in trades_df.columns if c.startswith("entry_distance_sma_") and c.endswith("_pct")]
    for col in pct_cols:
        sma_name = col.replace("entry_distance_", "").replace("_pct", "")
        # Buckets: below_-10pct, -10pct_to_-5pct, -5pct_to_-2pct, -2pct_to_0, 0_to_2pct, 2pct_to_5pct, 5pct_to_10pct, above_10pct
        bins = [-np.inf, -0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.10, np.inf]
        labels = [
            "below_-10pct", "-10pct_to_-5pct", "-5pct_to_-2pct", "-2pct_to_0",
            "0_to_2pct", "2pct_to_5pct", "5pct_to_10pct", "above_10pct"
        ]
        _process_bucket(trades_df, col, bins, labels, sma_name, "percentage", buckets)
        
    # Analyze ATR Distances
    atr_cols = [c for c in trades_df.columns if c.startswith("entry_distance_sma_") and c.endswith("_atr")]
    for col in atr_cols:
        sma_name = col.replace("entry_distance_", "").replace("_atr", "")
        # Buckets: below_-3atr, -3atr_to_-2atr, -2atr_to_-1atr, -1atr_to_0, 0_to_1atr, 1atr_to_2atr, 2atr_to_3atr, above_3atr
        bins = [-np.inf, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, np.inf]
        labels = [
            "below_-3atr", "-3atr_to_-2atr", "-2atr_to_-1atr", "-1atr_to_0",
            "0_to_1atr", "1atr_to_2atr", "2atr_to_3atr", "above_3atr"
        ]
        _process_bucket(trades_df, col, bins, labels, sma_name, "atr", buckets)
        
    if not buckets:
        return
        
    results_df = pd.DataFrame(buckets)
    results_df.to_csv(run_dir / "ma_distance_analysis.csv", index=False)
    
    # Save as JSON tree: distance_type -> sma_name -> bucket_name -> stats
    json_data = {}
    for t in results_df["distance_type"].unique():
        json_data[t] = {}
        t_df = results_df[results_df["distance_type"] == t]
        for s in t_df["sma_name"].unique():
            json_data[t][s] = {}
            s_df = t_df[t_df["sma_name"] == s]
            for _, row in s_df.iterrows():
                row_dict = row.to_dict()
                bucket_name = row_dict.pop("bucket")
                # Remove redundant keys
                row_dict.pop("distance_type")
                row_dict.pop("sma_name")
                json_data[t][s][bucket_name] = row_dict
                
    with open(run_dir / "ma_distance_analysis.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)


def _process_bucket(df: pd.DataFrame, col: str, bins: list, labels: list, sma_name: str, dist_type: str, buckets: list) -> None:
    # Safely calculate durations
    if "entry_time" in df.columns and "exit_time" in df.columns:
        entry = pd.to_datetime(df["entry_time"], errors="coerce")
        exit_ = pd.to_datetime(df["exit_time"], errors="coerce")
        durations = (exit_ - entry).dt.total_seconds() / 3600.0
    else:
        durations = pd.Series(0, index=df.index)
        
    df = df.copy()
    df["_bucket"] = pd.cut(df[col], bins=bins, labels=labels, right=False)
    df["_duration"] = durations
    
    for label in labels:
        b_df = df[df["_bucket"] == label]
        
        trade_count = len(b_df)
        net_pnl = float(b_df["pnl"].sum()) if trade_count else 0.0
        wins = b_df[b_df["pnl"] > 0]
        losses = b_df[b_df["pnl"] < 0]
        gross_win = float(wins["pnl"].sum()) if not wins.empty else 0.0
        gross_loss = abs(float(losses["pnl"].sum())) if not losses.empty else 0.0
        
        buckets.append({
            "distance_type": dist_type,
            "sma_name": sma_name,
            "bucket": label,
            "trade_count": trade_count,
            "net_pnl": net_pnl,
            "win_rate": float(len(wins) / trade_count) if trade_count else 0.0,
            "average_pnl": float(net_pnl / trade_count) if trade_count else 0.0,
            "profit_factor": float(gross_win / gross_loss) if gross_loss else 0.0,
            "average_duration": float(b_df["_duration"].mean()) if trade_count and b_df["_duration"].notna().any() else 0.0,
            "long_count": int((b_df["side"] == "long").sum()),
            "short_count": int((b_df["side"] == "short").sum()),
        })
