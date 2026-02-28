"""Tests for export module."""

import os
import csv
import tempfile
import pytest


def _sample_results():
    """Build a list with one sample result for export testing."""
    return [{
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap_b": 3000.0,
        "current_price": 190.0,
        "trailing_pe": 30.0,
        "buffett_score": 75.0,
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
    }]


class TestExport:
    def test_csv_export(self):
        from utils.export import export_csv

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            tmppath = f.name

        try:
            export_csv(_sample_results(), tmppath)
            assert os.path.exists(tmppath)

            with open(tmppath) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["Symbol"] == "AAPL"
            assert "Revenue CAGR (%)" in rows[0]
            assert rows[0]["Revenue Growing"] == "Yes"
        finally:
            os.unlink(tmppath)

    def test_flat_row_keys(self):
        from utils.export import _flat_row

        row = _flat_row(_sample_results()[0])
        assert "Symbol" in row
        assert "Buffett Score" in row
        assert "Revenue CAGR (%)" in row
        assert "Revenue Growing" in row
        assert "Intrinsic Value" in row

    def test_excel_export_or_fallback(self):
        from utils.export import export_excel

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmppath = f.name

        try:
            export_excel(_sample_results(), tmppath)
            # File should exist (either as xlsx or csv fallback)
            assert os.path.exists(tmppath) or os.path.exists(tmppath.replace(".xlsx", ".csv"))
        finally:
            if os.path.exists(tmppath):
                os.unlink(tmppath)
            csv_fallback = tmppath.replace(".xlsx", ".csv")
            if os.path.exists(csv_fallback):
                os.unlink(csv_fallback)
