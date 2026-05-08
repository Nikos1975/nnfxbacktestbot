from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "strategy",
    "pair",
    "timeframe",
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


def read_summary(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
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
    merged = pd.concat(frames, ignore_index=True)
    return expectancy_flags(merged)


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

    survivors = survivors.sort_values(
        ["pair", "timeframe", "entry_regime", "quality_score", "sum_profit_ratio_pct"],
        ascending=[True, True, True, False, False],
    )

    return survivors


def make_timeframe_comparison(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["strategy", "pair", "timeframe"], as_index=False)
        .agg(
            total_trades=("trades", "sum"),
            total_sum_profit_ratio_pct=("sum_profit_ratio_pct", "sum"),
            weighted_avg_profit_ratio_pct=(
                "avg_profit_ratio_pct",
                lambda s: None,
            ),
            avg_win_rate_pct=("win_rate_pct", "mean"),
            avg_quality_score=("quality_score", "mean"),
            roi_suspect_rows=("roi_exit_suspect", "sum"),
        )
    )

    # Correct weighted average after groupby because lambda above lacks access to trades.
    weighted_rows = []
    for (strategy, pair, timeframe), g in df.groupby(["strategy", "pair", "timeframe"]):
        total_trades = g["trades"].sum()
        weighted_avg = (
            (g["avg_profit_ratio_pct"] * g["trades"]).sum() / total_trades
            if total_trades
            else None
        )
        weighted_rows.append(
            {
                "strategy": strategy,
                "pair": pair,
                "timeframe": timeframe,
                "weighted_avg_profit_ratio_pct": round(weighted_avg, 4) if weighted_avg is not None else None,
            }
        )

    weighted = pd.DataFrame(weighted_rows)
    grouped = grouped.drop(columns=["weighted_avg_profit_ratio_pct"]).merge(
        weighted,
        on=["strategy", "pair", "timeframe"],
        how="left",
    )

    return grouped.sort_values(
        ["pair", "total_sum_profit_ratio_pct"],
        ascending=[True, False],
    )


def make_regime_matrix(df: pd.DataFrame) -> pd.DataFrame:
    # Best strategy per pair/timeframe/regime.
    idx = (
        df.sort_values(["quality_score", "sum_profit_ratio_pct"], ascending=[False, False])
        .groupby(["pair", "timeframe", "entry_regime"])
        .head(1)
        .index
    )
    return df.loc[idx].sort_values(["pair", "timeframe", "entry_regime"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Summary CSVs, e.g. 1d, 4h, 1h regime_performance summary files.",
    )
    parser.add_argument(
        "--outdir",
        required=True,
        help="Output directory for comparison CSVs.",
    )
    parser.add_argument("--min-trades", type=int, default=30)
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_all(input_paths)

    all_path = outdir / "step2_all_regime_results_with_flags.csv"
    best_path = outdir / "step2_best_by_pair_timeframe_regime.csv"
    survivors_path = outdir / "step2_survivors_min_trades.csv"
    timeframe_path = outdir / "step2_timeframe_comparison.csv"
    matrix_path = outdir / "step2_regime_router_candidates.csv"

    df.to_csv(all_path, index=False)
    make_best_by_bucket(df).to_csv(best_path, index=False)
    make_survivors(df, args.min_trades).to_csv(survivors_path, index=False)
    make_timeframe_comparison(df).to_csv(timeframe_path, index=False)
    make_regime_matrix(df).to_csv(matrix_path, index=False)

    print("")
    print("Wrote:")
    print(f"- {all_path}")
    print(f"- {best_path}")
    print(f"- {survivors_path}")
    print(f"- {timeframe_path}")
    print(f"- {matrix_path}")

    print("")
    print("Top regime-router candidates:")
    print(make_regime_matrix(df).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
