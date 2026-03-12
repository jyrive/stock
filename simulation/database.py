"""SQLite persistence for simulation portfolios, transactions, and backtest runs.

Separate from the manual paper-trading tables in positions — simulations
are fully isolated.
"""

import json
import os
import sqlite3
from datetime import date, datetime
from typing import Optional, List

from utils.db import DB_PATH, get_connection, ensure_schema


def _connect(db_path=None):
    """Open and initialise simulation tables."""
    conn = get_connection(db_path)
    ensure_schema(conn, db_path)
    return conn


# ── Save / Load simulation runs ─────────────────────────────────────

def save_simulation(portfolio, run_type="autotrade", db_path=None):
    """Persist a SimPortfolio to the database.

    Returns the run_id.
    """
    from simulation.engine import compute_metrics

    conn = _connect(db_path)
    metrics = compute_metrics(portfolio)

    # Simulation config
    config = {
        "starting_cash": portfolio.starting_cash,
        "max_position_pct": portfolio.max_position_pct,
        "max_positions": portfolio.max_positions,
        "stop_loss_pct": portfolio.stop_loss_pct,
        "take_profit_pct": portfolio.take_profit_pct,
        "commission": portfolio.commission,
    }

    start_date = portfolio.equity_curve[0]["date"] if portfolio.equity_curve else date.today().isoformat()
    end_date = portfolio.equity_curve[-1]["date"] if portfolio.equity_curve else None

    cursor = conn.execute("""
        INSERT INTO sim_runs (name, run_type, start_date, end_date,
                              starting_cash, final_value, total_return_pct,
                              config_json, metrics_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        portfolio.name,
        run_type,
        start_date,
        end_date,
        portfolio.starting_cash,
        metrics.get("final_value"),
        metrics.get("total_return_pct"),
        json.dumps(config),
        json.dumps(metrics),
    ))
    run_id = cursor.lastrowid

    # Save transactions
    for txn in portfolio.transactions:
        conn.execute("""
            INSERT INTO sim_transactions (run_id, date, symbol, action, shares,
                                          price, value, verdict, fund_score,
                                          tech_score, macro_score, reason, dividends)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, txn.date, txn.symbol, txn.action, txn.shares,
            txn.price, txn.value, txn.verdict, txn.fund_score,
            txn.tech_score, txn.macro_score, txn.reason, txn.dividends_collected,
        ))

    # Save equity curve
    for snap in portfolio.equity_curve:
        conn.execute("""
            INSERT INTO sim_equity_curve (run_id, date, total_value, cash,
                                          holdings_value, num_holdings)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_id, snap["date"], snap["total_value"], snap["cash"],
            snap["holdings_value"], snap["num_holdings"],
        ))

    # Save current holdings
    for sym, h in portfolio.holdings.items():
        last_verdict = None
        for txn in reversed(portfolio.transactions):
            if txn.symbol == sym:
                last_verdict = txn.verdict
                break
        conn.execute("""
            INSERT INTO sim_holdings (run_id, symbol, shares, avg_cost,
                                      total_cost, first_buy_date, dividends,
                                      last_verdict)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, sym, h.shares, h.avg_cost, h.total_cost,
            h.first_buy_date, h.dividends_collected, last_verdict,
        ))

    conn.commit()
    conn.close()
    return run_id


def list_runs(run_type=None, limit=20, db_path=None):
    """List saved simulation runs."""
    conn = _connect(db_path)
    if run_type:
        rows = conn.execute("""
            SELECT * FROM sim_runs WHERE run_type = ?
            ORDER BY created_at DESC LIMIT ?
        """, (run_type, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM sim_runs ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run(run_id, db_path=None):
    """Get a simulation run with its transactions, equity curve, and holdings."""
    conn = _connect(db_path)

    run = conn.execute("SELECT * FROM sim_runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        conn.close()
        return None

    transactions = conn.execute("""
        SELECT * FROM sim_transactions WHERE run_id = ? ORDER BY date, id
    """, (run_id,)).fetchall()

    equity_curve = conn.execute("""
        SELECT * FROM sim_equity_curve WHERE run_id = ? ORDER BY date
    """, (run_id,)).fetchall()

    holdings = conn.execute("""
        SELECT * FROM sim_holdings WHERE run_id = ?
    """, (run_id,)).fetchall()

    conn.close()

    return {
        "run": dict(run),
        "transactions": [dict(r) for r in transactions],
        "equity_curve": [dict(r) for r in equity_curve],
        "holdings": [dict(r) for r in holdings],
    }


def get_latest_autotrade_run(db_path=None):
    """Get the most recent autotrade run."""
    runs = list_runs(run_type="autotrade", limit=1, db_path=db_path)
    if not runs:
        return None
    return get_run(runs[0]["id"], db_path=db_path)


def delete_run(run_id, db_path=None):
    """Delete a simulation run and all associated data."""
    conn = _connect(db_path)
    conn.execute("DELETE FROM sim_transactions WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM sim_equity_curve WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM sim_holdings WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM sim_runs WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()
