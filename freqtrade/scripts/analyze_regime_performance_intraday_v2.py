from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


INTERVAL_TO_MS = {
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}


@dataclass(frozen=True)
class RegimeConfig:
    ema_period: int = 200
    ema_slope_period: int = 10
    adx_period: int = 14
    chop_period: int = 14
    trend_adx_min: float = 20.0
    trend_chop_max: float = 55.0
    consolidation_adx_max: float = 20.0
    consolidation_chop_min: float = 55.0


def parse_dt(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        unit = "ms" if value > 10_000_000_000 else "s"
        return pd.to_datetime(value, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(str(value), utc=True, errors="coerce")


def safe_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return math.nan
        return float(value)
    except Exception:
        return math.nan


def read_meta_for_zip(zip_path: Path) -> dict[str, Any]:
    meta_path = zip_path.with_suffix(".meta.json")
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_json_from_zip(path: Path) -> list[tuple[str, Any]]:
    loaded: list[tuple[str, Any]] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                lower = name.lower()
                if not lower.endswith(".json"):
                    continue
                if "config" in lower or "strategy" in lower or "params" in lower:
                    continue
                try:
                    with zf.open(name) as fh:
                        loaded.append((f"{path.name}:{name}", json.loads(fh.read().decode("utf-8"))))
                except Exception as exc:
                    print(f"Skipping JSON inside {path.name}/{name}: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"Skipping unreadable ZIP {path}: {exc}", file=sys.stderr)
    return loaded


def infer_timeframe_from_data(data: Any, meta: dict[str, Any]) -> str | None:
    # Try meta first.
    for key in ("timeframe", "timeframes"):
        val = meta.get(key)
        if isinstance(val, str):
            return val
        if isinstance(val, list) and val:
            return str(val[0])

    # Try common result/config locations.
    if isinstance(data, dict):
        for key in ("timeframe", "timeframes"):
            val = data.get(key)
            if isinstance(val, str):
                return val
            if isinstance(val, list) and val:
                return str(val[0])

        config = data.get("config")
        if isinstance(config, dict):
            val = config.get("timeframe")
            if isinstance(val, str):
                return val

        # Sometimes result dict is nested by strategy.
        for value in data.values():
            if isinstance(value, dict):
                tf = infer_timeframe_from_data(value, {})
                if tf:
                    return tf

    return None


def infer_strategy_name(source_name: str, data: Any, meta: dict[str, Any]) -> str:
    for key in ("strategy", "strategy_name"):
        val = meta.get(key)
        if isinstance(val, str):
            return val

    if isinstance(data, dict):
        val = data.get("strategy")
        if isinstance(val, str):
            return val

        strategy_comparison = data.get("strategy_comparison")
        if isinstance(strategy_comparison, list) and strategy_comparison:
            name = strategy_comparison[0].get("key") or strategy_comparison[0].get("strategy")
            if name:
                return str(name)

        for key in data.keys():
            if str(key).startswith("Nnfx") or str(key) == "RegimeFilteredStrategy":
                return str(key)

    return Path(source_name.split(":")[0]).stem


def find_trade_lists(obj: Any) -> list[list[dict[str, Any]]]:
    found: list[list[dict[str, Any]]] = []

    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        keys = set().union(*(x.keys() for x in obj[: min(5, len(obj))]))
        trade_like_keys = {
            "pair",
            "open_date",
            "open_date_utc",
            "open_timestamp",
            "close_date",
            "close_timestamp",
            "profit_ratio",
            "profit_abs",
            "close_profit_abs",
            "trade_duration",
        }
        if "pair" in keys and len(keys & trade_like_keys) >= 3:
            found.append(obj)

    if isinstance(obj, dict):
        for value in obj.values():
            if isinstance(value, (dict, list)):
                found.extend(find_trade_lists(value))
    elif isinstance(obj, list):
        for value in obj:
            if isinstance(value, (dict, list)):
                found.extend(find_trade_lists(value))

    return found


def load_trades(export_dir: Path, timeframe: str, since_minutes: int | None) -> pd.DataFrame:
    paths = sorted(export_dir.glob("backtest-result-*.zip"))

    if since_minutes is not None:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=since_minutes)
        paths = [
            p for p in paths
            if pd.Timestamp.fromtimestamp(p.stat().st_mtime, tz="UTC") >= cutoff
        ]

    rows: list[dict[str, Any]] = []

    for path in paths:
        meta = read_meta_for_zip(path)
        loaded_items = load_json_from_zip(path)

        for source_name, data in loaded_items:
            inferred_tf = infer_timeframe_from_data(data, meta)
            if inferred_tf and inferred_tf != timeframe:
                continue

            strategy_name = infer_strategy_name(source_name, data, meta)

            for trades in find_trade_lists(data):
                for t in trades:
                    open_time = (
                        t.get("open_date")
                        or t.get("open_date_utc")
                        or t.get("open_timestamp")
                        or t.get("open_time")
                    )
                    close_time = (
                        t.get("close_date")
                        or t.get("close_date_utc")
                        or t.get("close_timestamp")
                        or t.get("close_time")
                    )
                    profit_ratio = (
                        t.get("profit_ratio")
                        if t.get("profit_ratio") is not None
                        else t.get("close_profit")
                    )
                    profit_abs = (
                        t.get("profit_abs")
                        if t.get("profit_abs") is not None
                        else t.get("close_profit_abs")
                    )

                    rows.append(
                        {
                            "source_file": source_name,
                            "zip_file": path.name,
                            "strategy": strategy_name,
                            "pair": t.get("pair"),
                            "timeframe": timeframe,
                            "open_date": parse_dt(open_time),
                            "close_date": parse_dt(close_time),
                            "profit_ratio": safe_float(profit_ratio),
                            "profit_abs": safe_float(profit_abs),
                            "duration_min": safe_float(t.get("trade_duration")),
                            "is_open": bool(t.get("is_open", False)),
                        }
                    )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.dropna(subset=["pair", "open_date"])


def binance_symbol(pair: str) -> str:
    return pair.replace("/", "").replace(":", "")


def floor_to_timeframe(ts: pd.Series, timeframe: str) -> pd.Series:
    if timeframe == "1d":
        return ts.dt.floor("D")
    if timeframe == "4h":
        return ts.dt.floor("4h")
    if timeframe == "1h":
        return ts.dt.floor("h")
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def download_binance_ohlcv(pair: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    if timeframe not in INTERVAL_TO_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    symbol = binance_symbol(pair)
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
    step_ms = INTERVAL_TO_MS[timeframe]

    rows: list[list[Any]] = []
    current = start_ms

    while current < end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "interval": timeframe,
                "startTime": current,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        url = f"https://api.binance.com/api/v3/klines?{params}"
        with urllib.request.urlopen(url, timeout=30) as response:
            batch = json.loads(response.read().decode("utf-8"))

        if not batch:
            break

        rows.extend(batch)
        current = int(batch[-1][0]) + step_ms

    if not rows:
        raise RuntimeError(f"No Binance data returned for {pair} {timeframe}")

    df = pd.DataFrame(
        rows,
        columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ],
    )

    df["bar_time"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[["bar_time", "open", "high", "low", "close", "volume"]].dropna()


def add_regimes(df: pd.DataFrame, cfg: RegimeConfig) -> pd.DataFrame:
    out = df.copy()
    out["ema"] = out["close"].ewm(span=cfg.ema_period, adjust=False, min_periods=cfg.ema_period).mean()
    out["ema_slope"] = out["ema"].diff(cfg.ema_slope_period)

    high = out["high"]
    low = out["low"]
    close = out["close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=out.index)
    minus_dm = pd.Series(0.0, index=out.index)

    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move

    atr = tr.ewm(alpha=1 / cfg.adx_period, adjust=False, min_periods=cfg.adx_period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / cfg.adx_period, adjust=False, min_periods=cfg.adx_period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / cfg.adx_period, adjust=False, min_periods=cfg.adx_period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    out["adx"] = dx.ewm(alpha=1 / cfg.adx_period, adjust=False, min_periods=cfg.adx_period).mean()

    atr_sum = tr.rolling(cfg.chop_period, min_periods=cfg.chop_period).sum()
    high_max = high.rolling(cfg.chop_period, min_periods=cfg.chop_period).max()
    low_min = low.rolling(cfg.chop_period, min_periods=cfg.chop_period).min()
    ratio = atr_sum / (high_max - low_min).replace(0, pd.NA)
    out["chop"] = 100 * ratio.apply(
        lambda x: math.log10(x) if pd.notna(x) and x > 0 else math.nan
    ) / math.log10(cfg.chop_period)

    out["regime"] = "TRANSITION"

    uptrend = (
        (out["close"] > out["ema"])
        & (out["ema_slope"] > 0)
        & (out["adx"] >= cfg.trend_adx_min)
        & (out["chop"] < cfg.trend_chop_max)
    )

    downtrend = (
        (out["close"] < out["ema"])
        & (out["ema_slope"] < 0)
        & (out["adx"] >= cfg.trend_adx_min)
        & (out["chop"] < cfg.trend_chop_max)
    )

    consolidating = (
        (out["adx"] < cfg.consolidation_adx_max)
        | (out["chop"] >= cfg.consolidation_chop_min)
    )

    out.loc[consolidating, "regime"] = "CONSOLIDATING"
    out.loc[uptrend, "regime"] = "UPTREND"
    out.loc[downtrend, "regime"] = "DOWNTREND"

    return out


def summarize(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (strategy, pair, timeframe, regime), g in trades.groupby(
        ["strategy", "pair", "timeframe", "entry_regime"], dropna=False
    ):
        profits = g["profit_ratio"].dropna()
        wins = profits[profits > 0]
        losses = profits[profits < 0]

        rows.append(
            {
                "strategy": strategy,
                "pair": pair,
                "timeframe": timeframe,
                "entry_regime": regime,
                "trades": len(g),
                "win_rate_pct": round(100 * len(wins) / len(profits), 2) if len(profits) else None,
                "sum_profit_ratio_pct": round(100 * profits.sum(), 2) if len(profits) else None,
                "avg_profit_ratio_pct": round(100 * profits.mean(), 3) if len(profits) else None,
                "median_profit_ratio_pct": round(100 * profits.median(), 3) if len(profits) else None,
                "avg_win_pct": round(100 * wins.mean(), 3) if len(wins) else None,
                "avg_loss_pct": round(100 * losses.mean(), 3) if len(losses) else None,
                "avg_duration_min": round(g["duration_min"].dropna().mean(), 1)
                if g["duration_min"].notna().any()
                else None,
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["pair", "timeframe", "entry_regime", "sum_profit_ratio_pct"],
        ascending=[True, True, True, False],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeframe", required=True, choices=["1h", "4h", "1d"])
    parser.add_argument("--start", default="2017-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--since-minutes", type=int, default=None, help="Only inspect result zips modified in the last N minutes.")
    args = parser.parse_args()

    start = args.start
    end = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    export_dir = Path(args.exports)

    trades = load_trades(export_dir, args.timeframe, args.since_minutes)

    if trades.empty:
        print("No matching trades found.", file=sys.stderr)
        print("Use --since-minutes only if you recently ran the target timeframe.", file=sys.stderr)
        print("Or run backtests again before analyzing.", file=sys.stderr)
        return 3

    trades["entry_bar_time"] = floor_to_timeframe(trades["open_date"], args.timeframe)

    regime_frames = []
    for pair in sorted(trades["pair"].dropna().unique()):
        print(f"Downloading/classifying regimes for {pair} {args.timeframe} from {start} to {end}...")
        ohlcv = download_binance_ohlcv(pair, args.timeframe, start, end)
        regimes = add_regimes(ohlcv, RegimeConfig())
        regimes["pair"] = pair
        regime_frames.append(regimes[["pair", "bar_time", "regime", "adx", "chop", "ema_slope"]])

    regimes_all = pd.concat(regime_frames, ignore_index=True)

    merged = trades.merge(
        regimes_all,
        left_on=["pair", "entry_bar_time"],
        right_on=["pair", "bar_time"],
        how="left",
    )
    merged["entry_regime"] = merged["regime"].fillna("UNKNOWN")

    summary = summarize(merged)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False)

    detail_path = out_path.with_name(out_path.stem + "_trades.csv")
    merged.to_csv(detail_path, index=False)

    print("")
    print("Wrote:")
    print(f"- {out_path}")
    print(f"- {detail_path}")
    print("")
    print(summary.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
