"""Tests for the alerts module."""

import os
import tempfile
import pytest

from utils.scores_db import save_scores


def _sample_result(symbol="AAPL", score=75.0, mos=10.0, iv=200.0, price=180.0):
    """Build a result dict for testing alerts."""
    return {
        "symbol": symbol,
        "name": f"{symbol} Corp",
        "sector": "Technology",
        "industry": "Software",
        "market_cap_b": 3000.0,
        "current_price": price,
        "trailing_pe": 25.0,
        "fundamental_score": score,
        "eps_analysis": {"eps_score": 75, "eps_growth_rate": 10.0, "eps_consistent": True},
        "roe_analysis": {"roe_score": 70, "roe": 20.0, "debt_to_equity": 50.0},
        "fcf_analysis": {"fcf_score": 80, "fcf_current": 50.0, "fcf_yield": 3.0, "fcf_growing": True},
        "balance_analysis": {"balance_score": 65, "current_ratio": 2.0, "cash_to_debt": 1.0,
                             "retained_earnings_growing": True, "goodwill_pct": 5.0},
        "dividend_analysis": {"dividend_score": 55, "dividend_yield_pct": 1.5,
                              "payout_ratio_pct": 30.0, "consecutive_increases": 5},
        "dcf_analysis": {"intrinsic_value": iv, "margin_of_safety": mos, "undervalued": mos > 0},
        "revenue_analysis": {"revenue_cagr": 8.0, "revenue_growing": True},
    }


class TestAlerts:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def teardown_method(self):
        os.unlink(self.db_path)

    def test_undervalued_detected(self):
        from commands.alerts import scan_alerts

        results = [
            _sample_result("AAPL", score=70, mos=15.0),
            _sample_result("MSFT", score=60, mos=-5.0),
        ]
        save_scores(results, db_path=self.db_path)

        alerts = scan_alerts(db_path=self.db_path)
        symbols = [a["symbol"] for a in alerts["undervalued"]]
        assert "AAPL" in symbols
        assert "MSFT" not in symbols

    def test_bargains_detected(self):
        from commands.alerts import scan_alerts

        results = [
            _sample_result("AAPL", score=65, mos=20.0),   # Bargain: score≥55 + MoS>10
            _sample_result("MSFT", score=40, mos=20.0),    # Not bargain: score<55
        ]
        save_scores(results, db_path=self.db_path)

        alerts = scan_alerts(db_path=self.db_path)
        bargain_syms = [b["symbol"] for b in alerts["bargains"]]
        assert "AAPL" in bargain_syms
        assert "MSFT" not in bargain_syms

    def test_no_alerts_on_empty_db(self):
        from commands.alerts import scan_alerts

        alerts = scan_alerts(db_path=self.db_path)
        assert alerts["undervalued"] == []
        assert alerts["bargains"] == []
        assert alerts["score_drops"] == []
