from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULTS_ROOT = PROJECT_ROOT / "results" / "nnfx_crypto" / "backtests"


def list_runs() -> list[Path]:
    if not RESULTS_ROOT.exists():
        return []

    return sorted(
        [path for path in RESULTS_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    st.set_page_config(
        page_title="NNFX Crypto Backtest Viewer",
        layout="wide",
    )

    st.title("NNFX Crypto Backtest Viewer")

    runs = list_runs()

    if not runs:
        st.warning(f"No backtest runs found in: {RESULTS_ROOT}")
        return

    selected_name = st.sidebar.selectbox(
        "Backtest run",
        options=[run.name for run in runs],
    )

    run_dir = RESULTS_ROOT / selected_name

    st.sidebar.write("Selected run:")
    st.sidebar.code(str(run_dir))

    summary_path = run_dir / "summary.md"
    metrics_path = run_dir / "metrics.json"
    equity_chart_path = run_dir / "chart_equity_curve.png"
    price_chart_path = run_dir / "chart_price_signals.png"
    trades_path = run_dir / "trades.csv"
    equity_curve_path = run_dir / "equity_curve.csv"
    config_path = run_dir / "resolved_config.yml"
    report_path = run_dir / "report.html"

    tabs = st.tabs(
        [
            "Summary",
            "Metrics",
            "Charts",
            "Trades",
            "Equity Curve",
            "Config",
            "Files",
        ]
    )

    with tabs[0]:
        st.subheader("Summary")
        summary = load_text(summary_path)
        if summary:
            st.markdown(summary)
        else:
            st.info("No summary.md found.")

        if report_path.exists():
            st.markdown(f"HTML report path: `{report_path}`")

    with tabs[1]:
        st.subheader("Metrics")
        metrics = load_json(metrics_path)

        if metrics:
            metric_items = list(metrics.items())
            cols = st.columns(4)

            for index, (key, value) in enumerate(metric_items):
                with cols[index % 4]:
                    st.metric(label=str(key), value=str(value))

            st.divider()
            st.json(metrics)
        else:
            st.info("No metrics.json found.")

    with tabs[2]:
        st.subheader("Charts")

        if equity_chart_path.exists():
            st.markdown("### Equity Curve")
            st.image(str(equity_chart_path), use_container_width=True)
        else:
            st.info("No chart_equity_curve.png found.")

        if price_chart_path.exists():
            st.markdown("### Price Signals")
            st.image(str(price_chart_path), use_container_width=True)
        else:
            st.info("No chart_price_signals.png found.")

    with tabs[3]:
        st.subheader("Trades")
        trades = load_csv(trades_path)

        if trades.empty:
            st.info("No trades.csv found or file is empty.")
        else:
            st.write(f"Rows: {len(trades)}")
            st.dataframe(trades, use_container_width=True)

            csv_bytes = trades.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download trades.csv",
                data=csv_bytes,
                file_name="trades.csv",
                mime="text/csv",
            )

    with tabs[4]:
        st.subheader("Equity Curve Data")
        equity_curve = load_csv(equity_curve_path)

        if equity_curve.empty:
            st.info("No equity_curve.csv found or file is empty.")
        else:
            st.write(f"Rows: {len(equity_curve)}")
            st.dataframe(equity_curve, use_container_width=True)

    with tabs[5]:
        st.subheader("Resolved Config")
        config_text = load_text(config_path)

        if config_text:
            try:
                parsed = yaml.safe_load(config_text)
                st.json(parsed)
            except Exception:
                st.code(config_text, language="yaml")
        else:
            st.info("No resolved_config.yml found.")

    with tabs[6]:
        st.subheader("Run Files")
        files = sorted(run_dir.iterdir())

        file_rows = [
            {
                "name": file.name,
                "size_bytes": file.stat().st_size,
                "modified": file.stat().st_mtime,
            }
            for file in files
            if file.is_file()
        ]

        st.dataframe(pd.DataFrame(file_rows), use_container_width=True)


if __name__ == "__main__":
    main()