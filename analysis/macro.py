"""Macro-economic environment analysis — global market context.

Fetches global macro indicators via yfinance and scores the current
environment for equity investing (0–100, higher = more favorable).

Three-layer decision model:
    1. Fundamental Score  → WHAT to buy  (fundamental quality)
    2. Technical Score → WHEN to buy  (stock-level entry)
    3. Macro Score    → HOW MUCH     (position sizing context)

Indicators:
    US:        S&P 500 vs 200-MA, VIX, 10Y yield, 2Y-10Y spread
    Europe:    STOXX 600 vs 200-MA, EUR/USD
    Asia:      Nikkei 225 vs 200-MA
    Emerging:  EEM vs 200-MA
    Commodities: Gold, Oil (WTI), Copper
    Currency:  USD Index
"""

import numpy as np

from datasources.market import get_price_history

# ── Ticker map ──────────────────────────────────────────────────

_INDICATORS = {
    # symbol          label                 category
    "^GSPC":         ("S&P 500",            "us"),
    "^STOXX":        ("STOXX 600",          "europe"),
    "^N225":         ("Nikkei 225",         "asia"),
    "EEM":           ("MSCI EM ETF",        "emerging"),
    "^VIX":          ("VIX",                "volatility"),
    "^TNX":          ("10Y Treasury",       "rates"),
    "2YY=F":         ("2Y Treasury",        "rates"),
    "DX-Y.NYB":     ("USD Index",           "currency"),
    "EURUSD=X":      ("EUR/USD",            "currency"),
    "GC=F":          ("Gold",               "commodities"),
    "CL=F":          ("Oil (WTI)",          "commodities"),
    "HG=F":          ("Copper",             "commodities"),
}

# ── Data fetching ───────────────────────────────────────────────

def fetch_indicator(symbol, period="1y"):
    """Fetch price history for a single indicator. Returns dict or None."""
    try:
        h = get_price_history(symbol, period=period)
        if h is None or h.empty or len(h) < 50:
            return None

        closes = h["Close"].values.astype(float)
        label, category = _INDICATORS[symbol]

        sma200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else float(np.mean(closes))
        sma50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else None

        high_52w = float(np.max(closes))
        low_52w = float(np.min(closes))
        current = float(closes[-1])

        pct_vs_200 = ((current - sma200) / sma200) * 100 if sma200 else None
        pos_52w = ((current - low_52w) / (high_52w - low_52w) * 100) if high_52w != low_52w else 50.0

        ytd_pct = None
        if len(h) > 0:
            idx = h.index
            year_start = idx[0]
            for i, dt in enumerate(idx):
                if hasattr(dt, 'year') and dt.year == idx[-1].year:
                    year_start = idx[i]
                    break
            start_price = float(h["Close"].iloc[h.index.get_indexer([year_start], method="nearest")[0]])
            if start_price:
                ytd_pct = ((current - start_price) / start_price) * 100

        return {
            "symbol": symbol,
            "label": label,
            "category": category,
            "current": current,
            "sma200": sma200,
            "sma50": sma50,
            "pct_vs_200": pct_vs_200,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pos_52w": pos_52w,
            "ytd_pct": ytd_pct,
        }
    except Exception:
        return None

def fetch_all():
    """Fetch all macro indicators. Returns dict keyed by symbol."""
    results = {}
    for sym in _INDICATORS:
        data = fetch_indicator(sym)
        if data:
            results[sym] = data
    return results

# ── Scoring ─────────────────────────────────────────────────────

def score_vix(vix_current):
    """Score VIX: high fear = buying opportunity (higher score)."""
    if vix_current is None:
        return 10
    if vix_current > 35:
        return 25
    if vix_current > 28:
        return 20
    if vix_current > 22:
        return 15
    if vix_current > 18:
        return 10
    if vix_current > 13:
        return 5
    return 0

def score_sp500_vs_200(pct):
    """Score S&P 500 vs 200-MA: below = opportunity (higher score)."""
    if pct is None:
        return 10
    if pct < -15:
        return 25
    if pct < -10:
        return 22
    if pct < -5:
        return 18
    if pct < 0:
        return 14
    if pct < 5:
        return 10
    if pct < 10:
        return 5
    return 2

def score_yield_spread(spread):
    """Score 2Y-10Y yield spread: normal = healthy, inverted = danger."""
    if spread is None:
        return 10
    if spread < -0.5:
        return 0
    if spread < 0:
        return 5
    if spread < 0.5:
        return 12
    if spread < 1.5:
        return 20
    return 15

def score_sp500_52w(pos_pct):
    """Score S&P 500 52-week position: near lows = opportunity."""
    if pos_pct is None:
        return 7
    if pos_pct < 20:
        return 15
    if pos_pct < 35:
        return 12
    if pos_pct < 50:
        return 8
    if pos_pct < 70:
        return 5
    if pos_pct < 85:
        return 3
    return 0

def score_10y_yield(yield_pct):
    """Score 10Y yield level: lower = more favorable for stocks."""
    if yield_pct is None:
        return 7
    if yield_pct < 2.5:
        return 15
    if yield_pct < 3.5:
        return 13
    if yield_pct < 4.0:
        return 10
    if yield_pct < 4.5:
        return 7
    if yield_pct < 5.0:
        return 4
    return 1

def compute_macro_score(data):
    """Compute macro environment score 0–100.

    Weights:
        VIX             25 pts
        S&P 500 vs 200  25 pts
        Yield spread    20 pts
        S&P 52-week pos 15 pts
        10Y yield level 15 pts
    """
    vix = data.get("^VIX", {}).get("current")
    sp_pct = data.get("^GSPC", {}).get("pct_vs_200")
    sp_52w = data.get("^GSPC", {}).get("pos_52w")

    y10 = data.get("^TNX", {}).get("current")
    y2 = data.get("2YY=F", {}).get("current")
    spread = (y10 - y2) if (y10 is not None and y2 is not None) else None

    score = (
        score_vix(vix) +
        score_sp500_vs_200(sp_pct) +
        score_yield_spread(spread) +
        score_sp500_52w(sp_52w) +
        score_10y_yield(y10)
    )
    return min(100, max(0, score))

# ── Global breadth ──────────────────────────────────────────────

def global_breadth(data):
    """Count how many major regions are above/below their 200-MA."""
    regions = {
        "^GSPC": "US",
        "^STOXX": "Europe",
        "^N225": "Asia",
        "EEM": "Emerging",
    }
    above = 0
    below = 0
    details = []
    for sym, name in regions.items():
        ind = data.get(sym)
        if ind and ind.get("pct_vs_200") is not None:
            pct = ind["pct_vs_200"]
            if pct >= 0:
                above += 1
                details.append((name, pct, "above"))
            else:
                below += 1
                details.append((name, pct, "below"))
    return above, below, details

# ── Environment label ───────────────────────────────────────────

def environment_label(macro_score, above, below):
    """Return an environment description based on score and breadth."""
    total = above + below
    breadth_ratio = above / total if total > 0 else 0.5

    if macro_score >= 70:
        if breadth_ratio >= 0.75:
            return "🟢 RISK-ON — Broad global rally, favorable entry conditions"
        return "🟢 FAVORABLE — High fear or valuations creating opportunities"
    if macro_score >= 50:
        if breadth_ratio >= 0.5:
            return "🟡 CONSTRUCTIVE — Mostly healthy, selective buying"
        return "🟡 MIXED — Some regions strong, others weak"
    if macro_score >= 35:
        if breadth_ratio < 0.25:
            return "🟠 CAUTIOUS — Most regions weak, be selective"
        return "🟠 MIXED — Elevated uncertainty, favor quality"
    return "🔴 DEFENSIVE — Risk-off environment, preserve capital"

# ── Main function ───────────────────────────────────────────────

def analyze_macro():
    """Run full macro environment analysis. Returns dict with all data + score."""
    data = fetch_all()

    y10 = data.get("^TNX", {}).get("current")
    y2 = data.get("2YY=F", {}).get("current")
    spread = (y10 - y2) if (y10 is not None and y2 is not None) else None

    macro_score = compute_macro_score(data)
    above, below, breadth = global_breadth(data)
    label = environment_label(macro_score, above, below)

    return {
        "indicators": data,
        "macro_score": macro_score,
        "yield_spread": spread,
        "breadth_above": above,
        "breadth_below": below,
        "breadth_detail": breadth,
        "environment": label,
    }

# ── Display Functions ────────────────────────────────────────────

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

    vix_score = score_vix(vix.get("current") if vix else None)
    sp_score = score_sp500_vs_200(d.get("^GSPC", {}).get("pct_vs_200"))
    spread_score = score_yield_spread(spread)
    sp52_score = score_sp500_52w(d.get("^GSPC", {}).get("pos_52w"))
    y10_score = score_10y_yield(y10.get("current") if y10 else None)

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
