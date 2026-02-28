"""verdict command: triangulation of Fundamental + Technical + Macro.

Usage:
    python stock.py verdict AAPL              # single stock
    python stock.py verdict AAPL MSFT GOOGL   # multiple stocks
    python stock.py verdict --portfolio       # all portfolio stocks
    python stock.py verdict --watchlist       # all watchlist stocks
    python stock.py verdict --all             # portfolio + watchlist
"""

import sys
import time
import warnings

from scoring.verdict import compute_verdict, print_verdict, print_verdict_table
from scoring.technical import analyze_technical
from scoring.macro import analyze_macro
from utils.cache import enable_cache
from utils.lists import portfolio_list, watchlist_list

warnings.filterwarnings("ignore")


def _resolve_tickers(args):
    """Resolve arguments to a ticker list."""
    tickers = []
    for arg in args:
        low = arg.lower()
        if low in ("--portfolio", "-p", "portfolio"):
            tickers.extend(portfolio_list())
        elif low in ("--watchlist", "-w", "watchlist"):
            tickers.extend(watchlist_list())
        elif low in ("--all", "-a"):
            tickers.extend(portfolio_list())
            tickers.extend(watchlist_list())
        else:
            tickers.append(arg.upper().strip())
    # deduplicate preserving order
    seen = set()
    unique = []
    for t in tickers:
        t = t.upper()
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _get_buffett_scores():
    """Fetch latest Buffett scores from the database."""
    try:
        from utils.database import get_latest_scores
        return {r["symbol"]: r.get("buffett_score") for r in get_latest_scores()}
    except Exception:
        return {}


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: python stock.py verdict AAPL [MSFT ...]")
        print("       python stock.py verdict --portfolio")
        print("       python stock.py verdict --watchlist")
        print("       python stock.py verdict --all")
        return

    tickers = _resolve_tickers(args)
    if not tickers:
        print("  No tickers to analyze.")
        return

    enable_cache()

    # 1. Fetch macro once (shared across all stocks)
    print("\n  Fetching macro environment...")
    macro = analyze_macro()
    macro_score = macro["macro_score"]

    # 2. Fetch Buffett scores from DB
    buffett_scores = _get_buffett_scores()

    # 3. Fetch technical for each ticker
    print(f"  Analyzing {len(tickers)} stock(s)...\n")

    verdicts = []
    missing_fundamental = []
    for i, ticker in enumerate(tickers, 1):
        ta = analyze_technical(ticker)
        tech_score = ta.get("tech_score", 0) if ta else None
        fund_score = buffett_scores.get(ticker)

        if fund_score is None:
            missing_fundamental.append(ticker)

        v = compute_verdict(fund_score, tech_score, macro_score)
        verdicts.append((ticker, v))

        if i < len(tickers):
            time.sleep(0.2)

    # 4. Print output
    if len(verdicts) == 1:
        symbol, v = verdicts[0]
        # Try to get company name
        name = None
        try:
            from utils.database import get_latest_scores
            for r in get_latest_scores():
                if r["symbol"] == symbol:
                    name = r.get("name")
                    break
        except Exception:
            pass
        print_verdict(v, symbol=symbol, name=name)
    else:
        # Sort by verdict quality
        _ORDER = {"STRONG BUY": 0, "BUY": 1, "ACCUMULATE": 2, "NEUTRAL": 3,
                   "WATCH": 4, "HOLD": 5, "AVOID": 6}
        verdicts.sort(key=lambda x: (_ORDER.get(x[1]["verdict"], 9),
                                      -(x[1].get("fund") or 0)))
        print_verdict_table(verdicts)

    # Warn about missing fundamentals
    if missing_fundamental:
        print(f"\n  ⚠️  No Buffett Score for: {', '.join(missing_fundamental)}")
        print(f"     Run: python stock.py analyze {' '.join(missing_fundamental)}")

    print()


if __name__ == "__main__":
    main()
