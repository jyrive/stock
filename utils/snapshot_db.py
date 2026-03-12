"""Persistent data store — point-in-time fundamentals, price & macro cache.

Solves the look-ahead bias problem by snapshotting fundamental data each time
we score a stock, and caching price/macro data locally so we can reconstruct
any historical state.

Tables:
    fundamental_snapshots   One row per (symbol, snapshot_date) — full info dict
    quarterly_financials    One row per (symbol, snapshot_date, period_end) — line items
    price_cache             Daily OHLCV per symbol — append-only
    macro_cache             Daily close per indicator — append-only

All timestamps are ISO-8601 date strings.
"""

import json
import os
import sqlite3
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from utils.db import DB_PATH, get_connection, ensure_schema


# ═══════════════════════════════════════════════════════════════════════
#  Connection & schema
# ═══════════════════════════════════════════════════════════════════════

def _connect(db_path=None):
    """Open the database and ensure all tables exist."""
    conn = get_connection(db_path)
    ensure_schema(conn, db_path)
    return conn


# ═══════════════════════════════════════════════════════════════════════
#  Fundamental snapshots
# ═══════════════════════════════════════════════════════════════════════

def save_fundamental_snapshot(symbol, info_dict, snapshot_date=None, db_path=None):
    """Save a point-in-time fundamental snapshot for a ticker.

    Call this every time we fetch ticker.info so we build history.
    """
    conn = _connect(db_path)
    snap_date = snapshot_date or date.today().isoformat()
    info = info_dict or {}

    # Extract queryable metrics
    mc = info.get("marketCap")
    fcf = info.get("freeCashflow")
    fcf_yield = (fcf / mc * 100) if fcf and mc and mc > 0 else None

    row = (
        symbol.upper(),
        snap_date,
        mc / 1e9 if mc else None,                          # market_cap (billions)
        info.get("trailingPE"),
        info.get("forwardPE"),
        info.get("priceToBook"),
        info.get("priceToSalesTrailing12Months"),
        _pct(info.get("returnOnEquity")),
        info.get("debtToEquity"),
        info.get("currentRatio"),
        _pct(info.get("profitMargins")),
        _pct(info.get("revenueGrowth")),
        _pct(info.get("earningsGrowth")),
        fcf_yield,
        _pct(info.get("dividendYield")),
        _pct(info.get("payoutRatio")),
        info.get("beta"),
        info.get("currentPrice", info.get("regularMarketPrice")),
        _safe_json(info),
    )

    conn.execute("""
        INSERT OR REPLACE INTO fundamental_snapshots (
            symbol, snapshot_date,
            market_cap, trailing_pe, forward_pe, price_to_book, price_to_sales,
            roe_pct, debt_to_equity, current_ratio, profit_margin,
            revenue_growth, earnings_growth, fcf_yield, dividend_yield,
            payout_ratio, beta, current_price, info_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, row)
    conn.commit()
    conn.close()


def get_fundamental_history(symbol, db_path=None):
    """Get all fundamental snapshots for a ticker, oldest first."""
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT * FROM fundamental_snapshots
        WHERE symbol = ?
        ORDER BY snapshot_date ASC
    """, (symbol.upper(),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_snapshot_coverage(db_path=None):
    """Return dict of symbol → [list of snapshot dates]."""
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT symbol, snapshot_date FROM fundamental_snapshots
        ORDER BY symbol, snapshot_date
    """).fetchall()
    conn.close()

    coverage = {}
    for r in rows:
        coverage.setdefault(r["symbol"], []).append(r["snapshot_date"])
    return coverage


# ═══════════════════════════════════════════════════════════════════════
#  Quarterly financials
# ═══════════════════════════════════════════════════════════════════════

def save_quarterly_financials(symbol, ticker_obj, snapshot_date=None, db_path=None):
    """Save quarterly income statement, balance sheet, and cash flow.

    ticker_obj: yfinance Ticker object (we read .quarterly_income_stmt etc.)
    """
    conn = _connect(db_path)
    snap_date = snapshot_date or date.today().isoformat()
    sym = symbol.upper()
    saved = 0

    for stmt_type, attr in [
        ("income", "quarterly_income_stmt"),
        ("balance", "quarterly_balance_sheet"),
        ("cashflow", "quarterly_cashflow"),
    ]:
        try:
            df = getattr(ticker_obj, attr, None)
            if df is None or df.empty:
                continue

            for col in df.columns:
                period_end = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                data = {}
                for idx_label in df.index:
                    val = df.loc[idx_label, col]
                    if pd.notna(val):
                        data[str(idx_label)] = float(val)

                if data:
                    conn.execute("""
                        INSERT OR REPLACE INTO quarterly_financials
                        (symbol, snapshot_date, period_end, statement_type, data_json)
                        VALUES (?, ?, ?, ?, ?)
                    """, (sym, snap_date, period_end, stmt_type, json.dumps(data)))
                    saved += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return saved


# ═══════════════════════════════════════════════════════════════════════
#  Price cache
# ═══════════════════════════════════════════════════════════════════════

def save_prices(symbol, price_df, db_path=None):
    """Save daily OHLCV from a yfinance history DataFrame. Append-only."""
    conn = _connect(db_path)
    sym = symbol.upper()
    saved = 0

    for dt, row in price_df.iterrows():
        trade_date = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
        try:
            conn.execute("""
                INSERT OR IGNORE INTO price_cache
                (symbol, trade_date, open, high, low, close, volume, dividends)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sym, trade_date,
                float(row.get("Open", 0)),
                float(row.get("High", 0)),
                float(row.get("Low", 0)),
                float(row.get("Close", 0)),
                float(row.get("Volume", 0)),
                float(row.get("Dividends", 0)),
            ))
            saved += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return saved


def get_price_range(symbol, db_path=None):
    """Return (first_date, last_date, count) for cached prices."""
    conn = _connect(db_path)
    row = conn.execute("""
        SELECT MIN(trade_date) as first_date,
               MAX(trade_date) as last_date,
               COUNT(*) as cnt
        FROM price_cache WHERE symbol = ?
    """, (symbol.upper(),)).fetchone()
    conn.close()
    if row and row["cnt"] > 0:
        return row["first_date"], row["last_date"], row["cnt"]
    return None, None, 0


# ═══════════════════════════════════════════════════════════════════════
#  Macro cache
# ═══════════════════════════════════════════════════════════════════════

def save_macro(indicator, price_df, db_path=None):
    """Save daily macro indicator closes from yfinance DataFrame."""
    conn = _connect(db_path)
    saved = 0

    for dt, row in price_df.iterrows():
        trade_date = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
        close_val = float(row.get("Close", row.get("close", 0)))
        if close_val and not np.isnan(close_val):
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO macro_cache
                    (indicator, trade_date, close)
                    VALUES (?, ?, ?)
                """, (indicator, trade_date, close_val))
                saved += 1
            except Exception:
                pass

    conn.commit()
    conn.close()
    return saved


def get_macro(indicator, start_date=None, end_date=None, db_path=None):
    """Get cached macro data. Returns numpy array of closes or None."""
    conn = _connect(db_path)
    query = "SELECT trade_date, close FROM macro_cache WHERE indicator = ?"
    params = [indicator]
    if start_date:
        query += " AND trade_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND trade_date <= ?"
        params.append(end_date)
    query += " ORDER BY trade_date ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return None, None
    dates = [r["trade_date"] for r in rows]
    closes = np.array([r["close"] for r in rows], dtype=float)
    return dates, closes


def get_macro_range(indicator, db_path=None):
    """Return (first_date, last_date, count) for a cached macro indicator."""
    conn = _connect(db_path)
    row = conn.execute("""
        SELECT MIN(trade_date) as first_date,
               MAX(trade_date) as last_date,
               COUNT(*) as cnt
        FROM macro_cache WHERE indicator = ?
    """, (indicator,)).fetchone()
    conn.close()
    if row and row["cnt"] > 0:
        return row["first_date"], row["last_date"], row["cnt"]
    return None, None, 0


# ═══════════════════════════════════════════════════════════════════════
#  Statistics / coverage report
# ═══════════════════════════════════════════════════════════════════════

def get_datastore_stats(db_path=None):
    """Return summary statistics of all stored data."""
    conn = _connect(db_path)

    stats = {}

    # Fundamental snapshots
    row = conn.execute("""
        SELECT COUNT(DISTINCT symbol) as tickers,
               COUNT(*) as snapshots,
               MIN(snapshot_date) as first_date,
               MAX(snapshot_date) as last_date
        FROM fundamental_snapshots
    """).fetchone()
    stats["fundamentals"] = dict(row) if row else {}

    # Quarterly financials
    row = conn.execute("""
        SELECT COUNT(DISTINCT symbol) as tickers,
               COUNT(*) as records,
               MIN(period_end) as earliest_period,
               MAX(period_end) as latest_period
        FROM quarterly_financials
    """).fetchone()
    stats["quarterly"] = dict(row) if row else {}

    # Price cache
    row = conn.execute("""
        SELECT COUNT(DISTINCT symbol) as tickers,
               COUNT(*) as records,
               MIN(trade_date) as first_date,
               MAX(trade_date) as last_date
        FROM price_cache
    """).fetchone()
    stats["prices"] = dict(row) if row else {}

    # Macro cache
    row = conn.execute("""
        SELECT COUNT(DISTINCT indicator) as indicators,
               COUNT(*) as records,
               MIN(trade_date) as first_date,
               MAX(trade_date) as last_date
        FROM macro_cache
    """).fetchone()
    stats["macro"] = dict(row) if row else {}

    conn.close()
    return stats


# ═══════════════════════════════════════════════════════════════════════
#  Cache read-back — reconstruct scorer data dicts from DB
# ═══════════════════════════════════════════════════════════════════════

def load_fundamentals(symbol, db_path=None):
    """Reconstruct the canonical scorer data dict from the DB cache.

    Reads the latest fundamental snapshot and rebuilds the ``data`` dict
    shape that scorers expect (same as ``providers.yfinance.get_fundamentals``
    returns).

    Returns the data dict or None if no snapshot exists.
    """
    conn = _connect(db_path)
    sym = symbol.upper()

    # Latest snapshot
    snap = conn.execute("""
        SELECT * FROM fundamental_snapshots
        WHERE symbol = ?
        ORDER BY snapshot_date DESC LIMIT 1
    """, (sym,)).fetchone()

    if not snap:
        conn.close()
        return None

    snap = dict(snap)

    # Reconstruct the info dict from the JSON blob
    info = {}
    if snap.get("info_json"):
        try:
            info = json.loads(snap["info_json"])
        except Exception:
            pass

    # Reconstruct annual financial statements from quarterly_financials
    income_stmt = _rebuild_annual_statement(conn, sym, "income")
    balance_sheet = _rebuild_annual_statement(conn, sym, "balance")
    cash_flow = _rebuild_annual_statement(conn, sym, "cashflow")

    conn.close()

    return {
        "symbol": sym,
        "name": info.get("longName", info.get("shortName", sym)),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": (snap["market_cap"] or 0) * 1e9,  # stored as billions
        "current_price": snap.get("current_price", 0),
        "trailing_pe": snap.get("trailing_pe"),
        "forward_pe": snap.get("forward_pe"),
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
    }


def _rebuild_annual_statement(conn, symbol, stmt_type):
    """Rebuild a financial statement DataFrame from quarterly_financials.

    Returns a pandas DataFrame with line-item rows and date columns,
    matching the shape returned by yfinance's ``ticker.income_stmt`` etc.
    Returns an empty DataFrame if no data found.
    """
    rows = conn.execute("""
        SELECT period_end, data_json FROM quarterly_financials
        WHERE symbol = ? AND statement_type = ?
        ORDER BY period_end DESC
    """, (symbol, stmt_type)).fetchall()

    if not rows:
        return pd.DataFrame()

    # Build {period_end: {line_item: value}} and pivot
    all_items = set()
    periods = {}
    for r in rows:
        pe = r["period_end"]
        try:
            data = json.loads(r["data_json"])
        except Exception:
            continue
        periods[pe] = data
        all_items.update(data.keys())

    if not periods:
        return pd.DataFrame()

    # Create DataFrame: rows = line items, columns = period dates
    sorted_periods = sorted(periods.keys(), reverse=True)
    df_data = {}
    for pe in sorted_periods:
        col = pd.Timestamp(pe)
        df_data[col] = {item: periods[pe].get(item, np.nan) for item in all_items}

    df = pd.DataFrame(df_data)
    return df


def get_data_age(symbol, category, db_path=None):
    """Check freshness of a specific data category for a symbol.

    Categories: "snapshot", "statements", "prices", "dividends", "metadata"
    Each has its own threshold defined in schema.REFRESH_POLICY.

    Returns (stale: bool, last_updated: datetime | None).
    """
    from datasources.schema import REFRESH_POLICY

    policy = REFRESH_POLICY.get(category)
    if not policy:
        return True, None

    max_age_hours = policy["max_age_hours"]

    conn = _connect(db_path)
    sym = symbol.upper()

    if category == "statements":
        row = conn.execute("""
            SELECT MAX(snapshot_date) as last_ts
            FROM quarterly_financials WHERE symbol = ?
        """, (sym,)).fetchone()
    elif category == "prices":
        row = conn.execute("""
            SELECT MAX(trade_date) as last_ts
            FROM price_cache WHERE symbol = ?
        """, (sym,)).fetchone()
    else:
        # snapshot / metadata / dividends — all keyed off fundamental_snapshots
        row = conn.execute("""
            SELECT MAX(snapshot_date) as last_ts
            FROM fundamental_snapshots WHERE symbol = ?
        """, (sym,)).fetchone()

    conn.close()

    if not row or not row["last_ts"]:
        return True, None

    try:
        last = datetime.strptime(row["last_ts"], "%Y-%m-%d")
    except Exception:
        return True, None

    age = datetime.now() - last
    stale = age > timedelta(hours=max_age_hours)
    return stale, last


def get_snapshot_age(symbol, max_age_hours=None, db_path=None):
    """Check how old the latest snapshot is.

    Returns (stale: bool, last_updated: datetime | None).
    Kept for backward compatibility — delegates to get_data_age.
    """
    if max_age_hours is not None:
        # Caller passed explicit threshold — use old-style check
        from datasources.schema import MAX_SNAPSHOT_AGE_HOURS
        conn = _connect(db_path)
        row = conn.execute("""
            SELECT snapshot_date FROM fundamental_snapshots
            WHERE symbol = ?
            ORDER BY snapshot_date DESC LIMIT 1
        """, (symbol.upper(),)).fetchone()
        conn.close()

        if not row:
            return True, None
        try:
            snap_dt = datetime.strptime(row["snapshot_date"], "%Y-%m-%d")
        except Exception:
            return True, None
        age = datetime.now() - snap_dt
        stale = age > timedelta(hours=max_age_hours)
        return stale, snap_dt

    return get_data_age(symbol, "snapshot", db_path=db_path)


def get_cached_info(symbol, db_path=None):
    """Return the latest cached info dict (from info_json) or None."""
    conn = _connect(db_path)
    row = conn.execute("""
        SELECT info_json FROM fundamental_snapshots
        WHERE symbol = ?
        ORDER BY snapshot_date DESC LIMIT 1
    """, (symbol.upper(),)).fetchone()
    conn.close()

    if not row or not row["info_json"]:
        return None
    try:
        return json.loads(row["info_json"])
    except Exception:
        return None


def get_cached_prices(symbol, start_date=None, end_date=None, db_path=None):
    """Load price history from DB cache as a pandas DataFrame.

    Returns DataFrame with Open/High/Low/Close/Volume/Dividends columns
    indexed by date, or None if no data.
    """
    conn = _connect(db_path)
    query = """
        SELECT trade_date, open, high, low, close, volume, dividends
        FROM price_cache WHERE symbol = ?
    """
    params = [symbol.upper()]
    if start_date:
        query += " AND trade_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND trade_date <= ?"
        params.append(end_date)
    query += " ORDER BY trade_date ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return None

    data = [dict(r) for r in rows]
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df["trade_date"])
    df = df.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume", "dividends": "Dividends",
    })
    df = df.drop(columns=["trade_date"])
    return df


def get_latest_cached_price(symbol, db_path=None):
    """Return the most recent closing price from the cache, or None."""
    conn = _connect(db_path)
    row = conn.execute("""
        SELECT close FROM price_cache
        WHERE symbol = ?
        ORDER BY trade_date DESC LIMIT 1
    """, (symbol.upper(),)).fetchone()
    conn.close()
    return row["close"] if row else None


def get_cached_dividends(symbol, db_path=None):
    """Return cached dividends as a pandas Series indexed by date, or None."""
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT trade_date, dividends FROM price_cache
        WHERE symbol = ? AND dividends > 0
        ORDER BY trade_date ASC
    """, (symbol.upper(),)).fetchall()
    conn.close()

    if not rows:
        return None

    dates = pd.to_datetime([r["trade_date"] for r in rows])
    vals = [r["dividends"] for r in rows]
    return pd.Series(vals, index=dates)


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _pct(val):
    """Convert a 0-1 ratio to percentage, or return None."""
    if val is None:
        return None
    return float(val) * 100


def _safe_json(obj):
    """Serialize an object to JSON, handling non-serializable types."""
    def _default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return str(o)
    try:
        return json.dumps(obj, default=_default)
    except Exception:
        return "{}"
