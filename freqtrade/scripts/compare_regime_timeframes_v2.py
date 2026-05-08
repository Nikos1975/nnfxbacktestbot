from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_BASE_COLUMNS = {
    "strategy",
    "pair",
    "entry_regime",
    "trades",
    "win_rate_pct",
    "sum_profit_ratio_pct",
    "avg_profit_ratio_pct",
    "median_profit_ratio_pct",
    "avg_win_pct",
    "avg_loss_pct",
    "avg_duration_min",
}


def infer_timeframe_from_filename(path: Path) -> str:
    name = path.name.lower()

    if "1h" in name:
        return "1h"
    if "4h" in name:
        return "4h"
    if "1d" in name:
        return "1d"

    # Your original daily file is named regime_performance_MAX_summary.csv.
    if name == "regime_performance_max_summary.csv":
        return "1d"

    return "unknown"


def read_summary(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    missing = REQUIRED_BASE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    if "timeframe" not in df.columns:
        df["timeframe"] = infer_timeframe_from_filename(path)

    if (df["timeframe"] == "unknown").any():
        print(f"Warning: could not infer timeframe for {path}. Set to 'unknown'.")

    return df


def expectancy_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["avg_loss_abs_pct"] = out["avg_loss_pct"].abs()
    out["win_loss_ratio"] = out["avg_win_pct"] / out["avg_loss_abs_pct"].replace(0, pd.NA)

    out["roi_exit_suspect"] = out["median_profit_ratio_pct"].between(1.85, 2.15, inclusive="both")
    out["enough_trades"] = out["trades"] >= 30
    out["positive_sum"] = out["sum_profit_ratio_pct"] > 0
    out["positive_avg"] = out["avg_profit_ratio_pct"] > 0
    out["loss_larger_than_win"] = out["avg_loss_abs_pct"] > out["avg_win_pct"]

    out["quality_score"] = 0
    out.loc[out["enough_trades"], "quality_score"] += 1
    out.loc[out["positive_sum"], "quality_score"] += 2
    out.loc[out["positive_avg"], "quality_score"] += 1
    out.loc[out["win_rate_pct"] >= 55, "quality_score"] += 1
    out.loc[out["win_loss_ratio"] >= 0.75, "quality_score"] += 1
    out.loc[out["roi_exit_suspect"], "quality_score"] -= 1
    out.loc[out["loss_larger_than_win"], "quality_score"] -= 1

    return out


def load_all(inputs: list[Path]) -> pd.DataFrame:
    frames = []
    for p in inputs:
        df = read_summary(p)
        frames.append(df)
    return expectancy_flags(pd.concat(frames, ignore_index=True))


def make_best_by_bucket(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.sort_values(
        ["pair", "entry_regime", "timeframe", "quality_score", "sum_profit_ratio_pct", "avg_profit_ratio_pct"],
        ascending=[True, True, True, False, False, False],
    )

    return (
        ranked.groupby(["pair", "entry_regime", "timeframe"], as_index=False)
        .head(5)
        .reset_index(drop=True)
    )


def make_survivors(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    survivors = df[
        (df["trades"] >= min_trades)
        & (df["sum_profit_ratio_pct"] > 0)
        & (df["avg_profit_ratio_pct"] > 0)
    ].copy()

    return survivors.sort_values(
        ["pair", "timeframe", "entry_regime", "quality_score", "sum_profit_ratio_pct"],
        ascending=[True, True, True, False, False],
    )


def make_timeframe_comparison(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (strategy, pair, timeframe), g in df.groupby(["strategy", "pair", "timeframe"]):
        total_trades = g["trades"].sum()
        weighted_avg = (
            (g["avg_profit_ratio_pct"] * g["trades"]).sum() / total_trades
            if total_trades
            else None
        )

        rows.append(
            {
                "strategy": strategy,
                "pair": pair,
                "timeframe": timeframe,
                "total_trades": int(total_trades),
                "total_sum_profit_ratio_pct": round(g["sum_profit_ratio_pct"].sum(), 2),
                "weighted_avg_profit_ratio_pct": round(weighted_avg, 4) if weighted_avg is not None else None,
                "avg_win_rate_pct": round(g["win_rate_pct"].mean(), 2),
                "avg_quality_score": round(g["quality_score"].mean(), 2),
                "roi_suspect_rows": int(g["roi_exit_suspect"].sum()),
                "positive_regime_rows": int((g["sum_profit_ratio_pct"] > 0).sum()),
                "negative_regime_rows": int((g["sum_profit_ratio_pct"] <= 0).sum()),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["pair", "total_sum_profit_ratio_pct"],
        ascending=[True, False],
    )


def make_regime_matrix(df: pd.DataFrame) -> pd.DataFrame:
    candidates = []

    for (pair, timeframe, regime), g in df.groupby(["pair", "timeframe", "entry_regime"]):
        valid = g[g["trades"] >= 30].copy()
        if valid.empty:
            valid = g.copy()

        best = valid.sort_values(
            ["quality_score", "sum_profit_ratio_pct", "avg_profit_ratio_pct"],
            ascending=[False, False, False],
        ).head(1)

        candidates.append(best)

    return pd.concat(candidates, ignore_index=True).sort_values(["pair", "timeframe", "entry_regime"])


def make_1h_vs_4h_delta(df: pd.DataFrame) -> pd.DataFrame:
    intraday = df[df["timeframe"].isin(["1h", "4h"])].copy()

    pivot = intraday.pivot_table(
        index=["strategy", "pair", "entry_regime"],
        columns="timeframe",
        values=["trades", "sum_profit_ratio_pct", "avg_profit_ratio_pct", "win_rate_pct"],
        aggfunc="first",
    )

    pivot.columns = [f"{metric}_{tf}" for metric, tf in pivot.columns]
    pivot = pivot.reset_index()

    if "sum_profit_ratio_pct_4h" in pivot.columns and "sum_profit_ratio_pct_1h" in pivot.columns:
        pivot["sum_profit_delta_1h_minus_4h"] = (
            pivot["sum_profit_ratio_pct_1h"] - pivot["sum_profit_ratio_pct_4h"]
        )
    if "avg_profit_ratio_pct_4h" in pivot.columns and "avg_profit_ratio_pct_1h" in pivot.columns:
        pivot["avg_profit_delta_1h_minus_4h"] = (
            pivot["avg_profit_ratio_pct_1h"] - pivot["avg_profit_ratio_pct_4h"]
        )

    return pivot.sort_values(
        ["pair", "entry_regime", "sum_profit_delta_1h_minus_4h"],
        ascending=[True, True, False],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--min-trades", type=int, default=30)
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_all(input_paths)

    outputs = {
        "step2_all_regime_results_with_flags.csv": df,
        "step2_best_by_pair_timeframe_regime.csv": make_best_by_bucket(df),
        "step2_survivors_min_trades.csv": make_survivors(df, args.min_trades),
        "step2_timeframe_comparison.csv": make_timeframe_comparison(df),
        "step2_regime_router_candidates.csv": make_regime_matrix(df),
        "step2_1h_vs_4h_delta.csv": make_1h_vs_4h_delta(df),
    }

    print("")
    print("Wrote:")
    for filename, frame in outputs.items():
        path = outdir / filename
        frame.to_csv(path, index=False)
        print(f"- {path}")

    print("")
    print("Top regime-router candidates:")
    print(outputs["step2_regime_router_candidates.csv"].to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
