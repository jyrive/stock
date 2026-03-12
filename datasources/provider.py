"""Data provider dispatch — resolves where to get market data from.

Modes:
    "auto"   — use DB cache if fresh, else fetch live (default)
    "live"   — always fetch from remote provider, also updates cache
    "cache"  — DB only, no network; returns None if missing

Usage:
    from datasources.provider import get_fundamentals

    data = get_fundamentals("AAPL")                  # auto (default)
    data = get_fundamentals("AAPL", mode="live")     # force fresh
    data = get_fundamentals("AAPL", mode="cache")    # offline
"""

from datasources.schema import REFRESH_POLICY, max_age


# ═══════════════════════════════════════════════════════════════════════
#  Module-level config — override via configure()
# ═══════════════════════════════════════════════════════════════════════

_default_mode = "auto"


def configure(mode=None):
    """Set provider defaults (called once at startup from CLI flags)."""
    global _default_mode
    if mode:
        _default_mode = mode


# ═══════════════════════════════════════════════════════════════════════
#  Fundamentals
# ═══════════════════════════════════════════════════════════════════════

def get_fundamentals(symbol, mode=None):
    """Get the canonical data dict for fundamental scoring.

    In auto mode, checks each data category independently:
      - snapshot (valuation metrics)  — refreshes daily
      - statements (quarterly fins)   — refreshes every ~90 days

    This avoids re-fetching expensive quarterly statements on every run
    while keeping valuations current.

    Returns the scorer data dict or None.
    """
    effective_mode = mode or _default_mode

    if effective_mode == "cache":
        return _load_cached(symbol)

    if effective_mode == "live":
        return _fetch_and_cache(symbol, refresh_statements=True)

    # auto — check each data category independently
    from utils.snapshot_db import get_data_age

    snap_stale, _ = get_data_age(symbol, "snapshot")
    stmts_stale, _ = get_data_age(symbol, "statements")

    if not snap_stale and not stmts_stale:
        data = _load_cached(symbol)
        if data is not None:
            return data

    # Something is stale or missing — fetch with selective refresh
    return _fetch_and_cache(symbol, refresh_statements=stmts_stale)


# ═══════════════════════════════════════════════════════════════════════
#  Price history
# ═══════════════════════════════════════════════════════════════════════

def get_price_history(symbol, period=None, start=None, end=None, mode=None):
    """Price history with cache/live/auto logic.

    In 'cache' mode, reads from price_cache table.
    In 'live' mode, fetches from remote and updates cache.
    In 'auto' mode, uses cache if fresh (< 18h), else fetches live.
    """
    effective_mode = mode or _default_mode

    if effective_mode == "cache":
        return _load_cached_prices(symbol, start=start, end=end)

    if effective_mode == "auto":
        from utils.snapshot_db import get_data_age
        stale, _ = get_data_age(symbol, "prices")
        if not stale:
            cached = _load_cached_prices(symbol, start=start, end=end)
            if cached is not None and not cached.empty:
                return cached

    # live or auto-stale — fetch from remote
    from datasources.providers.yfinance import get_price_history as _remote_prices
    hist = _remote_prices(symbol, period=period, start=start, end=end)
    if hist is not None:
        _cache_prices(symbol, hist)
    return hist


def get_current_price(symbol, mode=None):
    """Latest price for a single ticker."""
    effective_mode = mode or _default_mode

    if effective_mode == "cache":
        from utils.snapshot_db import get_latest_cached_price
        return get_latest_cached_price(symbol)

    from datasources.providers.yfinance import get_current_price as _remote
    return _remote(symbol)


def get_current_prices(symbols, mode=None):
    """Current prices for multiple tickers."""
    prices = {}
    for sym in symbols:
        p = get_current_price(sym, mode=mode)
        if p is not None:
            prices[sym] = p
    return prices


# ═══════════════════════════════════════════════════════════════════════
#  Macro indicators
# ═══════════════════════════════════════════════════════════════════════

def get_macro_history(symbol, period=None, start=None, end=None, mode=None):
    """Macro indicator history with cache/live/auto logic."""
    effective_mode = mode or _default_mode

    if effective_mode == "cache":
        from utils.snapshot_db import get_macro
        dates, closes = get_macro(symbol, start_date=start, end_date=end)
        if closes is not None and len(closes) > 0:
            import pandas as pd
            import numpy as np
            idx = pd.to_datetime(dates)
            return pd.DataFrame({"Close": closes}, index=idx)
        return None

    from datasources.providers.yfinance import get_macro_history as _remote
    hist = _remote(symbol, period=period, start=start, end=end)
    if hist is not None:
        _cache_macro(symbol, hist)
    return hist


# ═══════════════════════════════════════════════════════════════════════
#  Dividends
# ═══════════════════════════════════════════════════════════════════════

def get_dividends(symbol, mode=None):
    """Dividend history for a ticker.

    Dividends update infrequently (~quarterly). In auto mode, uses
    cached data if within the 30-day threshold.
    """
    effective_mode = mode or _default_mode

    if effective_mode == "cache":
        return _load_cached_dividends(symbol)

    if effective_mode == "auto":
        from utils.snapshot_db import get_data_age
        stale, _ = get_data_age(symbol, "dividends")
        if not stale:
            cached = _load_cached_dividends(symbol)
            if cached is not None and len(cached) > 0:
                return cached

    from datasources.providers.yfinance import get_dividends as _remote
    return _remote(symbol)


# ═══════════════════════════════════════════════════════════════════════
#  Raw info (for non-scoring uses like peers, study)
# ═══════════════════════════════════════════════════════════════════════

def get_info(symbol, mode=None):
    """Get info dict — live or from cached snapshot's info_json."""
    effective_mode = mode or _default_mode

    if effective_mode == "cache":
        from utils.snapshot_db import get_cached_info
        return get_cached_info(symbol)

    from datasources.providers.yfinance import get_info as _remote
    return _remote(symbol)


def get_quarterly_financials(symbol, mode=None):
    """Get quarterly financials ticker object (live only — no cache path)."""
    from datasources.providers.yfinance import get_quarterly_financials as _remote
    return _remote(symbol)


# ═══════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════

def _load_cached(symbol):
    """Reconstruct scorer data dict from DB cache."""
    from utils.snapshot_db import load_fundamentals
    return load_fundamentals(symbol)


def _fetch_and_cache(symbol, refresh_statements=True):
    """Fetch live from remote provider and persist to cache.

    Args:
        refresh_statements: If False, skip the expensive quarterly
            financials fetch and graft cached statements onto the
            fresh snapshot instead.  Saves ~3 API calls when
            statements haven't changed (they update quarterly).
    """
    from datasources.providers.yfinance import get_fundamentals as _remote_fund

    data = _remote_fund(symbol)
    if data is None:
        return None

    # Always save the snapshot (one cheap row of valuation metrics)
    try:
        from utils.snapshot_db import save_fundamental_snapshot
        save_fundamental_snapshot(symbol, data["info"])
    except Exception:
        pass

    # Statements — only re-fetch when stale (expensive: 3 API calls)
    if refresh_statements:
        try:
            from datasources.providers.yfinance import (
                get_quarterly_financials as _remote_qtr,
            )
            from utils.snapshot_db import save_quarterly_financials
            ticker_obj = _remote_qtr(symbol)
            if ticker_obj:
                save_quarterly_financials(symbol, ticker_obj)
        except Exception:
            pass
    else:
        # Graft cached statements onto the fresh snapshot
        data = _merge_cached_statements(symbol, data)

    return data


def _cache_prices(symbol, price_df):
    """Persist price history to DB cache."""
    try:
        from utils.snapshot_db import save_prices
        save_prices(symbol, price_df)
    except Exception:
        pass


def _cache_macro(symbol, price_df):
    """Persist macro history to DB cache."""
    try:
        from utils.snapshot_db import save_macro
        save_macro(symbol, price_df)
    except Exception:
        pass


def _load_cached_prices(symbol, start=None, end=None):
    """Load price history from DB cache as DataFrame."""
    try:
        from utils.snapshot_db import get_cached_prices
        return get_cached_prices(symbol, start_date=start, end_date=end)
    except Exception:
        return None


def _load_cached_dividends(symbol):
    """Load dividends from price_cache table."""
    try:
        from utils.snapshot_db import get_cached_dividends
        return get_cached_dividends(symbol)
    except Exception:
        return None


def _merge_cached_statements(symbol, data):
    """Graft cached financial statements onto a fresh data dict.

    Used when the snapshot (valuation metrics) was refreshed but
    statements are still within their 90-day freshness window.
    """
    try:
        from utils.snapshot_db import load_fundamentals
        cached = load_fundamentals(symbol)
        if cached:
            for key in ("income_stmt", "balance_sheet", "cash_flow"):
                if key in cached and cached[key] is not None:
                    data[key] = cached[key]
    except Exception:
        pass
    return data
