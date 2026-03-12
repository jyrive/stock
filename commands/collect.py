"""Data collection pipeline — build historical dataset for continuous learning.

Collects and persists:
    1. Fundamental snapshots (point-in-time info dict)
    2. Quarterly financial statements (income, balance, cashflow)
    3. Daily price cache (OHLCV for all watched tickers)
    4. Macro indicator cache (VIX, yields, USD, gold, oil, indices)

Usage:
    python stock.py collect                   # collect all (portfolio + watchlist)
    python stock.py collect AAPL MSFT         # collect specific tickers
    python stock.py collect --backfill        # backfill quarterly data + 5y prices
    python stock.py collect --macro           # only refresh macro indicators
    python stock.py collect --stats           # show data coverage report

This builds the dataset that the `study` command uses for unbiased ML analysis.
Run collect regularly (weekly is ideal) to accumulate point-in-time fundamentals.
"""

import sys
import time
from datetime import date, datetime

from datasources.market import get_info, get_quarterly_financials, get_price_history, get_macro_history

from utils.snapshot_db import (
    save_fundamental_snapshot,
    save_quarterly_financials,
    save_prices,
    save_macro,
    get_datastore_stats,
    get_price_range,
    get_macro_range,
    get_snapshot_coverage,
)
from utils.lists import portfolio_list, watchlist_list
from utils.config import enable_cache

# Same macro tickers used by study.py and macro/analysis.py
MACRO_TICKERS = [
    ("^GSPC", "S&P 500"),
    ("^STOXX", "STOXX 600"),
    ("^N225", "Nikkei 225"),
    ("EEM", "Emerging Mkts"),
    ("^VIX", "VIX"),
    ("^TNX", "10Y Yield"),
    ("2YY=F", "2Y Yield"),
    ("DX-Y.NYB", "USD Index"),
    ("EURUSD=X", "EUR/USD"),
    ("GC=F", "Gold"),
    ("CL=F", "Oil (WTI)"),
    ("HG=F", "Copper"),
]

# ═══════════════════════════════════════════════════════════════════════
#  Collect fundamentals for a ticker
# ═══════════════════════════════════════════════════════════════════════

def collect_ticker(symbol, backfill=False):
    """Collect all data for one ticker: snapshot + quarterly + prices.

    Returns dict with counts of saved items.
    """
    result = {"fundamentals": 0, "quarterly": 0, "prices": 0}
    sym = symbol.upper()

    try:
        # 1. Fundamental snapshot (today's point-in-time)
        info = get_info(sym)
        if info and info.get("marketCap"):
            save_fundamental_snapshot(sym, info)
            result["fundamentals"] = 1

        # 2. Quarterly financials (backfill ~5 quarters)
        ticker_obj = get_quarterly_financials(sym)
        if ticker_obj:
            qtr_saved = save_quarterly_financials(sym, ticker_obj)
            result["quarterly"] = qtr_saved

        # 3. Price history
        # Check what we already have
        first, last, cnt = get_price_range(sym)
        if backfill or cnt == 0:
            period = "5y"
        elif last:
            # Only fetch what's missing (from last cached date)
            period = "1mo"
        else:
            period = "2y"

        hist = get_price_history(sym, period=period)
        if hist is not None and len(hist) > 0:
            result["prices"] = save_prices(sym, hist)

    except Exception as e:
        print(f"    Error collecting {sym}: {e}")

    return result

# ═══════════════════════════════════════════════════════════════════════
#  Collect macro indicators
# ═══════════════════════════════════════════════════════════════════════

def collect_macro(backfill=False):
    """Collect/refresh all macro indicator data."""
    total_saved = 0

    for sym, name in MACRO_TICKERS:
        try:
            first, last, cnt = get_macro_range(sym)
            if backfill or cnt == 0:
                period = "5y"
            else:
                period = "1mo"

            hist = get_macro_history(sym, period=period)
            if hist is not None and len(hist) > 0:
                n = save_macro(sym, hist)
                total_saved += n
                print(f"    {name:20s} ({sym:12s}):  {n:>5d} days cached")
        except Exception as e:
            print(f"    Error: {name} ({sym}): {e}")

    return total_saved

# ═══════════════════════════════════════════════════════════════════════
#  Coverage report
# ═══════════════════════════════════════════════════════════════════════

def print_stats():
    """Print data coverage statistics."""
    G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"; W = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"

    stats = get_datastore_stats()

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║       DATA STORE — Coverage Report                         ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    # Fundamentals
    fs = stats.get("fundamentals", {})
    n_tick = fs.get("tickers", 0)
    n_snap = fs.get("snapshots", 0)
    print(f"  {BOLD}Fundamental Snapshots{W}")
    if n_snap > 0:
        print(f"    Tickers:   {n_tick}")
        print(f"    Snapshots: {n_snap}")
        print(f"    Range:     {fs.get('first_date')} → {fs.get('last_date')}")
        avg = n_snap / max(n_tick, 1)
        if avg >= 4:
            print(f"    {G}✓ Good coverage ({avg:.1f} snapshots/ticker){W}")
        else:
            print(f"    {Y}⚠ Building... ({avg:.1f} snapshots/ticker, need weekly scans){W}")
    else:
        print(f"    {Y}No data yet — run 'python stock.py collect' to start{W}")
    print()

    # Quarterly financials
    qs = stats.get("quarterly", {})
    n_qrec = qs.get("records", 0)
    print(f"  {BOLD}Quarterly Financials{W}")
    if n_qrec > 0:
        print(f"    Tickers:   {qs.get('tickers', 0)}")
        print(f"    Records:   {n_qrec}")
        print(f"    Period:    {qs.get('earliest_period')} → {qs.get('latest_period')}")
        print(f"    {G}✓ Quarterly data available for trend analysis{W}")
    else:
        print(f"    {Y}No data yet — run 'python stock.py collect --backfill'{W}")
    print()

    # Price cache
    ps = stats.get("prices", {})
    n_prec = ps.get("records", 0)
    print(f"  {BOLD}Price Cache{W}")
    if n_prec > 0:
        print(f"    Tickers:   {ps.get('tickers', 0)}")
        print(f"    Records:   {n_prec:,}")
        print(f"    Range:     {ps.get('first_date')} → {ps.get('last_date')}")
        print(f"    {G}✓ Local price data available (offline-capable){W}")
    else:
        print(f"    {Y}No data yet — will be populated on next collect{W}")
    print()

    # Macro cache
    ms = stats.get("macro", {})
    n_mrec = ms.get("records", 0)
    print(f"  {BOLD}Macro Cache{W}")
    if n_mrec > 0:
        print(f"    Indicators: {ms.get('indicators', 0)}")
        print(f"    Records:    {n_mrec:,}")
        print(f"    Range:      {ms.get('first_date')} → {ms.get('last_date')}")
        print(f"    {G}✓ Macro data cached locally{W}")
    else:
        print(f"    {Y}No data yet — run 'python stock.py collect --macro'{W}")
    print()

    # Per-ticker snapshot coverage
    coverage = get_snapshot_coverage()
    if coverage:
        print(f"  {BOLD}Per-Ticker Snapshot History{W}")
        print(f"  {'Ticker':8s}  {'Snapshots':>10s}  {'First':12s}  {'Latest':12s}")
        print(f"  {'─' * 50}")
        for sym in sorted(coverage.keys()):
            dates = coverage[sym]
            color = G if len(dates) >= 4 else (Y if len(dates) >= 2 else W)
            print(f"  {color}{sym:8s}  {len(dates):>10d}  {dates[0]:12s}  {dates[-1]:12s}{W}")
        print()

    # ML readiness assessment
    print(f"  {BOLD}ML Readiness{W}")
    snap_tickers = fs.get("tickers", 0)
    snap_count = fs.get("snapshots", 0)
    avg_snaps = snap_count / max(snap_tickers, 1)

    if snap_tickers >= 20 and avg_snaps >= 12:
        print(f"  {G}✓ Enough data for reliable ML study — point-in-time fundamentals available{W}")
    elif snap_tickers >= 10 and avg_snaps >= 4:
        print(f"  {Y}⚠ Growing — keep collecting weekly. {snap_tickers} tickers × {avg_snaps:.0f} snapshots{W}")
        weeks_needed = max(0, int((12 - avg_snaps)))
        print(f"    Estimated {weeks_needed} more weeks until ML-ready{W}")
    else:
        print(f"  {Y}⚠ Just started — need weekly collections over 3-6 months{W}")
        print(f"    Current: {snap_tickers} tickers, {avg_snaps:.1f} avg snapshots")
        print(f"    Target:  20+ tickers, 12+ snapshots each")
    print()

# ═══════════════════════════════════════════════════════════════════════
#  Main entry point
# ═══════════════════════════════════════════════════════════════════════

def main(args=None):
    """Execute data collection pipeline."""
    if args is None:
        args = sys.argv[1:]
    G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"; W = "\033[0m"; BOLD = "\033[1m"

    # Parse flags
    backfill = "--backfill" in args
    macro_only = "--macro" in args
    stats_only = "--stats" in args
    remaining = [a for a in args if not a.startswith("--")]

    enable_cache()

    if stats_only:
        print_stats()
        return

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║       DATA COLLECTION PIPELINE                             ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    # ── Macro indicators ──
    print(f"  {BOLD}Collecting macro indicators...{W}")
    macro_total = collect_macro(backfill=backfill)
    print(f"  {G}→ {macro_total:,} macro data points cached{W}\n")

    if macro_only:
        print_stats()
        return

    # ── Determine tickers ──
    if remaining:
        tickers = [t.upper() for t in remaining]
    else:
        # Portfolio + watchlist
        try:
            tickers = list(set(portfolio_list() + watchlist_list()))
        except Exception:
            tickers = []

    if not tickers:
        print(f"  {Y}No tickers to collect. Specify tickers or add to portfolio/watchlist.{W}")
        print(f"  Usage: python stock.py collect AAPL MSFT GOOGL")
        print(f"         python stock.py collect --backfill")
        return

    tickers.sort()
    print(f"  {BOLD}Collecting data for {len(tickers)} tickers...{W}")
    if backfill:
        print(f"  {B}Backfill mode: 5y price history + quarterly financials{W}\n")

    total = {"fundamentals": 0, "quarterly": 0, "prices": 0}
    for i, sym in enumerate(tickers):
        result = collect_ticker(sym, backfill=backfill)
        total["fundamentals"] += result["fundamentals"]
        total["quarterly"] += result["quarterly"]
        total["prices"] += result["prices"]

        status = []
        if result["fundamentals"]:
            status.append("snapshot")
        if result["quarterly"]:
            status.append(f"{result['quarterly']}q")
        if result["prices"]:
            status.append(f"{result['prices']}d")

        print(f"    [{i+1:>2d}/{len(tickers)}] {sym:6s}  {', '.join(status) if status else 'no data'}")

        # Rate limiting
        if (i + 1) % 5 == 0:
            time.sleep(0.5)

    print(f"\n  {BOLD}Collection Summary{W}")
    print(f"  Fundamental snapshots:  {total['fundamentals']}")
    print(f"  Quarterly statements:   {total['quarterly']}")
    print(f"  Price records cached:   {total['prices']:,}")
    print(f"  Macro records cached:   {macro_total:,}")
    print()

    # Show coverage
    print_stats()
