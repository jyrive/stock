"""Macro analysis output — print functions for macro dashboard."""

from macro.analysis import (
    _score_vix,
    _score_sp500_vs_200,
    _score_yield_spread,
    _score_sp500_52w,
    _score_10y_yield,
)


def macro_one_liner(macro):
    """Return a single-line summary string for compact workflow output."""
    d = macro["indicators"]
    vix = d.get("^VIX", {}).get("current")
    y10 = d.get("^TNX", {}).get("current")
    sp_pct = d.get("^GSPC", {}).get("pct_vs_200")

    vix_s = f"VIX {vix:.0f}" if vix else "VIX -"
    y10_s = f"10Y {y10:.1f}%" if y10 else "10Y -"
    sp_s = f"S&P {sp_pct:+.1f}% vs 200MA" if sp_pct is not None else "S&P -"

    icon = macro["environment"].split(" ")[0]
    return f"Macro: {macro['macro_score']}/100 {icon} — {vix_s}, {y10_s}, {sp_s}"


def print_macro_compact(macro):
    """Print a compact macro summary (~10 lines)."""
    d = macro["indicators"]
    score = macro["macro_score"]

    print(f"\n  {'─' * 60}")
    print(f"  MACRO ENVIRONMENT                    Score: {score}/100")
    print(f"  {'─' * 60}")

    # US
    sp = d.get("^GSPC", {})
    vix = d.get("^VIX", {})
    sp_str = f"{sp.get('pct_vs_200', 0):+.1f}% vs 200MA" if sp else "-"
    vix_str = f"{vix.get('current', 0):.0f}" if vix else "-"
    y10 = d.get("^TNX", {})
    y10_str = f"{y10.get('current', 0):.1f}%" if y10 else "-"
    spread = macro.get("yield_spread")
    spread_str = f"{spread:+.2f}%" if spread is not None else "-"
    spread_note = ""
    if spread is not None:
        if spread < -0.5:
            spread_note = " ⚠️ inverted"
        elif spread < 0:
            spread_note = " ⚠️ flat"
    print(f"  🇺🇸 US        S&P 500 {sp_str}    VIX: {vix_str}    10Y: {y10_str}    Spread: {spread_str}{spread_note}")

    # Europe
    stoxx = d.get("^STOXX", {})
    eur = d.get("EURUSD=X", {})
    stoxx_str = f"{stoxx.get('pct_vs_200', 0):+.1f}% vs 200MA" if stoxx else "-"
    eur_str = f"{eur.get('current', 0):.2f}" if eur else "-"
    print(f"  🇪🇺 Europe    STOXX 600 {stoxx_str}    EUR/USD: {eur_str}")

    # Asia
    nk = d.get("^N225", {})
    nk_str = f"{nk.get('pct_vs_200', 0):+.1f}% vs 200MA" if nk else "-"
    print(f"  🇯🇵 Asia      Nikkei {nk_str}")

    # Emerging
    eem = d.get("EEM", {})
    eem_str = f"{eem.get('pct_vs_200', 0):+.1f}% vs 200MA" if eem else "-"
    print(f"  🌍 Emerging   EEM {eem_str}")

    # Commodities
    gold = d.get("GC=F", {})
    oil = d.get("CL=F", {})
    copper = d.get("HG=F", {})
    g_str = f"${gold.get('current', 0):,.0f}" if gold else "-"
    o_str = f"${oil.get('current', 0):.0f}" if oil else "-"
    c_str = f"${copper.get('current', 0):.2f}" if copper else "-"
    print(f"  🛢  Commodities  Oil: {o_str}    Gold: {g_str}    Copper: {c_str}")

    # USD
    usd = d.get("DX-Y.NYB", {})
    usd_str = f"{usd.get('current', 0):.1f}" if usd else "-"
    usd_ytd = f" ({usd.get('ytd_pct', 0):+.1f}% YTD)" if usd and usd.get("ytd_pct") is not None else ""
    print(f"  💵 USD Index   {usd_str}{usd_ytd}")

    # Breadth + environment
    above = macro["breadth_above"]
    below = macro["breadth_below"]
    print(f"\n  Global breadth: {above}/4 regions above 200-MA")
    print(f"  {macro['environment']}")
    print()


def print_macro_full(macro):
    """Print full macro dashboard with detailed breakdown."""
    d = macro["indicators"]
    score = macro["macro_score"]

    print()
    print("=" * 66)
    print("  GLOBAL MACRO DASHBOARD")
    print("=" * 66)
    print(f"\n  Macro Score: {score}/100")
    print(f"  {macro['environment']}")

    # ── Regional Markets ──
    print(f"\n  {'─' * 62}")
    print(f"  REGIONAL MARKETS")
    print(f"  {'─' * 62}")
    print(f"  {'Region':<12}{'Index':<16}{'Price':>10}{'vs 200MA':>10}{'52w Pos':>9}{'YTD':>8}")
    print(f"  {'─' * 62}")

    for sym in ("^GSPC", "^STOXX", "^N225", "EEM"):
        ind = d.get(sym)
        if not ind:
            continue
        region = {"^GSPC": "🇺🇸 US", "^STOXX": "🇪🇺 Europe", "^N225": "🇯🇵 Asia", "EEM": "🌍 EM"}[sym]
        price = f"{ind['current']:,.1f}" if ind["current"] > 100 else f"{ind['current']:.2f}"
        pct = f"{ind['pct_vs_200']:+.1f}%" if ind.get("pct_vs_200") is not None else "-"
        pos = f"{ind['pos_52w']:.0f}%" if ind.get("pos_52w") is not None else "-"
        ytd = f"{ind['ytd_pct']:+.1f}%" if ind.get("ytd_pct") is not None else "-"
        print(f"  {region:<12}{ind['label']:<16}{price:>10}{pct:>10}{pos:>9}{ytd:>8}")

    # ── Rates & Volatility ──
    print(f"\n  {'─' * 62}")
    print(f"  RATES & VOLATILITY")
    print(f"  {'─' * 62}")

    vix = d.get("^VIX", {})
    y10 = d.get("^TNX", {})
    y2 = d.get("2YY=F", {})
    spread = macro.get("yield_spread")

    if vix:
        vix_signal = ""
        v = vix["current"]
        if v > 30:
            vix_signal = "  ← 🔴 Extreme fear"
        elif v > 22:
            vix_signal = "  ← 🟡 Elevated"
        elif v < 14:
            vix_signal = "  ← ⚠️ Complacency"
        print(f"  VIX (Fear Index):    {v:>8.1f}{vix_signal}")

    if y10:
        print(f"  10Y Treasury Yield:  {y10['current']:>8.2f}%")
    if y2:
        print(f"  2Y Treasury Yield:   {y2['current']:>8.2f}%")
    if spread is not None:
        spread_signal = ""
        if spread < -0.5:
            spread_signal = "  ← ⚠️ INVERTED — recession risk"
        elif spread < 0:
            spread_signal = "  ← ⚠️ Flat/inverted"
        elif spread > 1.5:
            spread_signal = "  ← Early recovery signal"
        print(f"  2Y-10Y Spread:       {spread:>+8.2f}%{spread_signal}")

    # ── Commodities ──
    print(f"\n  {'─' * 62}")
    print(f"  COMMODITIES & CURRENCY")
    print(f"  {'─' * 62}")
    print(f"  {'Indicator':<20}{'Price':>12}{'vs 200MA':>10}{'52w Pos':>9}{'YTD':>8}")
    print(f"  {'─' * 62}")

    for sym in ("GC=F", "CL=F", "HG=F", "DX-Y.NYB", "EURUSD=X"):
        ind = d.get(sym)
        if not ind:
            continue
        price = f"${ind['current']:,.2f}" if ind["current"] < 200 else f"${ind['current']:,.0f}"
        pct = f"{ind['pct_vs_200']:+.1f}%" if ind.get("pct_vs_200") is not None else "-"
        pos = f"{ind['pos_52w']:.0f}%" if ind.get("pos_52w") is not None else "-"
        ytd = f"{ind['ytd_pct']:+.1f}%" if ind.get("ytd_pct") is not None else "-"
        print(f"  {ind['label']:<20}{price:>12}{pct:>10}{pos:>9}{ytd:>8}")

    # ── Score breakdown ──
    print(f"\n  {'─' * 62}")
    print(f"  MACRO SCORE BREAKDOWN    Total: {score}/100")
    print(f"  {'─' * 62}")

    vix_score = _score_vix(vix.get("current") if vix else None)
    sp_score = _score_sp500_vs_200(d.get("^GSPC", {}).get("pct_vs_200"))
    spread_score = _score_yield_spread(spread)
    sp52_score = _score_sp500_52w(d.get("^GSPC", {}).get("pos_52w"))
    y10_score = _score_10y_yield(y10.get("current") if y10 else None)

    print(f"  {'Component':<25}{'Score':>6}{'Max':>6}  Rationale")
    print(f"  {'─' * 62}")
    print(f"  {'VIX (fear = opportunity)':<25}{vix_score:>6}{25:>6}  Higher VIX = better entry")
    print(f"  {'S&P 500 vs 200-MA':<25}{sp_score:>6}{25:>6}  Below MA = cheaper market")
    print(f"  {'Yield Spread (2-10Y)':<25}{spread_score:>6}{20:>6}  Normal curve = healthy")
    print(f"  {'S&P 52-week position':<25}{sp52_score:>6}{15:>6}  Near lows = opportunity")
    print(f"  {'10Y Yield level':<25}{y10_score:>6}{15:>6}  Lower = equity-friendly")

    # ── Interpretation ──
    print(f"\n  {'─' * 62}")
    print(f"  INTERPRETATION")
    print(f"  {'─' * 62}")
    above = macro["breadth_above"]
    below = macro["breadth_below"]
    print(f"  Global breadth:  {above}/4 regions above 200-day MA")

    if score >= 70:
        print("  Stance:  Aggressive — high conviction buys warranted")
        print("  Sizing:  Full positions on quality stocks")
    elif score >= 50:
        print("  Stance:  Constructive — normal buying, favor quality")
        print("  Sizing:  Normal position sizes")
    elif score >= 35:
        print("  Stance:  Cautious — reduce position sizes, be selective")
        print("  Sizing:  Half positions, average in gradually")
    else:
        print("  Stance:  Defensive — preserve capital, wait for better entry")
        print("  Sizing:  Minimal new positions, build cash")

    print(f"\n  {macro['environment']}")
    print()
