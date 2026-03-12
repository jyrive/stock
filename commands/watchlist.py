"""watchlist command: manage and analyze stocks you're WATCHING for entry.

Subcommands:
    (none)         Analyze all watchlist stocks, ranked by opportunity
    add TICKERS    Add tickers to watchlist
    remove TICKERS Remove tickers from watchlist
    list           Show current watchlist tickers
    export         Analyze and export to CSV
"""

import sys

from utils.lists import (
    watchlist_list, watchlist_add, watchlist_remove,
    WATCHLIST_PATH,
)


def _analyze_watchlist(extra_flags=None):
    """Run full analysis on watchlist tickers."""
    tickers = watchlist_list()
    if not tickers:
        print("Watchlist is empty.  Add stocks with: python stock.py watchlist add AAPL")
        print("Or discover new candidates: python stock.py discover")
        return

    print(f"\n  👀 WATCHLIST — {len(tickers)} stocks")
    print(f"  {'─' * 50}")

    # Run analyze
    sys.argv = ["analyze.py"] + tickers + (extra_flags or [])
    from commands.analyze import main as analyze_main
    analyze_main()

    # Show which ones are undervalued (buying opportunities)
    from utils.scores_db import get_latest_scores
    latest = get_latest_scores()
    w_set = set(t.upper() for t in tickers)

    opportunities = []
    for row in latest:
        if row["symbol"] in w_set:
            mos = row.get("margin_of_safety")
            score = row.get("fundamental_score")
            if mos is not None and mos > 0 and score is not None:
                opportunities.append(row)

    if opportunities:
        opportunities.sort(key=lambda x: x.get("margin_of_safety", 0), reverse=True)
        print(f"\n  🎯 BUYING OPPORTUNITIES — undervalued watchlist stocks:")
        print(f"  {'Symbol':<8}{'Score':>7}{'MoS%':>8}{'Price':>10}{'IV$':>10}")
        print(f"  {'─' * 44}")
        for o in opportunities:
            price = f"${o['current_price']:.2f}" if o.get("current_price") else "-"
            iv = f"${o['intrinsic_value']:.2f}" if o.get("intrinsic_value") else "-"
            print(f"  {o['symbol']:<8}{o['fundamental_score']:>7.0f}{o['margin_of_safety']:>7.1f}%{price:>10}{iv:>10}")
        print(f"\n  Consider: python stock.py portfolio buy {opportunities[0]['symbol']}\n")
    else:
        print("\n  No undervalued stocks on your watchlist right now.\n")


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        _analyze_watchlist()
        return

    subcmd = args[0].lower()
    symbols = [s.upper().strip() for s in args[1:] if s.strip()]

    if subcmd == "list":
        tickers = watchlist_list()
        if tickers:
            print(f"\n  Watchlist ({len(tickers)} stocks):")
            for t in tickers:
                print(f"    {t}")
            print(f"\n  File: {WATCHLIST_PATH}\n")
        else:
            print("  Watchlist is empty.  Add with: python stock.py watchlist add AAPL")

    elif subcmd == "add":
        if not symbols:
            print("Usage: python stock.py watchlist add AAPL MSFT ...")
            return
        added = watchlist_add(symbols)
        if added:
            print(f"  ✅ Added to watchlist: {', '.join(added)}")
        already = [s for s in symbols if s not in added]
        if already:
            print(f"  ℹ️  Already on watchlist: {', '.join(already)}")

    elif subcmd == "remove":
        if not symbols:
            print("Usage: python stock.py watchlist remove AAPL")
            return
        removed = watchlist_remove(symbols)
        if removed:
            print(f"  ✅ Removed from watchlist: {', '.join(removed)}")
        not_found = [s for s in symbols if s not in removed]
        if not_found:
            print(f"  ℹ️  Not on watchlist: {', '.join(not_found)}")

    elif subcmd == "export":
        _analyze_watchlist(extra_flags=["--csv"])

    else:
        print(f"Unknown watchlist command: '{subcmd}'")
        print("Usage: python stock.py watchlist [list|add|remove|export]")


if __name__ == "__main__":
    main()
