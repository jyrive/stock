"""portfolio command: manage and analyze stocks you OWN.

Subcommands:
    (none)         Analyze all portfolio stocks + show alerts + P&L
    add TICKERS    Add tickers to portfolio
    remove TICKERS Remove tickers from portfolio
    list           Show current portfolio tickers
    buy TICKER --shares N [--price P] [--date D]
                   Record a paper buy (auto-fetches price if omitted)
    sell TICKER --shares N [--price P]
                   Record a paper sell
    pnl            Show P&L, total return vs SPY benchmark
    positions      Show all open positions
    transactions   Show transaction history
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


def _parse_flag(args, flag, default=None):
    """Extract --flag VALUE from args list, return (value, remaining_args)."""
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            val = args[idx + 1]
            remaining = args[:idx] + args[idx + 2:]
            return val, remaining
    return default, args


def _get_current_price(symbol):
    """Fetch current price from market data provider."""
    from datasources.market import get_current_price
    return get_current_price(symbol)


def print_pnl(compact=False):
    """Print portfolio P&L with total return vs SPY."""
    from utils.positions import get_positions, has_positions
    from utils.returns import calculate_portfolio_returns

    if not has_positions():
        print("  No positions recorded yet.")
        print("  Record a buy:  python stock.py portfolio buy AAPL --shares 10")
        return

    positions = get_positions()
    if not positions:
        print("  All positions closed.")
        return

    print(f"\n  Fetching prices for {len(positions)} positions...")
    data = calculate_portfolio_returns(positions)
    if not data:
        return

    # Per-position table
    p = data["portfolio"]
    results = data["positions"]

    print(f"\n  {'Symbol':<7}{'Shares':>7}{'Avg$':>9}{'Now$':>9}{'P&L$':>10}{'Price%':>8}{'Div$':>8}{'Total%':>8}{'Days':>6}")
    print(f"  {'─' * 72}")

    for r in sorted(results, key=lambda x: x.get("total_return_pct") or 0, reverse=True):
        sym = r["symbol"]
        shares = f"{r['shares']:.0f}" if r['shares'] == int(r['shares']) else f"{r['shares']:.2f}"

        if r["current_price"] is None:
            print(f"  {sym:<7}{shares:>7}  ${r['avg_cost']:>7.2f}     —          —       —       —       —")
            continue

        avg = f"${r['avg_cost']:.2f}"
        now = f"${r['current_price']:.2f}"
        pnl = r["price_pnl"]
        pnl_str = f"{'+'if pnl>=0 else ''}{pnl:,.0f}"
        price_ret = f"{'+'if r['price_return_pct']>=0 else ''}{r['price_return_pct']:.1f}%"
        div = f"+{r['dividends']:.0f}" if r["dividends"] else "—"
        total_ret = f"{'+'if r['total_return_pct']>=0 else ''}{r['total_return_pct']:.1f}%"
        days = str(r["holding_days"])

        print(f"  {sym:<7}{shares:>7}{avg:>9}{now:>9}{pnl_str:>10}{price_ret:>8}{div:>8}{total_ret:>8}{days:>6}")

    # Portfolio totals
    print(f"  {'─' * 72}")
    cost_str = f"${p['total_cost']:,.0f}"
    val_str = f"${p['current_value']:,.0f}"
    pnl_str = f"{'+'if p['price_pnl']>=0 else ''}{p['price_pnl']:,.0f}"
    div_str = f"+{p['total_dividends']:.0f}" if p['total_dividends'] else "—"
    total_ret = f"{'+'if p['total_return_pct']>=0 else ''}{p['total_return_pct']:.1f}%"
    print(f"  {'TOTAL':<7}{'':>7}{cost_str:>9}{val_str:>9}{pnl_str:>10}{'':>8}{div_str:>8}{total_ret:>8}")

    # Benchmark comparison
    b = data["benchmark"]
    if b["return_pct"] is not None:
        spy_ret = f"{'+'if b['return_pct']>=0 else ''}{b['return_pct']:.1f}%"
        alpha = data["alpha"]
        alpha_str = f"{'+'if alpha>=0 else ''}{alpha:.1f}%"
        beating = "✅ BEATING" if alpha > 0 else "❌ TRAILING"

        print(f"\n  📊 vs SPY (since {b['start_date']}):")
        print(f"     Your portfolio: {total_ret} total return")
        print(f"     S&P 500 (SPY):  {spy_ret} total return")
        print(f"     Alpha:          {alpha_str}  {beating} the index")


def print_positions():
    """Show all open positions."""
    from utils.positions import get_positions, has_positions

    if not has_positions():
        print("  No positions recorded.")
        return

    positions = get_positions()
    if not positions:
        print("  All positions closed.")
        return

    print(f"\n  Open Positions ({len(positions)}):")
    print(f"  {'Symbol':<8}{'Shares':>8}{'Avg Cost':>10}{'Total Cost':>12}{'Since'}")
    print(f"  {'─' * 50}")
    for p in positions:
        shares = f"{p['shares']:.0f}" if p['shares'] == int(p['shares']) else f"{p['shares']:.2f}"
        print(f"  {p['symbol']:<8}{shares:>8}  ${p['avg_cost']:>8.2f}  ${p['total_cost']:>9.2f}  {p['first_buy_date']}")


def print_transactions(symbol=None):
    """Show transaction history."""
    from utils.positions import get_transactions

    txns = get_transactions(symbol)
    if not txns:
        print(f"  No transactions{' for ' + symbol if symbol else ''}.")
        return

    label = f" for {symbol}" if symbol else ""
    print(f"\n  Transaction History{label} ({len(txns)} records):")
    print(f"  {'ID':>4}  {'Date':<12}{'Action':<6}{'Symbol':<8}{'Shares':>8}{'Price':>10}{'Note'}")
    print(f"  {'─' * 62}")
    for t in txns:
        note = t.get("note") or ""
        shares = f"{t['shares']:.0f}" if t['shares'] == int(t['shares']) else f"{t['shares']:.2f}"
        print(f"  {t['id']:>4}  {t['date']:<12}{t['action']:<6}{t['symbol']:<8}{shares:>8}  ${t['price']:>8.2f}  {note}")


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        # Default: analyze everything + show P&L if positions exist
        _analyze_portfolio()
        from utils.positions import has_positions
        if has_positions():
            print()
            print_pnl(compact=True)
        return

    subcmd = args[0].lower()
    rest = args[1:]

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
        symbols = [s.upper().strip() for s in rest if s.strip() and not s.startswith("--")]
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
        symbols = [s.upper().strip() for s in rest if s.strip() and not s.startswith("--")]
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
        # Parse: portfolio buy AAPL --shares 10 [--price 150.00] [--date 2026-01-15]
        shares_str, rest = _parse_flag(rest, "--shares")
        price_str, rest = _parse_flag(rest, "--price")
        date_str, rest = _parse_flag(rest, "--date")
        symbols = [s.upper().strip() for s in rest if s.strip() and not s.startswith("--")]

        if not symbols:
            print("Usage: python stock.py portfolio buy AAPL --shares 10 [--price 150] [--date 2026-01-15]")
            return

        from utils.positions import record_buy

        for sym in symbols:
            # Move from watchlist → portfolio (legacy behavior)
            move_to_portfolio([sym])

            if shares_str:
                shares = float(shares_str)
                if price_str:
                    price = float(price_str)
                else:
                    print(f"  Fetching current price for {sym}...")
                    price = _get_current_price(sym)
                    if price is None:
                        print(f"  ❌ Could not fetch price for {sym}. Use --price to specify.")
                        continue

                record_buy(sym, shares, price, buy_date=date_str)
                d = date_str or "today"
                print(f"  ✅ Bought {shares:.0f} shares of {sym} @ ${price:.2f} ({d})")
                print(f"     Total cost: ${shares * price:,.2f}")
            else:
                print(f"  ✅ {sym} added to portfolio.")
                print(f"     💡 Record position: python stock.py portfolio buy {sym} --shares 10")

    elif subcmd == "sell":
        shares_str, rest = _parse_flag(rest, "--shares")
        price_str, rest = _parse_flag(rest, "--price")
        symbols = [s.upper().strip() for s in rest if s.strip() and not s.startswith("--")]

        if not symbols:
            print("Usage: python stock.py portfolio sell AAPL --shares 10 [--price 150]")
            return

        from utils.positions import record_sell

        for sym in symbols:
            if shares_str:
                shares = float(shares_str)
                if price_str:
                    price = float(price_str)
                else:
                    print(f"  Fetching current price for {sym}...")
                    price = _get_current_price(sym)
                    if price is None:
                        print(f"  ❌ Could not fetch price for {sym}. Use --price to specify.")
                        continue

                record_sell(sym, shares, price)
                pnl_note = ""
                # Calculate P&L on this sale
                from utils.positions import get_positions
                # We need avg cost before the sell was recorded... it's already recorded
                # Just show the sell confirmation
                print(f"  ✅ Sold {shares:.0f} shares of {sym} @ ${price:.2f}")
                print(f"     Proceeds: ${shares * price:,.2f}")
            else:
                # Legacy: just move to watchlist
                move_to_watchlist([sym])
                print(f"  ✅ {sym} moved to watchlist.")

    elif subcmd == "pnl":
        print_pnl()

    elif subcmd == "positions":
        print_positions()

    elif subcmd in ("transactions", "txns"):
        sym = rest[0].upper() if rest else None
        print_transactions(sym)

    elif subcmd == "export":
        _analyze_portfolio(extra_flags=["--csv"])

    else:
        print(f"Unknown portfolio command: '{subcmd}'")
        print("Usage: python stock.py portfolio [list|add|remove|buy|sell|pnl|positions|transactions|export]")


if __name__ == "__main__":
    main()
