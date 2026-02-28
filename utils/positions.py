"""Paper portfolio positions tracking via SQLite.

Stores buy/sell transactions and provides P&L + total return calculations.
Uses the same scores.db file as the screening database.
"""

import os
import sqlite3
from datetime import date, datetime

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scores.db"
)


def _connect(db_path=None):
    """Open and initialise the positions table."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            action      TEXT    NOT NULL,  -- 'BUY' or 'SELL'
            shares      REAL    NOT NULL,
            price       REAL    NOT NULL,
            date        TEXT    NOT NULL,
            note        TEXT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_symbol
        ON positions (symbol)
    """)

    conn.commit()
    return conn


# ── Record transactions ──────────────────────────────────────────────

def record_buy(symbol, shares, price, buy_date=None, note=None, db_path=None):
    """Record a buy transaction."""
    conn = _connect(db_path)
    d = buy_date or date.today().isoformat()
    conn.execute(
        "INSERT INTO positions (symbol, action, shares, price, date, note) VALUES (?,?,?,?,?,?)",
        (symbol.upper(), "BUY", shares, price, d, note),
    )
    conn.commit()
    conn.close()


def record_sell(symbol, shares, price, sell_date=None, note=None, db_path=None):
    """Record a sell transaction."""
    conn = _connect(db_path)
    d = sell_date or date.today().isoformat()
    conn.execute(
        "INSERT INTO positions (symbol, action, shares, price, date, note) VALUES (?,?,?,?,?,?)",
        (symbol.upper(), "SELL", shares, price, d, note),
    )
    conn.commit()
    conn.close()


# ── Query positions ──────────────────────────────────────────────────

def get_positions(db_path=None):
    """Get net position for each symbol.

    Returns list of dicts:
        {symbol, shares, avg_cost, total_cost, first_buy_date}

    Handles multiple buys (averages cost) and partial sells.
    """
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT symbol, action, shares, price, date FROM positions ORDER BY date, id"
    ).fetchall()
    conn.close()

    # Aggregate per symbol
    holdings = {}  # symbol -> {shares, total_cost, first_buy_date}
    for r in rows:
        sym = r["symbol"]
        if sym not in holdings:
            holdings[sym] = {"shares": 0, "total_cost": 0, "first_buy_date": r["date"]}

        if r["action"] == "BUY":
            holdings[sym]["shares"] += r["shares"]
            holdings[sym]["total_cost"] += r["shares"] * r["price"]
        elif r["action"] == "SELL":
            # Reduce shares (FIFO cost reduction proportional)
            h = holdings[sym]
            if h["shares"] > 0:
                avg = h["total_cost"] / h["shares"]
                sell_shares = min(r["shares"], h["shares"])
                h["shares"] -= sell_shares
                h["total_cost"] -= sell_shares * avg

    # Build result — only open positions
    result = []
    for sym, h in holdings.items():
        if h["shares"] > 0.001:  # skip fully closed
            avg_cost = h["total_cost"] / h["shares"]
            result.append({
                "symbol": sym,
                "shares": h["shares"],
                "avg_cost": avg_cost,
                "total_cost": h["total_cost"],
                "first_buy_date": h["first_buy_date"],
            })

    result.sort(key=lambda x: x["symbol"])
    return result


def get_transactions(symbol=None, db_path=None):
    """Get all transactions, optionally filtered by symbol."""
    conn = _connect(db_path)
    if symbol:
        rows = conn.execute(
            "SELECT * FROM positions WHERE symbol = ? ORDER BY date, id",
            (symbol.upper(),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM positions ORDER BY date, id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_positions(db_path=None):
    """Check if any positions exist."""
    conn = _connect(db_path)
    row = conn.execute("SELECT COUNT(*) FROM positions").fetchone()
    conn.close()
    return row[0] > 0


def delete_position(position_id, db_path=None):
    """Delete a transaction by ID (for corrections)."""
    conn = _connect(db_path)
    conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
    conn.commit()
    conn.close()
