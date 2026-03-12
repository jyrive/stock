"""Database abstraction layer — connection management, schema, and migrations.

Centralizes all database access so the engine can be swapped later
(e.g. SQLite → PostgreSQL) by changing this one module.

Usage:
    from utils.db import transaction, get_connection, DB_PATH

    # Preferred — auto commit/rollback/close:
    with transaction() as conn:
        conn.execute("INSERT INTO ...", (...))

    # Manual (legacy compat) — caller must close:
    conn = get_connection()
    ...
    conn.close()
"""

import os
import sqlite3
from contextlib import contextmanager

from datasources.schema import SNAPSHOT_FIELDS, PRICE_COLUMNS, sql_columns

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, "scores.db")

# ═══════════════════════════════════════════════════════════════════════
#  Connection factory
# ═══════════════════════════════════════════════════════════════════════

def get_connection(db_path=None):
    """Open a new database connection.

    Currently SQLite.  To switch engines later, change this function
    and the transaction() context manager — everything else uses them.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction(db_path=None):
    """Context manager: yields a connection, auto-commits on success,
    rolls back on exception, and always closes.

    Usage:
        with transaction() as conn:
            conn.execute("INSERT INTO ...", (...))
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  Schema initialisation — runs once per process
# ═══════════════════════════════════════════════════════════════════════

_initialized_paths: set = set()


def ensure_schema(conn, db_path=None):
    """Create all tables and run migrations if needed.

    Safe to call on every connection — actual work happens only once
    per process per database path.
    """
    key = db_path or DB_PATH
    if key in _initialized_paths:
        return

    # Enable WAL for better concurrent read performance
    conn.execute("PRAGMA journal_mode=WAL")

    # Create all tables
    _create_all_tables(conn)

    # Run migrations
    _migrate(conn)

    conn.commit()
    _initialized_paths.add(key)


def reset_initialized():
    """Clear the initialization cache — for testing only."""
    _initialized_paths.clear()


# ═══════════════════════════════════════════════════════════════════════
#  Table definitions — each domain module registers its DDL here
# ═══════════════════════════════════════════════════════════════════════

def _create_all_tables(conn):
    """Create all tables (idempotent via IF NOT EXISTS)."""

    # ── Scores (from scores_db.py) ───────────────────────────────
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
            revenue_score INTEGER,
            tech_score    INTEGER,
            rsi_14        REAL,
            price_vs_sma200_pct REAL,
            fundamental_score REAL,
            PRIMARY KEY (symbol, scan_date)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scores_date ON scores (scan_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scores_symbol ON scores (symbol)"
    )

    # ── Fundamental snapshots — columns derived from schema ──────
    _snap_cols = sql_columns(SNAPSHOT_FIELDS)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS fundamental_snapshots (
            symbol          TEXT    NOT NULL,
            snapshot_date   TEXT    NOT NULL,
            {_snap_cols},
            info_json       TEXT,
            PRIMARY KEY (symbol, snapshot_date)
        )
    """)

    # ── Quarterly financials ─────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_financials (
            symbol          TEXT    NOT NULL,
            snapshot_date   TEXT    NOT NULL,
            period_end      TEXT    NOT NULL,
            statement_type  TEXT    NOT NULL,
            data_json       TEXT    NOT NULL,
            PRIMARY KEY (symbol, period_end, statement_type)
        )
    """)

    # ── Price cache — columns derived from schema ────────────────
    _price_cols = sql_columns(PRICE_COLUMNS)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS price_cache (
            symbol      TEXT    NOT NULL,
            trade_date  TEXT    NOT NULL,
            {_price_cols},
            PRIMARY KEY (symbol, trade_date)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_symbol_date "
        "ON price_cache (symbol, trade_date)"
    )

    # ── Macro cache ──────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS macro_cache (
            indicator   TEXT    NOT NULL,
            trade_date  TEXT    NOT NULL,
            close       REAL   NOT NULL,
            PRIMARY KEY (indicator, trade_date)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_macro_ind_date "
        "ON macro_cache (indicator, trade_date)"
    )

    # ── Positions (paper trading) ────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            action      TEXT    NOT NULL,
            shares      REAL    NOT NULL,
            price       REAL    NOT NULL,
            date        TEXT    NOT NULL,
            note        TEXT
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_positions_symbol "
        "ON positions (symbol)"
    )

    # ── Simulation runs ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            run_type        TEXT    NOT NULL,
            start_date      TEXT    NOT NULL,
            end_date        TEXT,
            starting_cash   REAL    NOT NULL,
            final_value     REAL,
            total_return_pct REAL,
            config_json     TEXT,
            metrics_json    TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          INTEGER NOT NULL,
            date            TEXT    NOT NULL,
            symbol          TEXT    NOT NULL,
            action          TEXT    NOT NULL,
            shares          REAL    NOT NULL,
            price           REAL    NOT NULL,
            value           REAL    NOT NULL,
            verdict         TEXT,
            fund_score      REAL,
            tech_score      REAL,
            macro_score     REAL,
            reason          TEXT,
            dividends       REAL    DEFAULT 0,
            FOREIGN KEY (run_id) REFERENCES sim_runs(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_equity_curve (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          INTEGER NOT NULL,
            date            TEXT    NOT NULL,
            total_value     REAL    NOT NULL,
            cash            REAL    NOT NULL,
            holdings_value  REAL    NOT NULL,
            num_holdings    INTEGER NOT NULL,
            FOREIGN KEY (run_id) REFERENCES sim_runs(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_holdings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          INTEGER NOT NULL,
            symbol          TEXT    NOT NULL,
            shares          REAL    NOT NULL,
            avg_cost        REAL    NOT NULL,
            total_cost      REAL    NOT NULL,
            first_buy_date  TEXT    NOT NULL,
            dividends       REAL    DEFAULT 0,
            last_verdict    TEXT,
            FOREIGN KEY (run_id) REFERENCES sim_runs(id)
        )
    """)

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sim_txn_run "
        "ON sim_transactions (run_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sim_eq_run "
        "ON sim_equity_curve (run_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sim_hold_run "
        "ON sim_holdings (run_id)"
    )

    # ── Schema version tracking ──────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id      INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
    """)


# ═══════════════════════════════════════════════════════════════════════
#  Migrations
# ═══════════════════════════════════════════════════════════════════════

def _get_version(conn):
    """Get current schema version (0 if table doesn't exist or is empty)."""
    try:
        row = conn.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        ).fetchone()
        return row["version"] if row else 0
    except Exception:
        return 0


def _set_version(conn, version):
    """Set the schema version."""
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, ?)",
        (version,),
    )


# Each migration function upgrades FROM the previous version.
# They run in order; only un-applied migrations execute.
# To add a new migration, append a function to this list.

def _migrate_v1(conn):
    """V1: baseline — add missing columns to scores table for older DBs."""
    existing_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(scores)").fetchall()
    }
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
        ("revenue_score", "INTEGER"),
        ("tech_score", "INTEGER"),
        ("rsi_14", "REAL"),
        ("price_vs_sma200_pct", "REAL"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE scores ADD COLUMN {col} {ctype}")

    # Rename buffett_score → fundamental_score
    if "buffett_score" in existing_cols and "fundamental_score" not in existing_cols:
        conn.execute(
            "ALTER TABLE scores RENAME COLUMN buffett_score TO fundamental_score"
        )


_MIGRATIONS = [
    _migrate_v1,
    # Future migrations go here:
    # _migrate_v2,
    # _migrate_v3,
]


def _migrate(conn):
    """Run any un-applied migrations."""
    current = _get_version(conn)
    for i, fn in enumerate(_MIGRATIONS):
        version = i + 1
        if version > current:
            fn(conn)
            _set_version(conn, version)
