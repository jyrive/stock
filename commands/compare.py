"""compare command: side-by-side comparison of two sets of stocks.

Usage:
    python stock.py compare AAPL,MSFT GOOGL,META      # two comma-separated lists
    python stock.py compare portfolio.txt other.txt     # two files
    python stock.py compare portfolio watchlist          # portfolio vs watchlist
    python stock.py compare AAPL,MSFT                   # compare against portfolio
"""

import os
import sys
import time

from commands.analyze import screen_stock
from utils.lists import load_tickers
from utils.config import enable_cache
from utils.lists import portfolio_list, watchlist_list

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _resolve_tickers(arg):
    """Resolve an argument to a list of tickers.

    Handles: "portfolio", "watchlist", "file.txt", "AAPL,MSFT,GOOGL"
    """
    low = arg.lower()
    if low == "portfolio":
        return portfolio_list(), "Portfolio"
    if low == "watchlist":
        return watchlist_list(), "Watchlist"

    # File path
    if arg.endswith(".txt") or arg.endswith(".csv"):
        path = arg if os.path.isabs(arg) else os.path.join(_PROJECT_ROOT, arg)
        if os.path.exists(path):
            return load_tickers(path), os.path.basename(arg)
        print(f"File not found: {path}")
        return [], arg

    # Comma/space separated tickers
    tickers = [t.strip().upper() for t in arg.replace(",", " ").split() if t.strip()]
    return tickers, ", ".join(tickers[:3]) + ("..." if len(tickers) > 3 else "")

def _analyze_list(tickers, label):
    """Analyze a list of tickers and return scored results."""
    if not tickers:
        print(f"  {label}: no tickers to analyze.")
        return []

    results = []
    for i, ticker in enumerate(tickers, 1):
        result = screen_stock(ticker, i, len(tickers))
        if result:
            results.append(result)
        time.sleep(0.3)
    results.sort(key=lambda x: x["fundamental_score"], reverse=True)
    return results

def _print_side_by_side(results_a, label_a, results_b, label_b):
    """Print comparison table."""
    print(f"\n  {'═' * 70}")
    print(f"  COMPARISON: {label_a} vs {label_b}")
    print(f"  {'═' * 70}")

    # Summary stats
    def _avg(res, key):
        vals = [r.get(key) for r in res if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0

    print(f"\n  {'Metric':<25}  {label_a:>20}  {label_b:>20}")
    print(f"  {'─' * 67}")
    print(f"  {'Stocks':<25}  {len(results_a):>20}  {len(results_b):>20}")

    avg_a = _avg(results_a, "fundamental_score")
    avg_b = _avg(results_b, "fundamental_score")
    print(f"  {'Avg Fundamental Score':<25}  {avg_a:>20.1f}  {avg_b:>20.1f}")

    avg_pe_a = _avg(results_a, "trailing_pe")
    avg_pe_b = _avg(results_b, "trailing_pe")
    if avg_pe_a or avg_pe_b:
        print(f"  {'Avg P/E':<25}  {avg_pe_a:>20.1f}  {avg_pe_b:>20.1f}")

    # Count undervalued
    uv_a = sum(1 for r in results_a if r.get("dcf_analysis", {}).get("undervalued"))
    uv_b = sum(1 for r in results_b if r.get("dcf_analysis", {}).get("undervalued"))
    print(f"  {'Undervalued (DCF)':<25}  {uv_a:>20}  {uv_b:>20}")

    # Top scorer each
    if results_a:
        top_a = results_a[0]
        print(f"  {'Top scorer':<25}  {top_a['symbol'] + ' (' + str(top_a['fundamental_score']) + ')':>20}", end="")
    else:
        print(f"  {'Top scorer':<25}  {'—':>20}", end="")
    if results_b:
        top_b = results_b[0]
        print(f"  {top_b['symbol'] + ' (' + str(top_b['fundamental_score']) + ')':>20}")
    else:
        print(f"  {'—':>20}")

    # Individual rankings side by side
    print(f"\n  {'─' * 67}")
    print(f"  {'Rank':<6} {label_a + ' (Score)':<32} {label_b + ' (Score)':<32}")
    print(f"  {'─' * 67}")

    max_rows = max(len(results_a), len(results_b))
    for i in range(max_rows):
        col_a = ""
        col_b = ""
        if i < len(results_a):
            r = results_a[i]
            uv = " ✦" if r.get("dcf_analysis", {}).get("undervalued") else ""
            col_a = f"{r['symbol']:<8} {r['fundamental_score']:>5.0f}{uv}"
        if i < len(results_b):
            r = results_b[i]
            uv = " ✦" if r.get("dcf_analysis", {}).get("undervalued") else ""
            col_b = f"{r['symbol']:<8} {r['fundamental_score']:>5.0f}{uv}"
        print(f"  {i + 1:>4}. {col_a:<32} {col_b:<32}")

    print(f"\n  ✦ = undervalued (intrinsic value > current price)")

    # Overlaps
    tickers_a = set(r["symbol"] for r in results_a)
    tickers_b = set(r["symbol"] for r in results_b)
    overlap = tickers_a & tickers_b
    if overlap:
        print(f"\n  Overlap ({len(overlap)}): {', '.join(sorted(overlap))}")

    only_a = tickers_a - tickers_b
    only_b = tickers_b - tickers_a
    if only_a:
        print(f"  Only in {label_a}: {', '.join(sorted(only_a))}")
    if only_b:
        print(f"  Only in {label_b}: {', '.join(sorted(only_b))}")

    print()

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        print("Usage: python stock.py compare <list_A> <list_B>")
        print()
        print("  Lists can be:")
        print("    portfolio           Your portfolio stocks")
        print("    watchlist           Your watchlist stocks")
        print("    file.txt            Ticker file")
        print("    AAPL,MSFT,GOOGL     Comma-separated tickers")
        print()
        print("Examples:")
        print("  python stock.py compare portfolio watchlist")
        print("  python stock.py compare portfolio other.txt")
        print("  python stock.py compare AAPL,MSFT GOOGL,META")
        return

    if len(args) == 1:
        # Compare against portfolio
        tickers_a, label_a = portfolio_list(), "Portfolio"
        tickers_b, label_b = _resolve_tickers(args[0])
        if not tickers_a:
            print("Portfolio is empty. Comparing against the tickers requires a portfolio.")
            print("Add stocks: python stock.py portfolio add AAPL MSFT")
            return
    else:
        tickers_a, label_a = _resolve_tickers(args[0])
        tickers_b, label_b = _resolve_tickers(args[1])

    if not tickers_a and not tickers_b:
        print("Both lists are empty. Nothing to compare.")
        return

    enable_cache()

    print(f"\n  Analyzing {label_a} ({len(tickers_a)} stocks)...")
    results_a = _analyze_list(tickers_a, label_a)

    print(f"\n  Analyzing {label_b} ({len(tickers_b)} stocks)...")
    results_b = _analyze_list(tickers_b, label_b)

    _print_side_by_side(results_a, label_a, results_b, label_b)

if __name__ == "__main__":
    main()
