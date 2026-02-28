"""Score trend chart — matplotlib line chart from SQLite history."""

import os
import sys

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — works without display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def plot_score_history(histories, output_path=None):
    """Plot score history for one or more tickers.

    Args:
        histories: dict of {symbol: [list of row dicts from DB]}
        output_path: file path to save PNG (default: charts/TICKER_trend.png)

    Returns:
        path to saved chart file.
    """
    if not histories:
        print("  No history data to chart.")
        return None

    fig, ax = plt.subplots(figsize=(12, 6))

    symbols = []
    for symbol, rows in histories.items():
        if len(rows) < 2:
            print(f"  {symbol}: need at least 2 data points for a chart (have {len(rows)})")
            continue

        dates = [datetime.strptime(r["scan_date"], "%Y-%m-%d") for r in rows]
        scores = [r["buffett_score"] for r in rows]

        ax.plot(dates, scores, "o-", label=symbol, linewidth=2, markersize=6)
        symbols.append(symbol)

    if not symbols:
        print("  Not enough data points for any ticker. Run analyze.py on multiple days.")
        plt.close(fig)
        return None

    # Styling
    ax.set_ylabel("Buffett Score", fontsize=12)
    ax.set_xlabel("Scan Date", fontsize=12)
    ax.set_title("Buffett Score Trend", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 105)
    ax.axhline(y=70, color="green", linestyle="--", alpha=0.3, label="Strong (70+)")
    ax.axhline(y=40, color="orange", linestyle="--", alpha=0.3, label="Moderate (40)")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)

    # Date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=45)

    plt.tight_layout()

    # Save
    if output_path is None:
        chart_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "charts"
        )
        os.makedirs(chart_dir, exist_ok=True)
        name = "_".join(symbols[:5])  # Limit filename length
        output_path = os.path.join(chart_dir, f"{name}_trend.png")

    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"  Chart saved: {output_path}")
    return output_path


def chart_from_db(symbols):
    """Convenience: load history from DB and plot."""
    from screener.db import get_ticker_history

    histories = {}
    for sym in symbols:
        sym = sym.upper().strip()
        rows = get_ticker_history(sym)
        if rows:
            histories[sym] = rows

    if not histories:
        print("  No history found in database for these tickers.")
        print("  Run analyze.py first to generate scores, then run again later to build history.")
        return None

    return plot_score_history(histories)
