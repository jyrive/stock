"""yfinance market-data provider.

Maps yfinance API responses to the canonical schema defined in
``datasources.schema``.  Other modules should not import yfinance
directly — all yfinance access is isolated here.
"""

import yfinance as yf
import pandas as pd
from typing import Optional, Dict, List


# ═══════════════════════════════════════════════════════════════════════
#  yfinance key → schema field name mapping
# ═══════════════════════════════════════════════════════════════════════
#
#  Used by get_fundamentals() and save_fundamental_snapshot() when
#  converting provider-specific keys to the canonical names defined
#  in datasources.schema.SNAPSHOT_FIELDS.

FIELD_MAP = {
    # yfinance info key       → our schema field name
    "marketCap":               "market_cap",
    "currentPrice":            "current_price",
    "regularMarketPrice":      "current_price",   # fallback key
    "trailingPE":              "trailing_pe",
    "forwardPE":               "forward_pe",
    "priceToBook":             "price_to_book",
    "priceToSalesTrailing12Months": "price_to_sales",
    "returnOnEquity":          "roe_pct",
    "debtToEquity":            "debt_to_equity",
    "currentRatio":            "current_ratio",
    "profitMargins":           "profit_margin",
    "revenueGrowth":           "revenue_growth",
    "earningsGrowth":          "earnings_growth",
    "dividendYield":           "dividend_yield",
    "payoutRatio":             "payout_ratio",
    "beta":                    "beta",
    "freeCashflow":            "free_cashflow",
    "sharesOutstanding":       "shares_outstanding",
    "dividendRate":            "dividend_rate",
}

# Fields that yfinance returns as 0-1 ratios needing ×100 for percentage
_PCT_FIELDS = {
    "returnOnEquity", "profitMargins", "revenueGrowth",
    "earningsGrowth", "dividendYield", "payoutRatio",
}


# ═══════════════════════════════════════════════════════════════════════
#  Low-level ticker access
# ═══════════════════════════════════════════════════════════════════════

def _ticker(symbol: str):
    """Create a yfinance Ticker object.  Internal helper."""
    return yf.Ticker(symbol)


# ═══════════════════════════════════════════════════════════════════════
#  Fundamentals
# ═══════════════════════════════════════════════════════════════════════

def get_info(symbol: str) -> Optional[dict]:
    """Fetch the raw yfinance ``info`` dict for a ticker.

    Returns None if the ticker is invalid or data unavailable.
    """
    try:
        info = _ticker(symbol).info
        if info and info.get("marketCap"):
            return info
        return None
    except Exception:
        return None


def get_fundamentals(symbol: str) -> Optional[dict]:
    """Fetch comprehensive fundamental data for a company.

    Returns the canonical ``data`` dict consumed by all scorers, or None.
    Keys: symbol, name, sector, industry, info, income_stmt, balance_sheet,
          cash_flow, market_cap, current_price, trailing_pe, forward_pe.
    """
    try:
        ticker = _ticker(symbol)
        info = ticker.info

        if not info or "marketCap" not in info:
            return None

        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "current_price": info.get(
                "currentPrice", info.get("regularMarketPrice", 0)
            ),
            "trailing_pe": info.get("trailingPE", None),
            "forward_pe": info.get("forwardPE", None),
            "info": info,
            "income_stmt": ticker.income_stmt,
            "balance_sheet": ticker.balance_sheet,
            "cash_flow": ticker.cash_flow,
        }
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return None


def get_quarterly_financials(symbol: str):
    """Return the yfinance Ticker object for accessing quarterly statements.

    The caller can use .quarterly_income_stmt, .quarterly_balance_sheet,
    .quarterly_cashflow on the returned object.

    Returns None on error.
    """
    try:
        return _ticker(symbol)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
#  Price history
# ═══════════════════════════════════════════════════════════════════════

def get_price_history(
    symbol: str,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV price history for a ticker.

    Specify either 'period' (e.g. "1y", "2y", "5y") or start/end dates.
    Returns a pandas DataFrame with columns Open, High, Low, Close, Volume,
    Dividends, or None on failure.
    """
    try:
        t = _ticker(symbol)
        kwargs = {}
        if period:
            kwargs["period"] = period
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end

        # Default to 1y if nothing specified
        if not kwargs:
            kwargs["period"] = "1y"

        hist = t.history(**kwargs)
        if hist is None or hist.empty:
            return None
        return hist
    except Exception:
        return None


def get_current_price(symbol: str) -> Optional[float]:
    """Fetch the latest price for a single ticker.

    Returns None on failure.
    """
    try:
        info = _ticker(symbol).info
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        return None


def get_current_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices for multiple tickers.

    Returns {symbol: price} — missing tickers are omitted.
    """
    prices = {}
    for sym in symbols:
        p = get_current_price(sym)
        if p is not None:
            prices[sym] = p
    return prices


# ═══════════════════════════════════════════════════════════════════════
#  Macro indicators
# ═══════════════════════════════════════════════════════════════════════

def get_macro_history(
    symbol: str,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """Fetch price history for a macro indicator (VIX, yields, indices, etc.).

    Same as get_price_history but semantically distinct — macro indicators
    are not stocks. Uses the same yfinance backend.
    """
    return get_price_history(symbol, period=period, start=start, end=end)


# ═══════════════════════════════════════════════════════════════════════
#  Dividends
# ═══════════════════════════════════════════════════════════════════════

def get_dividends(symbol: str) -> Optional[pd.Series]:
    """Fetch dividend history for a ticker.

    Returns a pandas Series indexed by date, or None.
    """
    try:
        divs = _ticker(symbol).dividends
        if divs is None or divs.empty:
            return None
        return divs
    except Exception:
        return None
