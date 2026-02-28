"""Tests for database module."""

import os
import tempfile
import pytest

from utils.database import (
    save_scores,
    get_latest_scores,
    get_ticker_history,
    get_scan_dates,
    _connect,
)


def _sample_result(symbol="AAPL", score=75.0):
    """Build a minimal result dict for database storage."""
    return {
        "symbol": symbol,
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap_b": 3000.0,
        "current_price": 190.0,
        "trailing_pe": 30.0,
        "eps_analysis": {
            "eps_score": 80,
            "eps_growth_rate": 12.5,
            "eps_consistent": True,
        },
        "roe_analysis": {
            "roe_score": 70,
            "roe": 25.0,
            "debt_to_equity": 80.0,
        },
        "fcf_analysis": {
            "fcf_score": 85,
            "fcf_current": 100.0,
            "fcf_yield": 3.5,
            "fcf_growing": True,
        },
        "balance_analysis": {
            "balance_score": 65,
            "current_ratio": 1.5,
            "cash_to_debt": 0.8,
            "retained_earnings_growing": True,
            "goodwill_pct": 5.0,
        },
        "dividend_analysis": {
            "dividend_score": 60,
            "dividend_yield_pct": 0.5,
            "payout_ratio_pct": 15.0,
            "consecutive_increases": 10,
        },
        "dcf_analysis": {
            "intrinsic_value": 200.0,
            "margin_of_safety": 5.0,
            "undervalued": False,
        },
        "revenue_analysis": {
            "revenue_cagr": 8.5,
            "revenue_growing": True,
        },
        "buffett_score": score,
    }


class TestDatabase:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def teardown_method(self):
        os.unlink(self.db_path)

    def test_save_and_retrieve(self):
        results = [_sample_result("AAPL", 75), _sample_result("MSFT", 80)]
        saved = save_scores(results, db_path=self.db_path)
        assert saved == 2

        latest = get_latest_scores(db_path=self.db_path)
        assert len(latest) == 2
        # Sorted by score DESC
        assert latest[0]["symbol"] == "MSFT"

    def test_ticker_history(self):
        results = [_sample_result("AAPL", 75)]
        save_scores(results, db_path=self.db_path)

        history = get_ticker_history("AAPL", db_path=self.db_path)
        assert len(history) == 1
        assert history[0]["symbol"] == "AAPL"
        assert history[0]["buffett_score"] == 75

    def test_scan_dates(self):
        save_scores([_sample_result()], db_path=self.db_path)
        dates = get_scan_dates(db_path=self.db_path)
        assert len(dates) == 1

    def test_revenue_columns_saved(self):
        results = [_sample_result("AAPL")]
        save_scores(results, db_path=self.db_path)

        latest = get_latest_scores(db_path=self.db_path)
        assert latest[0]["revenue_cagr"] == 8.5
        assert latest[0]["revenue_growing"] == 1

    def test_migration_adds_columns(self):
        """Test that _connect migrates old DBs without revenue columns."""
        import sqlite3

        # Create a minimal table without revenue columns
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE scores (
                symbol TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                buffett_score REAL,
                PRIMARY KEY (symbol, scan_date)
            )
        """)
        conn.commit()
        conn.close()

        # _connect should add the missing columns
        conn = _connect(self.db_path)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(scores)").fetchall()}
        conn.close()

        assert "revenue_cagr" in cols
        assert "revenue_growing" in cols
        assert "balance_score" in cols
