#!/usr/bin/env python3
"""
Score History Viewer

Browse historical screening scores to spot stocks that stand out
at specific moments.

Usage:
    python history.py                    # show latest scores + movers
    python history.py AAPL               # show score history for AAPL
    python history.py AAPL MSFT          # compare multiple tickers
    python history.py --dates            # list all scan dates
    python history.py --date 2026-02-27  # show scores from a specific date
    python history.py --movers           # biggest score changes over time
"""

import sys
import warnings

from screener.db import (
    get_scan_dates,
    get_scores_by_date,
    get_ticker_history,
    get_latest_scores,
    get_biggest_movers,
)
from screener.output import (
    print_summary_table,
    print_legend,
    _fmt,
    _data_line,
    _DATA_HDR,
)

warnings.filterwarnings("ignore")

HEADER = "=" * 80
DIVIDER = "─" * 70


def print_ticker_history(symbol, history):
    """Print score evolution for a single ticker."""
    if not history:
        print(f"  No history found for {symbol}.\n")
        return

    latest = history[-1]
    name = latest.get("name") or symbol

    print(f"\n{HEADER}")
    print(f"  {symbol} — {name}")
    print(f"  Sector: {latest.get('sector', 'N/A')} | Industry: {latest.get('industry', 'N/A')}")
    print(HEADER)

    print(f"\n  {'Date':<13}{_DATA_HDR}")
    print(f"  {'─' * 115}")

    prev_score = None
    for row in history:
        score = row.get("buffett_score", 0)
        f = _fmt(row)

        # Arrow indicator for score change
        arrow = ""
        if prev_score is not None:
            diff = score - prev_score
            if diff > 2:
                arrow = " ▲"
            elif diff < -2:
                arrow = " ▼"
            elif diff != 0:
                arrow = " ~"

        # Override formatted score with arrow
        f["score"] = f"{score:.1f}{arrow}"

        print(f"  {row['scan_date']:<13}{_data_line(f)}")

        prev_score = score

    # Summary
    if len(history) >= 2:
        first = history[0]["buffett_score"]
        last = history[-1]["buffett_score"]
        change = last - first
        direction = "▲" if change > 0 else "▼" if change < 0 else "="
        print(f"\n  Overall: {first:.1f} → {last:.1f}  ({direction} {abs(change):.1f} pts"
              f" over {len(history)} scans)")

    print_legend()


def print_movers(movers, top_n=20):
    """Print biggest score movers."""
    if not movers:
        print("  No score changes found (need at least 2 scans).\n")
        return

    # Split into risers and fallers
    risers = [m for m in movers if m["change"] > 0][:top_n]
    fallers = [m for m in movers if m["change"] < 0][:top_n]

    if risers:
        print(f"\n{HEADER}")
        print(f"  BIGGEST RISERS")
        print(HEADER)
        print(f"  {'Symbol':<9}{'Name':<30}{'Old':>7}{'New':>7}{'Change':>8}{'Period'}")
        print(f"  {DIVIDER}")
        for m in risers:
            name = (m.get("name") or "?")[:28]
            print(f"  {m['symbol']:<9}{name:<30}{m['old_score']:>7.1f}{m['new_score']:>7.1f}"
                  f"  ▲{m['change']:>5.1f}  {m['old_date']} → {m['new_date']}")

    if fallers:
        print(f"\n{HEADER}")
        print(f"  BIGGEST FALLERS")
        print(HEADER)
        print(f"  {'Symbol':<9}{'Name':<30}{'Old':>7}{'New':>7}{'Change':>8}{'Period'}")
        print(f"  {DIVIDER}")
        for m in fallers:
            name = (m.get("name") or "?")[:28]
            print(f"  {m['symbol']:<9}{name:<30}{m['old_score']:>7.1f}{m['new_score']:>7.1f}"
                  f"  ▼{abs(m['change']):>5.1f}  {m['old_date']} → {m['new_date']}")

    print()


def main():
    args = sys.argv[1:]

    if not args:
        # Default: show latest scores + movers
        latest = get_latest_scores()
        dates = get_scan_dates()

        if not latest:
            print("No scores in database yet. Run buffett_screener.py first.")
            return

        print(f"\nDatabase has {len(dates)} scan date(s), {len(latest)} unique tickers.")
        print(f"Most recent scan: {dates[0] if dates else 'none'}")

        print_summary_table(latest, f"Latest Scores ({dates[0] if dates else ''})")

        movers = get_biggest_movers()
        if movers:
            print_movers(movers)

        print("Usage:")
        print("  python history.py AAPL            # ticker history")
        print("  python history.py --dates          # list scan dates")
        print("  python history.py --date 2026-02-27 # scores from a date")
        print("  python history.py --movers         # biggest score changes")
        return

    if args[0] == "--dates":
        dates = get_scan_dates()
        if not dates:
            print("No scans yet.")
            return
        print(f"\n  Scan dates ({len(dates)}):\n")
        for d in dates:
            count = len(get_scores_by_date(d))
            print(f"    {d}  ({count} stocks)")
        print()
        return

    if args[0] == "--date" and len(args) >= 2:
        scan_date = args[1]
        scores = get_scores_by_date(scan_date)
        print_summary_table(scores, f"Scores from {scan_date}")
        return

    if args[0] == "--movers":
        movers = get_biggest_movers()
        print_movers(movers)
        return

    # Treat args as ticker symbols — show history for each
    for symbol in args:
        symbol = symbol.upper().strip()
        history = get_ticker_history(symbol)
        print_ticker_history(symbol, history)


if __name__ == "__main__":
    main()
