"""Peer comparison: fetch same-sector peers and display side-by-side table."""

import yfinance as yf


# Fallback peers per sector when yfinance doesn't return enough
_SECTOR_PEERS = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "ORCL", "CRM", "ADBE", "INTC", "CSCO"],
    "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA"],
    "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "BMY", "AMGN"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "TJX", "LOW", "CMG", "LULU"],
    "Consumer Defensive": ["PG", "KO", "PEP", "WMT", "COST", "CL", "MDLZ", "GIS", "KHC", "STZ"],
    "Industrials": ["HON", "UPS", "CAT", "GE", "MMM", "RTX", "BA", "LMT", "DE", "ETN"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "MPC", "PSX", "VLO", "KMI"],
    "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA"],
    "Basic Materials": ["LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "DOW", "NUE", "CF"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ES"],
}


def find_peers(symbol, sector, industry, max_peers=5):
    """Find same-sector peers for comparison.

    Strategy:
    1. Try yfinance's built-in recommendations/peers
    2. Fall back to sector-based peer list
    3. Exclude the target stock itself
    """
    peers = []

    # Try yfinance recommendations
    try:
        ticker = yf.Ticker(symbol)
        # yfinance has a recommendations property; sometimes has peers
        recs = getattr(ticker, "recommendations", None)
        if recs is not None and hasattr(recs, "index") and len(recs) > 0:
            # recommendations is a DataFrame with 'To Grade', 'From Grade' etc.
            # Not peer symbols — skip this approach
            pass
    except Exception:
        pass

    # Use sector-based fallback
    if not peers and sector in _SECTOR_PEERS:
        peers = [p for p in _SECTOR_PEERS[sector] if p != symbol.upper()]

    # Generic fallback
    if not peers:
        peers = [p for p in _SECTOR_PEERS.get("Technology", []) if p != symbol.upper()]

    return peers[:max_peers]


def fetch_peer_metrics(symbols):
    """Fetch key comparison metrics for a list of symbols.

    Returns list of dicts with: symbol, name, sector, industry,
    market_cap_b, roe, pe, de, current_ratio, fcf_yield, div_yield, margin.
    """
    results = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            if not info or "marketCap" not in info:
                continue

            mc = info.get("marketCap", 0)
            price = info.get("currentPrice", info.get("regularMarketPrice", 0))
            fcf = info.get("freeCashflow")
            fcf_yield = (fcf / mc * 100) if fcf and mc else None

            results.append({
                "symbol": sym,
                "name": (info.get("longName") or info.get("shortName", sym))[:30],
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap_b": round(mc / 1e9, 1) if mc else None,
                "roe_pct": round(info.get("returnOnEquity", 0) * 100, 1) if info.get("returnOnEquity") else None,
                "trailing_pe": round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else None,
                "debt_to_equity": round(info.get("debtToEquity", 0), 0) if info.get("debtToEquity") else None,
                "current_ratio": round(info.get("currentRatio", 0), 2) if info.get("currentRatio") else None,
                "fcf_yield": round(fcf_yield, 1) if fcf_yield else None,
                "dividend_yield": round(info.get("dividendRate", 0) / price * 100, 2) if info.get("dividendRate") and price else None,
                "profit_margin": round(info.get("profitMargins", 0) * 100, 1) if info.get("profitMargins") else None,
                "revenue_growth": round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else None,
                "current_price": round(price, 2) if price else None,
            })
        except Exception:
            continue

    return results


def print_peer_comparison(target_symbol, target_data, peers):
    """Print a side-by-side peer comparison table."""
    from .colors import USE_COLOR, good, warn, bad, dim, BOLD, RESET

    all_stocks = []

    # Build target entry from the analysis data we already have
    info = target_data.get("info", {})
    mc = target_data.get("market_cap", 0)
    price = target_data.get("current_price", 0)
    fcf = info.get("freeCashflow")
    fcf_yield = (fcf / mc * 100) if fcf and mc else None

    target_entry = {
        "symbol": target_symbol,
        "name": (target_data.get("name", target_symbol))[:30],
        "sector": target_data.get("sector", "N/A"),
        "industry": target_data.get("industry", "N/A"),
        "market_cap_b": round(mc / 1e9, 1) if mc else None,
        "roe_pct": round(info.get("returnOnEquity", 0) * 100, 1) if info.get("returnOnEquity") else None,
        "trailing_pe": round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else None,
        "debt_to_equity": round(info.get("debtToEquity", 0), 0) if info.get("debtToEquity") else None,
        "current_ratio": round(info.get("currentRatio", 0), 2) if info.get("currentRatio") else None,
        "fcf_yield": round(fcf_yield, 1) if fcf_yield else None,
        "dividend_yield": round(info.get("dividendRate", 0) / price * 100, 2) if info.get("dividendRate") and price else None,
        "profit_margin": round(info.get("profitMargins", 0) * 100, 1) if info.get("profitMargins") else None,
        "revenue_growth": round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else None,
        "current_price": round(price, 2) if price else None,
    }
    all_stocks.append(target_entry)
    all_stocks.extend(peers)

    # Compute sector averages (excluding target)
    def _avg(key):
        vals = [p[key] for p in peers if p.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    avg = {
        "roe_pct": _avg("roe_pct"),
        "trailing_pe": _avg("trailing_pe"),
        "debt_to_equity": _avg("debt_to_equity"),
        "current_ratio": _avg("current_ratio"),
        "fcf_yield": _avg("fcf_yield"),
        "dividend_yield": _avg("dividend_yield"),
        "profit_margin": _avg("profit_margin"),
        "revenue_growth": _avg("revenue_growth"),
    }

    # Print table
    print(f"\n{'═' * 80}")
    print(f"  PEER COMPARISON — {target_data.get('sector', 'N/A')} sector")
    print(f"{'═' * 80}")

    hdr = (f"  {'Symbol':<8}{'Name':<26}{'MCap$B':>7}{'ROE%':>7}{'P/E':>7}"
           f"{'D/E':>7}{'CR':>6}{'FYld%':>7}{'DY%':>6}{'Margin':>7}{'RevG%':>7}")
    print(hdr)
    print(f"  {'─' * 98}")

    def _val(v, fmt=".1f"):
        if v is None:
            return "-"
        return f"{v:{fmt}}"

    def _color_val(v, fmt=".1f", high=None, mid=None, invert=False):
        if v is None:
            return dim("-") if USE_COLOR else "-"
        s = f"{v:{fmt}}"
        if not USE_COLOR or high is None:
            return s
        if invert:
            if v <= high:
                return good(s)
            if mid and v <= mid:
                return warn(s)
            return bad(s)
        else:
            if v >= high:
                return good(s)
            if mid is not None and v >= mid:
                return warn(s)
            return bad(s)

    def _pad(colored_str, width):
        import re
        visible = re.sub(r'\033\[[0-9;]*m', '', colored_str)
        pad_needed = width - len(visible)
        return " " * max(0, pad_needed) + colored_str

    for i, s in enumerate(all_stocks):
        marker = " ◀" if i == 0 else ""
        sym = s["symbol"]
        name = s["name"][:24]

        if USE_COLOR:
            row = (f"  {BOLD}{sym:<8}{RESET}" if i == 0 else f"  {sym:<8}")
            row += f"{name:<26}"
            row += _pad(_val(s.get("market_cap_b")), 7)
            row += _pad(_color_val(s.get("roe_pct"), high=15, mid=10), 7)
            row += _pad(_color_val(s.get("trailing_pe"), ".1f", high=15, mid=25, invert=True), 7)
            row += _pad(_color_val(s.get("debt_to_equity"), ".0f", high=100, mid=150, invert=True), 7)
            row += _pad(_color_val(s.get("current_ratio"), ".2f", high=1.5, mid=1.0), 6)
            row += _pad(_color_val(s.get("fcf_yield"), high=3, mid=1), 7)
            row += _pad(_color_val(s.get("dividend_yield"), ".2f", high=2, mid=0.5), 6)
            row += _pad(_color_val(s.get("profit_margin"), high=15, mid=5), 7)
            row += _pad(_color_val(s.get("revenue_growth"), high=10, mid=0), 7)
        else:
            row = (f"  {sym:<8}{name:<26}"
                   f"{_val(s.get('market_cap_b')):>7}"
                   f"{_val(s.get('roe_pct')):>7}"
                   f"{_val(s.get('trailing_pe')):>7}"
                   f"{_val(s.get('debt_to_equity'), '.0f'):>7}"
                   f"{_val(s.get('current_ratio'), '.2f'):>6}"
                   f"{_val(s.get('fcf_yield')):>7}"
                   f"{_val(s.get('dividend_yield'), '.2f'):>6}"
                   f"{_val(s.get('profit_margin')):>7}"
                   f"{_val(s.get('revenue_growth')):>7}")
        print(row + marker)

    # Averages row
    print(f"  {'─' * 98}")
    avg_row = (f"  {'AVG':<8}{'(Peer Average)':<26}"
               f"{'':>7}"
               f"{_val(avg.get('roe_pct')):>7}"
               f"{_val(avg.get('trailing_pe')):>7}"
               f"{_val(avg.get('debt_to_equity'), '.0f'):>7}"
               f"{_val(avg.get('current_ratio'), '.2f'):>6}"
               f"{_val(avg.get('fcf_yield')):>7}"
               f"{_val(avg.get('dividend_yield'), '.2f'):>6}"
               f"{_val(avg.get('profit_margin')):>7}"
               f"{_val(avg.get('revenue_growth')):>7}")
    print(avg_row)

    # Context notes
    print()
    target_roe = target_entry.get("roe_pct")
    if target_roe and avg["roe_pct"]:
        diff = target_roe - avg["roe_pct"]
        if diff > 5:
            print(f"  ✅ ROE ({target_roe}%) is {diff:.0f}pp above peer average ({avg['roe_pct']}%)")
        elif diff < -5:
            print(f"  ⚠️  ROE ({target_roe}%) is {abs(diff):.0f}pp below peer average ({avg['roe_pct']}%)")
        else:
            print(f"  ℹ️  ROE ({target_roe}%) is in line with peer average ({avg['roe_pct']}%)")

    target_pe = target_entry.get("trailing_pe")
    if target_pe and avg["trailing_pe"]:
        if target_pe < avg["trailing_pe"] * 0.8:
            print(f"  ✅ P/E ({target_pe}) is cheaper than peers ({avg['trailing_pe']})")
        elif target_pe > avg["trailing_pe"] * 1.2:
            print(f"  ⚠️  P/E ({target_pe}) is more expensive than peers ({avg['trailing_pe']})")
        else:
            print(f"  ℹ️  P/E ({target_pe}) is similar to peers ({avg['trailing_pe']})")

    target_margin = target_entry.get("profit_margin")
    if target_margin and avg["profit_margin"]:
        if target_margin > avg["profit_margin"] * 1.2:
            print(f"  ✅ Profit margin ({target_margin}%) exceeds peer average ({avg['profit_margin']}%)")
        elif target_margin < avg["profit_margin"] * 0.8:
            print(f"  ⚠️  Profit margin ({target_margin}%) trails peer average ({avg['profit_margin']}%)")

    print()
