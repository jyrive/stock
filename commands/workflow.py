"""Workflow commands: pre-built routines for daily, weekly, and monthly use.

Usage:
    python stock.py daily       Quick portfolio check + alerts (~30s)
    python stock.py weekly      Portfolio + watchlist + movers (~2min)
    python stock.py monthly     Full review: discover + analyze + compare + export (~5min)
"""

import sys
import time
from datetime import datetime


def _section(title):
    """Print a workflow section header with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'━' * 70}")
    print(f"  {title}  [{ts}]")
    print(f"{'━' * 70}")


def _has_tickers(source):
    """Check if portfolio/watchlist has tickers."""
    from utils.lists import portfolio_list, watchlist_list
    if source == "portfolio":
        return bool(portfolio_list())
    return bool(watchlist_list())


# ─── DAILY ──────────────────────────────────────────────────────

def daily():
    """Quick morning check: portfolio summary + entry signals + alerts.

    Output: ~30 lines — summary table, entry timing, and any active alerts.
    Runtime: ~30 seconds for a typical 10-stock portfolio.
    """
    start = time.time()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  DAILY CHECK                                                        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    from utils.cache import enable_cache
    enable_cache()

    if not _has_tickers("portfolio"):
        print("\n  Portfolio is empty. Add stocks first:")
        print("    python stock.py portfolio add AAPL MSFT GOOGL")
        print()
        return

    # 1. Portfolio summary (compact — no per-stock detail)
    _section("PORTFOLIO SUMMARY")
    from utils.lists import portfolio_list
    tickers = portfolio_list()
    print(f"  Analyzing {len(tickers)} holdings...\n")

    sys.argv = ["analyze.py"] + tickers + ["--summary"]
    from commands.analyze import main as analyze_main
    analyze_main()

    # 2. Technical entry signals (compact)
    _section("ENTRY SIGNALS")
    from scoring.technical import analyze_technical, _entry_rating
    from utils.database import get_latest_scores
    latest = {r["symbol"]: r.get("buffett_score") for r in get_latest_scores()}

    signals = []
    for t in tickers:
        ta = analyze_technical(t.upper())
        if ta:
            signals.append((ta, latest.get(t.upper())))

    if signals:
        signals.sort(key=lambda x: x[0].get("tech_score", 0), reverse=True)
        print(f"  {'Symbol':<8}{'Tech':>6}{'RSI':>6}{'vs200':>8}  {'Rating'}")
        print(f"  {'─' * 42}")
        for ta, bs in signals:
            tech = ta.get("tech_score", 0)
            rsi = ta.get("rsi_14")
            pct = ta.get("price_vs_sma200_pct")
            rsi_s = f"{rsi:.0f}" if rsi is not None else "-"
            pct_s = f"{pct:+.1f}%" if pct is not None else "-"
            stars, label = _entry_rating(tech, bs)
            print(f"  {ta['symbol']:<8}{tech:>6}{rsi_s:>6}{pct_s:>8}  {stars} {label}")
        # Highlight best entry
        best = signals[0]
        if best[0].get("tech_score", 0) >= 50:
            print(f"\n  📉 Best entry signal: {best[0]['symbol']} (Tech {best[0]['tech_score']})")
    else:
        print("  Could not fetch technical data.\n")

    # 3. Alerts (filtered to portfolio only)
    _section("ALERTS")
    from commands.alerts import scan_alerts, print_alerts
    alerts = scan_alerts()

    p_set = set(t.upper() for t in tickers)
    for key in ("undervalued", "score_drops", "bargains"):
        alerts[key] = [a for a in alerts[key] if a["symbol"] in p_set]

    if any(alerts[k] for k in ("undervalued", "score_drops", "bargains")):
        print_alerts(alerts)
    else:
        print("  ✅ No alerts for your portfolio stocks.\n")

    elapsed = time.time() - start
    print(f"  Done in {elapsed:.0f}s")


# ─── WEEKLY ─────────────────────────────────────────────────────

def weekly():
    """Weekly review: portfolio + watchlist + entry timing + movers.

    Output: ~60 lines — summary tables, entry timing, buying opportunities, score movers.
    Runtime: ~2 minutes for 10 portfolio + 10 watchlist stocks.
    """
    start = time.time()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  WEEKLY REVIEW                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    from utils.cache import enable_cache
    enable_cache()

    has_portfolio = _has_tickers("portfolio")
    has_watchlist = _has_tickers("watchlist")

    # 1. Portfolio summary (compact)
    if has_portfolio:
        _section("PORTFOLIO SUMMARY")
        from utils.lists import portfolio_list
        p_tickers = portfolio_list()
        print(f"  Analyzing {len(p_tickers)} holdings...\n")

        sys.argv = ["analyze.py"] + p_tickers + ["--summary"]
        from commands.analyze import main as analyze_main
        analyze_main()

        # Alerts for portfolio
        from commands.alerts import scan_alerts, print_alerts
        alerts = scan_alerts()
        p_set = set(t.upper() for t in p_tickers)
        for key in ("undervalued", "score_drops", "bargains"):
            alerts[key] = [a for a in alerts[key] if a["symbol"] in p_set]
        if any(alerts[k] for k in ("undervalued", "score_drops", "bargains")):
            print_alerts(alerts)
    else:
        print("\n  Portfolio is empty — skipping.")

    # 2. Watchlist summary (compact) + buying opportunities + entry timing
    if has_watchlist:
        _section("WATCHLIST — BUYING OPPORTUNITIES")
        from utils.lists import watchlist_list
        w_tickers = watchlist_list()
        print(f"  Analyzing {len(w_tickers)} watched stocks...\n")

        sys.argv = ["analyze.py"] + w_tickers + ["--summary"]
        from commands.analyze import main as analyze_main2
        analyze_main2()

        # Show buying opportunities (undervalued watchlist stocks)
        from utils.database import get_latest_scores
        latest = get_latest_scores()
        w_set = set(t.upper() for t in w_tickers)
        opportunities = []
        for row in latest:
            if row["symbol"] in w_set:
                mos = row.get("margin_of_safety")
                score = row.get("buffett_score")
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
                print(f"  {o['symbol']:<8}{o['buffett_score']:>7.0f}{o['margin_of_safety']:>7.1f}%{price:>10}{iv:>10}")
            print(f"\n  Consider: python stock.py portfolio buy {opportunities[0]['symbol']}")
        else:
            print("\n  No undervalued stocks on your watchlist right now.")

        # Technical entry timing for watchlist
        _section("WATCHLIST — ENTRY TIMING")
        from scoring.technical import analyze_technical, _entry_rating
        latest_scores = {r["symbol"]: r.get("buffett_score") for r in latest}

        ta_results = []
        for t in w_tickers:
            ta = analyze_technical(t.upper())
            if ta:
                ta_results.append((ta, latest_scores.get(t.upper())))

        if ta_results:
            ta_results.sort(key=lambda x: x[0].get("tech_score", 0), reverse=True)
            print(f"  {'Symbol':<8}{'Tech':>6}{'Buff':>6}{'RSI':>6}{'vs200':>8}{'BB%':>6}  {'Rating'}")
            print(f"  {'─' * 52}")
            for ta, bs in ta_results:
                tech = ta.get("tech_score", 0)
                rsi = ta.get("rsi_14")
                pct = ta.get("price_vs_sma200_pct")
                bb = ta.get("bb_position")
                rsi_s = f"{rsi:.0f}" if rsi is not None else "-"
                pct_s = f"{pct:+.1f}%" if pct is not None else "-"
                bb_s = f"{bb:.0%}" if bb is not None else "-"
                bs_s = f"{bs:.0f}" if bs is not None else "-"
                stars, label = _entry_rating(tech, bs)
                print(f"  {ta['symbol']:<8}{tech:>6}{bs_s:>6}{rsi_s:>6}{pct_s:>8}{bb_s:>6}  {stars} {label}")

            # Highlight strong entries
            strong = [(ta, bs) for ta, bs in ta_results
                      if ta.get("tech_score", 0) >= 50 and (bs or 0) >= 50]
            if strong:
                print(f"\n  📉 Strong entry signals:")
                for ta, bs in strong:
                    print(f"     {ta['symbol']} — Tech {ta['tech_score']}, Buffett {bs:.0f}")
        else:
            print("  Could not fetch technical data.\n")
    else:
        print("\n  Watchlist is empty — skipping.")

    # 3. Score movers (all tracked stocks)
    _section("SCORE MOVERS")
    from utils.database import get_biggest_movers
    from commands.history import print_movers
    movers = get_biggest_movers()
    if movers:
        # Filter to portfolio + watchlist only
        tracked = set()
        if has_portfolio:
            from utils.lists import portfolio_list as pl
            tracked.update(t.upper() for t in pl())
        if has_watchlist:
            from utils.lists import watchlist_list as wl
            tracked.update(t.upper() for t in wl())

        if tracked:
            filtered = [m for m in movers if m["symbol"] in tracked]
            if filtered:
                print_movers(filtered, top_n=10)
            else:
                print("  No score changes for tracked stocks yet.\n")
        else:
            print_movers(movers, top_n=10)
    else:
        print("  Need at least 2 scans to show movers.\n")

    elapsed = time.time() - start
    print(f"  Done in {elapsed:.0f}s")

    if not has_portfolio and not has_watchlist:
        print("\n  Get started:")
        print("    python stock.py portfolio add AAPL MSFT")
        print("    python stock.py watchlist add GOOGL META")
        print()


# ─── MONTHLY ────────────────────────────────────────────────────

def monthly():
    """Monthly full review: discover + full analysis + compare + entry timing + export.

    Output: verbose — full per-stock breakdowns, discovery scan, entry timing, comparison.
    Runtime: ~5 minutes depending on portfolio + watchlist size.
    """
    start = time.time()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  MONTHLY REVIEW                                                     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    from utils.cache import enable_cache
    enable_cache()

    has_portfolio = _has_tickers("portfolio")
    has_watchlist = _has_tickers("watchlist")

    # 1. Discover new candidates
    _section("DISCOVER — New Investment Ideas")
    sys.argv = ["discover.py"]
    from commands.discover import main as discover_main
    discover_main()

    # 2. Full portfolio analysis (verbose)
    if has_portfolio:
        _section("PORTFOLIO — Full Analysis")
        from utils.lists import portfolio_list
        p_tickers = portfolio_list()
        print(f"  Analyzing {len(p_tickers)} holdings (full detail)...\n")

        sys.argv = ["analyze.py"] + p_tickers
        from commands.analyze import main as analyze_main
        analyze_main()
    else:
        print("\n  Portfolio is empty — skipping.")

    # 3. Full watchlist analysis (verbose)
    if has_watchlist:
        _section("WATCHLIST — Full Analysis")
        from utils.lists import watchlist_list
        w_tickers = watchlist_list()
        print(f"  Analyzing {len(w_tickers)} watched stocks (full detail)...\n")

        sys.argv = ["analyze.py"] + w_tickers
        from commands.analyze import main as analyze_main2
        analyze_main2()
    else:
        print("\n  Watchlist is empty — skipping.")

    # 4. Compare portfolio vs watchlist
    if has_portfolio and has_watchlist:
        _section("COMPARE — Portfolio vs Watchlist")
        sys.argv = ["compare.py", "portfolio", "watchlist"]
        from commands.compare import main as compare_main
        compare_main()

    # 5. Entry timing for combined portfolio + watchlist
    all_tracked = []
    if has_portfolio:
        from utils.lists import portfolio_list as pl3
        all_tracked.extend(pl3())
    if has_watchlist:
        from utils.lists import watchlist_list as wl3
        all_tracked.extend(wl3())

    if all_tracked:
        _section("ENTRY TIMING — All Tracked Stocks")
        from scoring.technical import analyze_technical, _entry_rating
        from utils.database import get_latest_scores as gls2
        latest_bs = {r["symbol"]: r.get("buffett_score") for r in gls2()}

        ta_all = []
        for t in all_tracked:
            ta = analyze_technical(t.upper())
            if ta:
                ta_all.append((ta, latest_bs.get(t.upper())))

        if ta_all:
            ta_all.sort(key=lambda x: x[0].get("tech_score", 0), reverse=True)
            print(f"  {'Symbol':<8}{'Tech':>6}{'Buff':>6}{'RSI':>6}{'vs200':>8}{'BB%':>6}{'52w%':>6}  {'Rating'}")
            print(f"  {'─' * 58}")
            for ta, bs in ta_all:
                tech = ta.get("tech_score", 0)
                rsi = ta.get("rsi_14")
                pct = ta.get("price_vs_sma200_pct")
                bb = ta.get("bb_position")
                w52 = ta.get("week52_position")
                rsi_s = f"{rsi:.0f}" if rsi is not None else "-"
                pct_s = f"{pct:+.1f}%" if pct is not None else "-"
                bb_s = f"{bb:.0%}" if bb is not None else "-"
                w52_s = f"{w52:.0%}" if w52 is not None else "-"
                bs_s = f"{bs:.0f}" if bs is not None else "-"
                stars, label = _entry_rating(tech, bs)
                print(f"  {ta['symbol']:<8}{tech:>6}{bs_s:>6}{rsi_s:>6}{pct_s:>8}{bb_s:>6}{w52_s:>6}  {stars} {label}")

            strong = [(ta, bs) for ta, bs in ta_all
                      if ta.get("tech_score", 0) >= 50 and (bs or 0) >= 50]
            if strong:
                print(f"\n  📉 HIGHEST CONVICTION ENTRIES:")
                for ta, bs in strong:
                    print(f"     {ta['symbol']} — Tech {ta['tech_score']}, Buffett {bs:.0f}")

    # 6. Export CSV
    if has_portfolio:
        _section("EXPORT — Saving CSV snapshot")
        from utils.lists import portfolio_list as pl2
        from utils.database import get_latest_scores
        latest = get_latest_scores()
        p_set = set(t.upper() for t in pl2())

        # Get all tracked tickers for export
        export_tickers = list(p_set)
        if has_watchlist:
            from utils.lists import watchlist_list as wl2
            export_tickers += [t for t in wl2() if t.upper() not in p_set]

        from utils.export import export_csv_from_db
        export_csv_from_db(export_tickers)

    elapsed = time.time() - start
    print(f"\n  Monthly review complete in {elapsed:.0f}s")

    if not has_portfolio and not has_watchlist:
        print("\n  Get started:")
        print("    python stock.py portfolio add AAPL MSFT")
        print("    python stock.py watchlist add GOOGL META")
        print()
