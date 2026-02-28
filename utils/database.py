"""SQLite database for storing screening scores over time.

Stores one row per (ticker, date). Re-running on the same day overwrites
the previous result for that ticker.
"""

import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scores.db"
)


def _connect(db_path=None):
    """Open (and initialise) the database."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            symbol        TEXT    NOT NULL,
            scan_date     TEXT    NOT NULL,
            name          TEXT,
            sector        TEXT,
            industry      TEXT,
            market_cap_b  REAL,
            current_price REAL,
            trailing_pe   REAL,
            eps_score     INTEGER,
            eps_cagr      REAL,
            eps_consistent INTEGER,
            roe_score     INTEGER,
            roe_pct       REAL,
            debt_to_equity REAL,
            fcf_score     INTEGER,
            fcf_current_b REAL,
            fcf_yield     REAL,
            fcf_growing   INTEGER,
            balance_score INTEGER,
            current_ratio REAL,
            cash_to_debt  REAL,
            retained_earnings_growing INTEGER,
            goodwill_pct  REAL,
            dividend_score INTEGER,
            dividend_yield_pct REAL,
            payout_ratio_pct REAL,
            consecutive_div_increases INTEGER,
            intrinsic_value REAL,
            margin_of_safety REAL,
            undervalued   INTEGER,
            revenue_cagr  REAL,
            revenue_growing INTEGER,
            buffett_score REAL,
            PRIMARY KEY (symbol, scan_date)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_scores_date
        ON scores (scan_date)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_scores_symbol
        ON scores (symbol)
    """)

    # Migrate: add balance sheet columns if missing (for existing DBs)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(scores)").fetchall()}
    for col, ctype in [
        ("balance_score", "INTEGER"),
        ("current_ratio", "REAL"),
        ("cash_to_debt", "REAL"),
        ("retained_earnings_growing", "INTEGER"),
        ("goodwill_pct", "REAL"),
        ("dividend_score", "INTEGER"),
        ("dividend_yield_pct", "REAL"),
        ("payout_ratio_pct", "REAL"),
        ("consecutive_div_increases", "INTEGER"),
        ("revenue_cagr", "REAL"),
        ("revenue_growing", "INTEGER"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE scores ADD COLUMN {col} {ctype}")

    conn.commit()
    return conn


def save_scores(results, db_path=None):
    """Save a list of screener results to the database.

    Uses today's date. If a ticker already has a row for today, it gets
    overwritten (INSERT OR REPLACE on the primary key).
    """
    conn = _connect(db_path)
    today = date.today().isoformat()

    rows = []
    for r in results:
        eps = r.get("eps_analysis", {})
        roe = r.get("roe_analysis", {})
        fcf = r.get("fcf_analysis", {})
        bal = r.get("balance_analysis", {})
        div = r.get("dividend_analysis", {})
        dcf = r.get("dcf_analysis", {})
        rev = r.get("revenue_analysis", {})

        rows.append((
            r["symbol"],
            today,
            r.get("name"),
            r.get("sector"),
            r.get("industry"),
            r.get("market_cap_b"),
            r.get("current_price"),
            r.get("trailing_pe"),
            eps.get("eps_score"),
            eps.get("eps_growth_rate"),
            1 if eps.get("eps_consistent") else 0,
            roe.get("roe_score"),
            roe.get("roe"),
            roe.get("debt_to_equity"),
            fcf.get("fcf_score"),
            fcf.get("fcf_current"),
            fcf.get("fcf_yield"),
            1 if fcf.get("fcf_growing") else 0,
            bal.get("balance_score"),
            bal.get("current_ratio"),
            bal.get("cash_to_debt"),
            1 if bal.get("retained_earnings_growing") else 0,
            bal.get("goodwill_pct"),
            div.get("dividend_score"),
            div.get("dividend_yield_pct"),
            div.get("payout_ratio_pct"),
            div.get("consecutive_increases"),
            dcf.get("intrinsic_value"),
            dcf.get("margin_of_safety"),
            1 if dcf.get("undervalued") else 0,
            rev.get("revenue_cagr"),
            1 if rev.get("revenue_growing") else 0,
            r.get("buffett_score"),
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO scores (
            symbol, scan_date, name, sector, industry,
            market_cap_b, current_price, trailing_pe,
            eps_score, eps_cagr, eps_consistent,
            roe_score, roe_pct, debt_to_equity,
            fcf_score, fcf_current_b, fcf_yield, fcf_growing,
            balance_score, current_ratio, cash_to_debt,
            retained_earnings_growing, goodwill_pct,
            dividend_score, dividend_yield_pct, payout_ratio_pct,
            consecutive_div_increases,
            intrinsic_value, margin_of_safety, undervalued,
            revenue_cagr, revenue_growing,
            buffett_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()

    return len(rows)


def get_scan_dates(db_path=None):
    """Return all scan dates, most recent first."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT DISTINCT scan_date FROM scores ORDER BY scan_date DESC"
    ).fetchall()
    conn.close()
    return [r["scan_date"] for r in rows]


def get_scores_by_date(scan_date, db_path=None):
    """Return all scores for a given date, ranked by buffett_score."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT * FROM scores WHERE scan_date = ? ORDER BY buffett_score DESC",
        (scan_date,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ticker_history(symbol, db_path=None):
    """Return all scores for a ticker over time."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT * FROM scores WHERE symbol = ? ORDER BY scan_date ASC",
        (symbol.upper(),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_scores(db_path=None):
    """Return the most recent score for every ticker."""
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT s.* FROM scores s
        INNER JOIN (
            SELECT symbol, MAX(scan_date) AS max_date
            FROM scores GROUP BY symbol
        ) latest ON s.symbol = latest.symbol AND s.scan_date = latest.max_date
        ORDER BY s.buffett_score DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_biggest_movers(days=30, min_scans=2, db_path=None):
    """Find stocks with the biggest score changes over the last N days.

    Returns list of dicts with symbol, old_score, new_score, change, old_date, new_date.
    """
    conn = _connect(db_path)
    cutoff = date.today().isoformat()

    # Get latest score per ticker
    latest = conn.execute("""
        SELECT s.symbol, s.buffett_score, s.scan_date, s.name, s.sector
        FROM scores s
        INNER JOIN (
            SELECT symbol, MAX(scan_date) AS max_date
            FROM scores GROUP BY symbol
        ) l ON s.symbol = l.symbol AND s.scan_date = l.max_date
    """).fetchall()

    movers = []
    for row in latest:
        symbol = row["symbol"]
        # Find the oldest score within the window
        older = conn.execute("""
            SELECT buffett_score, scan_date FROM scores
            WHERE symbol = ? AND scan_date < ?
            ORDER BY scan_date ASC LIMIT 1
        """, (symbol, row["scan_date"])).fetchone()

        if older:
            change = row["buffett_score"] - older["buffett_score"]
            movers.append({
                "symbol": symbol,
                "name": row["name"],
                "sector": row["sector"],
                "old_score": older["buffett_score"],
                "new_score": row["buffett_score"],
                "change": round(change, 1),
                "old_date": older["scan_date"],
                "new_date": row["scan_date"],
            })

    conn.close()
    movers.sort(key=lambda x: abs(x["change"]), reverse=True)
    return movers
