"""portfolio command: manage and analyze stocks you OWN.

Subcommands:
    (none)         Analyze all portfolio stocks + show alerts + movers
    add TICKERS    Add tickers to portfolio
    remove TICKERS Remove tickers from portfolio
    list           Show current portfolio tickers
    buy TICKERS    Move from watchlist → portfolio (same as add, but also removes from watchlist)
    sell TICKERS   Move from portfolio → watchlist (keeps watching)
    export         Analyze and export to CSV
"""

import sys

from utils.lists import (
    portfolio_list, portfolio_add, portfolio_remove,
    move_to_portfolio, move_to_watchlist,
    PORTFOLIO_PATH,
)


def _analyze_portfolio(extra_flags=None):
    """Run full analysis on portfolio tickers."""
    tickers = portfolio_list()
    if not tickers:
        print("Portfolio is empty.  Add stocks with: python stock.py portfolio add AAPL MSFT")
        return

    print(f"\n  📊 PORTFOLIO CHECK — {len(tickers)} stocks")
    print(f"  {'─' * 50}")

    # Run analyze
    sys.argv = ["analyze.py"] + tickers + (extra_flags or [])
    from commands.analyze import main as analyze_main
    analyze_main()

    # Run alerts (only for portfolio tickers)
    print()
    from commands.alerts import scan_alerts, print_alerts
    alerts = scan_alerts()

    # Filter alerts to only portfolio stocks
    p_set = set(t.upper() for t in tickers)
    for key in ("undervalued", "score_drops", "bargains"):
        alerts[key] = [a for a in alerts[key] if a["symbol"] in p_set]

    if any(alerts[k] for k in ("undervalued", "score_drops", "bargains")):
        print_alerts(alerts)
    else:
        print("  ✅ No alerts for your portfolio stocks.\n")


def main():
    args = sys.argv[1:]

    if not args:
        # Default: analyze everything
        _analyze_portfolio()
        return

    subcmd = args[0].lower()
    symbols = [s.upper().strip() for s in args[1:] if s.strip()]

    if subcmd == "list":
        tickers = portfolio_list()
        if tickers:
            print(f"\n  Portfolio ({len(tickers)} stocks):")
            for t in tickers:
                print(f"    {t}")
            print(f"\n  File: {PORTFOLIO_PATH}\n")
        else:
            print("  Portfolio is empty.  Add with: python stock.py portfolio add AAPL")

    elif subcmd == "add":
        if not symbols:
            print("Usage: python stock.py portfolio add AAPL MSFT ...")
            return
        added = portfolio_add(symbols)
        if added:
            print(f"  ✅ Added to portfolio: {', '.join(added)}")
        already = [s for s in symbols if s not in added]
        if already:
            print(f"  ℹ️  Already in portfolio: {', '.join(already)}")

    elif subcmd == "remove":
        if not symbols:
            print("Usage: python stock.py portfolio remove AAPL")
            return
        removed = portfolio_remove(symbols)
        if removed:
            print(f"  ✅ Removed from portfolio: {', '.join(removed)}")
        not_found = [s for s in symbols if s not in removed]
        if not_found:
            print(f"  ℹ️  Not in portfolio: {', '.join(not_found)}")

    elif subcmd == "buy":
        if not symbols:
            print("Usage: python stock.py portfolio buy AAPL  (moves from watchlist → portfolio)")
            return
        moved = move_to_portfolio(symbols)
        if moved:
            print(f"  ✅ Moved to portfolio (removed from watchlist): {', '.join(moved)}")

    elif subcmd == "sell":
        if not symbols:
            print("Usage: python stock.py portfolio sell AAPL  (moves to watchlist)")
            return
        moved = move_to_watchlist(symbols)
        if moved:
            print(f"  ✅ Moved to watchlist (removed from portfolio): {', '.join(moved)}")

    elif subcmd == "export":
        _analyze_portfolio(extra_flags=["--csv"])

    else:
        print(f"Unknown portfolio command: '{subcmd}'")
        print("Usage: python stock.py portfolio [list|add|remove|buy|sell|export]")


if __name__ == "__main__":
    main()
