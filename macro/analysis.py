"""Macro-economic environment analysis — global market context.

Fetches global macro indicators via yfinance and scores the current
environment for equity investing (0–100, higher = more favorable).

Three-layer decision model:
    1. Buffett Score  → WHAT to buy  (fundamental quality)
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

import warnings
import numpy as np
import yfinance as yf

warnings.filterwarnings("ignore")

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

def _fetch_indicator(symbol, period="1y"):
    """Fetch price history for a single indicator. Returns dict or None."""
    try:
        t = yf.Ticker(symbol)
        h = t.history(period=period)
        if h.empty or len(h) < 50:
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


def _fetch_all():
    """Fetch all macro indicators. Returns dict keyed by symbol."""
    results = {}
    for sym in _INDICATORS:
        data = _fetch_indicator(sym)
        if data:
            results[sym] = data
    return results


# ── Scoring ─────────────────────────────────────────────────────

def _score_vix(vix_current):
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


def _score_sp500_vs_200(pct):
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


def _score_yield_spread(spread):
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


def _score_sp500_52w(pos_pct):
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


def _score_10y_yield(yield_pct):
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


def _compute_macro_score(data):
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
        _score_vix(vix) +
        _score_sp500_vs_200(sp_pct) +
        _score_yield_spread(spread) +
        _score_sp500_52w(sp_52w) +
        _score_10y_yield(y10)
    )
    return min(100, max(0, score))


# ── Global breadth ──────────────────────────────────────────────

def _global_breadth(data):
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

def _environment_label(macro_score, above, below):
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
    data = _fetch_all()

    y10 = data.get("^TNX", {}).get("current")
    y2 = data.get("2YY=F", {}).get("current")
    spread = (y10 - y2) if (y10 is not None and y2 is not None) else None

    macro_score = _compute_macro_score(data)
    above, below, breadth = _global_breadth(data)
    label = _environment_label(macro_score, above, below)

    return {
        "indicators": data,
        "macro_score": macro_score,
        "yield_spread": spread,
        "breadth_above": above,
        "breadth_below": below,
        "breadth_detail": breadth,
        "environment": label,
    }
