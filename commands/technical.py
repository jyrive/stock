"""technical command: technical analysis for entry timing.

Usage:
    python stock.py technical AAPL              # single stock TA
    python stock.py technical AAPL MSFT GOOGL   # multiple stocks
    python stock.py technical portfolio         # all portfolio stocks
    python stock.py technical watchlist         # all watchlist stocks
"""

import sys
import time
import warnings

from technical.analysis import analyze_technical
from output.technical import print_technical, _entry_rating
from utils.cache import enable_cache
from utils.lists import portfolio_list, watchlist_list

warnings.filterwarnings("ignore")


def _resolve_tickers(args):
    """Resolve arguments to a ticker list."""
    tickers = []
    for arg in args:
        low = arg.lower()
        if low == "portfolio":
            tickers.extend(portfolio_list())
        elif low == "watchlist":
            tickers.extend(watchlist_list())
        else:
            tickers.append(arg.upper().strip())
    return tickers


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: python stock.py technical AAPL [MSFT ...]")
        print("       python stock.py technical portfolio")
        print("       python stock.py technical watchlist")
        return

    tickers = _resolve_tickers(args)
    if not tickers:
        print("  No tickers to analyze.")
        return

    enable_cache()

    print()
    print("=" * 60)
    print("  TECHNICAL ANALYSIS — Entry Timing")
    print("=" * 60)

    # Try to get Buffett scores from database for combined rating
    buffett_scores = {}
    try:
        from utils.database import get_latest_scores
        for row in get_latest_scores():
            buffett_scores[row["symbol"]] = row.get("buffett_score")
    except Exception:
        pass

    results = []
    for i, ticker in enumerate(tickers, 1):
        print(f"\n  [{i}/{len(tickers)}] Fetching price data for {ticker}...")
        ta = analyze_technical(ticker)
        bs = buffett_scores.get(ticker)
        print_technical(ta, buffett_score=bs)
        results.append((ta, bs))
        if i < len(tickers):
            time.sleep(0.3)

    # Summary table if multiple stocks
    if len(results) > 1:
        print(f"\n{'=' * 60}")
        print(f"  ENTRY TIMING SUMMARY")
        print(f"{'=' * 60}")
        print(f"  {'Symbol':<8}{'Tech':>6}{'Buff':>6}{'RSI':>6}{'vs200':>8}{'BB%':>6}{'52w%':>6}  {'Rating'}")
        print(f"  {'─' * 58}")

        # Sort by tech score descending
        sorted_results = sorted(results, key=lambda x: x[0].get("tech_score", 0), reverse=True)
        for ta, bs in sorted_results:
            symbol = ta["symbol"]
            tech = ta.get("tech_score", 0)
            rsi = ta.get("rsi_14")
            pct200 = ta.get("price_vs_sma200_pct")
            bb = ta.get("bb_position")
            w52 = ta.get("week52_position")

            rsi_str = f"{rsi:.0f}" if rsi is not None else "-"
            pct200_str = f"{pct200:+.1f}%" if pct200 is not None else "-"
            bb_str = f"{bb:.0%}" if bb is not None else "-"
            w52_str = f"{w52:.0%}" if w52 is not None else "-"
            bs_str = f"{bs:.0f}" if bs is not None else "-"

            stars, label = _entry_rating(tech, bs)
            print(f"  {symbol:<8}{tech:>6}{bs_str:>6}{rsi_str:>6}{pct200_str:>8}{bb_str:>6}{w52_str:>6}  {stars} {label}")

        print(f"\n  Tech = Technical Score (0-100, higher = better entry)")
        print(f"  Buff = Buffett Score | RSI = 14-day RSI")
        print(f"  vs200 = Price vs 200-day MA | BB% = Bollinger position | 52w% = 52-week position")
        print()


if __name__ == "__main__":
    main()
