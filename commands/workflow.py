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

    # 0. Macro one-liner
    from macro.analysis import analyze_macro
    from output.macro import macro_one_liner
    macro = analyze_macro()
    print(f"\n  {macro_one_liner(macro)}")

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

    # 2. Verdicts — triangulated one-liner per stock
    _section("VERDICTS")
    from technical.analysis import analyze_technical
    from verdict.engine import compute_verdict
    from output.verdict import verdict_one_liner
    from utils.database import get_latest_scores
    latest = {r["symbol"]: r.get("fundamental_score") for r in get_latest_scores()}

    lines = []
    for t in tickers:
        ta = analyze_technical(t.upper())
        tech_score = ta.get("tech_score", 0) if ta else None
        fund_score = latest.get(t.upper())
        v = compute_verdict(fund_score, tech_score, macro["macro_score"])
        lines.append((t.upper(), v))

    if lines:
        _ORDER = {"STRONG BUY": 0, "BUY": 1, "ACCUMULATE": 2, "NEUTRAL": 3,
                  "WATCH": 4, "HOLD": 5, "AVOID": 6}
        lines.sort(key=lambda x: (_ORDER.get(x[1]["verdict"], 9),
                                   -(x[1].get("fund") or 0)))
        print(f"  {'Symbol':<8}{'Zones':<6} {'Verdict':<14}{'Size'}")
        print(f"  {'─' * 38}")
        for sym, v in lines:
            print(f"  {verdict_one_liner(v, sym)}")
    else:
        print("  Could not fetch data.\n")

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

    # 0. Macro compact
    _section("MACRO ENVIRONMENT")
    from macro.analysis import analyze_macro
    from output.macro import print_macro_compact
    macro = analyze_macro()
    print_macro_compact(macro)

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

        # P&L if positions are tracked
        from utils.positions import has_positions
        if has_positions():
            from commands.portfolio import print_pnl
            print_pnl(compact=True)
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
            print(f"\n  Consider: python stock.py portfolio buy {opportunities[0]['symbol']}")
        else:
            print("\n  No undervalued stocks on your watchlist right now.")

        # Technical entry timing for watchlist → Verdict table
        _section("WATCHLIST — VERDICTS")
        from technical.analysis import analyze_technical
        from verdict.engine import compute_verdict
        from output.verdict import print_verdict_table
        latest_scores = {r["symbol"]: r.get("fundamental_score") for r in latest}

        w_verdicts = []
        for t in w_tickers:
            ta = analyze_technical(t.upper())
            tech_score = ta.get("tech_score", 0) if ta else None
            fund_score = latest_scores.get(t.upper())
            v = compute_verdict(fund_score, tech_score, macro["macro_score"])
            w_verdicts.append((t.upper(), v))

        if w_verdicts:
            _ORDER = {"STRONG BUY": 0, "BUY": 1, "ACCUMULATE": 2, "NEUTRAL": 3,
                      "WATCH": 4, "HOLD": 5, "AVOID": 6}
            w_verdicts.sort(key=lambda x: (_ORDER.get(x[1]["verdict"], 9),
                                            -(x[1].get("fund") or 0)))
            print_verdict_table(w_verdicts, title="WATCHLIST VERDICTS")

            # Highlight actionable
            buys = [s for s, v in w_verdicts if v["verdict"] in ("STRONG BUY", "BUY")]
            if buys:
                print(f"\n  📈 Actionable: {', '.join(buys)}")
        else:
            print("  Could not fetch data.\n")
    else:
        print("\n  Watchlist is empty — skipping.")

    # 3. Discover new candidates (not in portfolio/watchlist)
    _section("DISCOVER — New Arrivals")
    from commands.discover import _collect_all_candidates
    from utils.discovery import PRESETS
    all_results, excluded = _collect_all_candidates()
    new_candidates = {t: info for t, info in all_results.items() if t not in excluded}
    ranked = sorted(new_candidates.values(), key=lambda x: len(x["presets"]), reverse=True)

    if ranked:
        print(f"  🆕 {len(ranked)} NEW stocks found (not in portfolio/watchlist):\n")
        print(f"  {'#':>3}  {'Ticker':<8}{'Company':<30}{'Conviction':<12}{'P/E':>6}{'Price':>10}")
        print(f"  {'─' * 72}")
        for i, info in enumerate(ranked[:20], 1):
            conv = len(info["presets"])
            stars = "★" * conv + "☆" * (len(PRESETS) - conv)
            pe = str(info.get("pe", "-"))[:6]
            price = f"${info.get('price', '-')}"
            print(f"  {i:>3}  {info['ticker']:<8}{info['company'][:29]:<30}{stars:<12}{pe:>6}{price:>10}")

        if len(ranked) > 20:
            print(f"\n  ... and {len(ranked) - 20} more.")
        top5 = [r["ticker"] for r in ranked[:5]]
        print(f"\n  Add to watchlist:  python stock.py watchlist add {' '.join(top5)}")
    else:
        print("  ✅ No new candidates — your watchlist covers all Finviz matches.")

    # 4. Score movers (all tracked stocks)
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

    # 0. Full macro dashboard
    _section("GLOBAL MACRO ENVIRONMENT")
    from macro.analysis import analyze_macro
    from output.macro import print_macro_full
    macro = analyze_macro()
    print_macro_full(macro)

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

    # 5. Triangulated verdicts for combined portfolio + watchlist
    all_tracked = []
    if has_portfolio:
        from utils.lists import portfolio_list as pl3
        all_tracked.extend(pl3())
    if has_watchlist:
        from utils.lists import watchlist_list as wl3
        all_tracked.extend(wl3())

    if all_tracked:
        _section("VERDICTS — All Tracked Stocks")
        from technical.analysis import analyze_technical
        from verdict.engine import compute_verdict
        from output.verdict import print_verdict_table
        from utils.database import get_latest_scores as gls2
        latest_bs = {r["symbol"]: r.get("fundamental_score") for r in gls2()}

        all_verdicts = []
        seen = set()
        for t in all_tracked:
            sym = t.upper()
            if sym in seen:
                continue
            seen.add(sym)
            ta = analyze_technical(sym)
            tech_score = ta.get("tech_score", 0) if ta else None
            fund_score = latest_bs.get(sym)
            v = compute_verdict(fund_score, tech_score, macro["macro_score"])
            all_verdicts.append((sym, v))

        if all_verdicts:
            _ORDER = {"STRONG BUY": 0, "BUY": 1, "ACCUMULATE": 2, "NEUTRAL": 3,
                      "WATCH": 4, "HOLD": 5, "AVOID": 6}
            all_verdicts.sort(key=lambda x: (_ORDER.get(x[1]["verdict"], 9),
                                              -(x[1].get("fund") or 0)))
            print_verdict_table(all_verdicts, title="ALL TRACKED STOCKS")

            buys = [s for s, v in all_verdicts if v["verdict"] in ("STRONG BUY", "BUY")]
            accum = [s for s, v in all_verdicts if v["verdict"] == "ACCUMULATE"]
            if buys:
                print(f"\n  📈 HIGHEST CONVICTION: {', '.join(buys)}")
            if accum:
                print(f"  📊 ACCUMULATE: {', '.join(accum)}")

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
