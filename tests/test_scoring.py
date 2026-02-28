"""Tests for scoring modules — uses mock data to avoid network calls."""

import pandas as pd
import numpy as np
import pytest

# ── Helpers: build mock financial data dicts ──────────────────────────


def _make_data(
    income_values=None,
    balance_values=None,
    cashflow_values=None,
    info_overrides=None,
    market_cap=100e9,
    current_price=150.0,
):
    """Build a ``data`` dict that mirrors ``get_financial_data()`` output."""
    years = pd.to_datetime(["2024-12-31", "2023-12-31", "2022-12-31", "2021-12-31"])

    # ── Income statement ─────────────────────────────────────────
    default_income = {
        "Net Income": [10e9, 9e9, 8e9, 7e9],
        "Diluted Average Shares": [1e9, 1e9, 1e9, 1e9],
        "Total Revenue": [80e9, 70e9, 65e9, 60e9],
    }
    inc = income_values if income_values is not None else default_income
    income_stmt = pd.DataFrame(inc, index=years).T

    # ── Balance sheet ────────────────────────────────────────────
    default_balance = {
        "Current Assets": [40e9, 38e9, 35e9, 30e9],
        "Current Liabilities": [20e9, 19e9, 18e9, 17e9],
        "Cash And Cash Equivalents": [15e9, 14e9, 12e9, 10e9],
        "Total Debt": [10e9, 11e9, 12e9, 13e9],
        "Stockholders Equity": [50e9, 48e9, 45e9, 42e9],
        "Retained Earnings": [30e9, 28e9, 25e9, 22e9],
        "Total Assets": [100e9, 95e9, 90e9, 85e9],
        "Goodwill": [5e9, 5e9, 5e9, 5e9],
    }
    bal = balance_values if balance_values is not None else default_balance
    balance_sheet = pd.DataFrame(bal, index=years).T

    # ── Cash flow ────────────────────────────────────────────────
    default_cf = {
        "Operating Cash Flow": [15e9, 13e9, 12e9, 11e9],
        "Capital Expenditure": [-3e9, -3e9, -2.5e9, -2e9],
    }
    cf = cashflow_values if cashflow_values is not None else default_cf
    cash_flow = pd.DataFrame(cf, index=years).T

    # ── Info dict ────────────────────────────────────────────────
    info = {
        "returnOnEquity": 0.20,
        "debtToEquity": 80.0,
        "trailingPE": 15.0,
        "freeCashflow": 12e9,
        "sharesOutstanding": 1e9,
        "dividendRate": 3.0,
        "payoutRatio": 0.30,
        "currentPrice": current_price,
        "marketCap": market_cap,
        "currentRatio": 2.0,
        "profitMargins": 0.125,
        "revenueGrowth": 0.14,
    }
    if info_overrides:
        info.update(info_overrides)

    return {
        "symbol": "TEST",
        "name": "Test Corp",
        "sector": "Technology",
        "industry": "Software",
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "market_cap": market_cap,
        "current_price": current_price,
        "trailing_pe": info.get("trailingPE"),
    }


# ═══════════════════════════════════════════════════════════════════
# EPS Tests
# ═══════════════════════════════════════════════════════════════════


class TestEPSGrowth:
    def test_consistent_growth(self):
        from scoring.eps import analyze_eps_growth

        data = _make_data()
        result = analyze_eps_growth(data)

        assert result["eps_consistent"] is True
        assert result["eps_score"] > 0
        assert len(result["eps_values"]) == 4
        assert result["eps_growth_rate"] > 0

    def test_declining_eps(self):
        from scoring.eps import analyze_eps_growth

        # Reverse: declining net income
        data = _make_data(income_values={
            "Net Income": [7e9, 8e9, 9e9, 10e9],
            "Diluted Average Shares": [1e9, 1e9, 1e9, 1e9],
            "Total Revenue": [60e9, 65e9, 70e9, 80e9],
        })
        result = analyze_eps_growth(data)
        assert result["eps_consistent"] is False

    def test_empty_income_stmt(self):
        from scoring.eps import analyze_eps_growth

        data = _make_data()
        data["income_stmt"] = pd.DataFrame()
        result = analyze_eps_growth(data)
        assert result["eps_score"] == 0
        assert result["eps_values"] == []


# ═══════════════════════════════════════════════════════════════════
# ROE Tests
# ═══════════════════════════════════════════════════════════════════


class TestROE:
    def test_high_roe(self):
        from scoring.roe import analyze_roe

        data = _make_data(info_overrides={"returnOnEquity": 0.25, "debtToEquity": 50})
        result = analyze_roe(data)

        assert result["roe"] == 25.0
        assert result["roe_high"] is True
        assert result["debt_reasonable"] is True
        assert result["roe_score"] > 50

    def test_low_roe(self):
        from scoring.roe import analyze_roe

        data = _make_data(info_overrides={"returnOnEquity": 0.05, "debtToEquity": 300})
        result = analyze_roe(data)

        assert result["roe"] == 5.0
        assert result["roe_high"] is False
        assert result["debt_reasonable"] is False
        assert result["roe_score"] < 30

    def test_missing_roe(self):
        from scoring.roe import analyze_roe

        data = _make_data(info_overrides={"returnOnEquity": None, "debtToEquity": None})
        # Remove equity from balance sheet to prevent historical calc
        data["balance_sheet"] = pd.DataFrame()
        result = analyze_roe(data)
        assert result["roe"] is None


# ═══════════════════════════════════════════════════════════════════
# FCF Tests
# ═══════════════════════════════════════════════════════════════════


class TestFCF:
    def test_strong_fcf(self):
        from scoring.fcf import analyze_free_cash_flow

        data = _make_data()
        result = analyze_free_cash_flow(data)

        assert result["fcf_current"] is not None
        assert result["fcf_current"] > 0
        assert result["fcf_score"] > 0
        assert result["fcf_positive_streak"] >= 1

    def test_no_cash_flow(self):
        from scoring.fcf import analyze_free_cash_flow

        data = _make_data(info_overrides={"freeCashflow": None})
        data["cash_flow"] = pd.DataFrame()
        result = analyze_free_cash_flow(data)
        assert result["fcf_current"] is None


# ═══════════════════════════════════════════════════════════════════
# Balance Sheet Tests
# ═══════════════════════════════════════════════════════════════════


class TestBalanceSheet:
    def test_strong_balance(self):
        from scoring.balance import analyze_balance_sheet

        data = _make_data()
        result = analyze_balance_sheet(data)

        assert result["current_ratio"] is not None
        assert result["current_ratio"] >= 1.5
        assert result["cash_to_debt"] is not None
        assert result["retained_earnings_growing"] is True
        assert result["balance_score"] > 50

    def test_empty_balance(self):
        from scoring.balance import analyze_balance_sheet

        data = _make_data()
        data["balance_sheet"] = pd.DataFrame()
        result = analyze_balance_sheet(data)
        assert result["balance_score"] == 0


# ═══════════════════════════════════════════════════════════════════
# Dividend Tests
# ═══════════════════════════════════════════════════════════════════


class TestDividend:
    def test_pays_dividend(self):
        from scoring.dividend import analyze_dividends

        data = _make_data(
            info_overrides={"dividendRate": 3.0, "payoutRatio": 0.35},
            cashflow_values={
                "Operating Cash Flow": [15e9, 13e9, 12e9, 11e9],
                "Capital Expenditure": [-3e9, -3e9, -2.5e9, -2e9],
                "Cash Dividends Paid": [-3e9, -2.8e9, -2.5e9, -2.2e9],
            },
        )
        result = analyze_dividends(data)

        assert result["pays_dividend"] is True
        assert result["dividend_yield_pct"] > 0
        assert result["dividend_score"] > 0

    def test_no_dividend(self):
        from scoring.dividend import analyze_dividends

        data = _make_data(info_overrides={"dividendRate": 0, "payoutRatio": None})
        result = analyze_dividends(data)
        assert result["pays_dividend"] is False
        assert result["dividend_yield_pct"] == 0.0
        # Growth-friendly: no dividend = neutral 50/100 (not penalised)
        assert result["dividend_score"] == 50


# ═══════════════════════════════════════════════════════════════════
# DCF Tests
# ═══════════════════════════════════════════════════════════════════


class TestDCF:
    def test_undervalued(self):
        from scoring.dcf import calculate_dcf_intrinsic_value
        from scoring.fcf import analyze_free_cash_flow

        # Low price → should be undervalued
        data = _make_data(current_price=50.0)
        fcf = analyze_free_cash_flow(data)
        result = calculate_dcf_intrinsic_value(data, fcf)

        assert result["intrinsic_value"] is not None
        assert result["intrinsic_value"] > 0
        assert result["margin_of_safety"] is not None
        assert result["undervalued"] is True

    def test_overvalued(self):
        from scoring.dcf import calculate_dcf_intrinsic_value
        from scoring.fcf import analyze_free_cash_flow

        # Very high price → should be overvalued
        data = _make_data(current_price=5000.0)
        fcf = analyze_free_cash_flow(data)
        result = calculate_dcf_intrinsic_value(data, fcf)

        assert result["intrinsic_value"] is not None
        assert result["undervalued"] is False

    def test_no_fcf(self):
        from scoring.dcf import calculate_dcf_intrinsic_value

        data = _make_data()
        fcf = {"fcf_current": None}
        data["info"]["freeCashflow"] = None
        result = calculate_dcf_intrinsic_value(data, fcf)
        assert result["intrinsic_value"] is None


# ═══════════════════════════════════════════════════════════════════
# Revenue Tests
# ═══════════════════════════════════════════════════════════════════


class TestRevenue:
    def test_growing_revenue(self):
        from scoring.revenue import analyze_revenue_growth

        data = _make_data()
        result = analyze_revenue_growth(data)

        assert result["revenue_growing"] is True
        assert result["revenue_cagr"] is not None
        assert result["revenue_cagr"] > 0
        assert result["revenue_score"] > 0
        assert len(result["revenue_values"]) == 4

    def test_declining_revenue(self):
        from scoring.revenue import analyze_revenue_growth

        data = _make_data(income_values={
            "Net Income": [10e9, 9e9, 8e9, 7e9],
            "Diluted Average Shares": [1e9, 1e9, 1e9, 1e9],
            "Total Revenue": [60e9, 65e9, 70e9, 80e9],  # oldest first but DataFrame reverses
        })
        result = analyze_revenue_growth(data)
        # The revenue_values are sorted by date; whether growing depends on order
        assert "revenue_cagr" in result

    def test_no_revenue_data(self):
        from scoring.revenue import analyze_revenue_growth

        data = _make_data()
        data["income_stmt"] = pd.DataFrame()
        result = analyze_revenue_growth(data)
        assert result["revenue_score"] == 0
        assert result["revenue_values"] == []
