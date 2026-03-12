"""Fundamental analysis — all scoring modules.

Each function takes a ``data`` dict (from ``utils.lists.get_financial_data``)
and returns an analysis dict with a score 0–100.

Sections:
    EPS Growth        — analyze_eps_growth()
    Return on Equity  — analyze_roe()
    Free Cash Flow    — analyze_free_cash_flow()
    Balance Sheet     — analyze_balance_sheet()
    Dividend          — analyze_dividends()
    DCF Valuation     — calculate_dcf_intrinsic_value()
    Revenue Growth    — analyze_revenue_growth()
"""

import numpy as np
import pandas as pd

from utils.config import get_dcf_params

# ── EPS Growth ─────────────────────────────────────────────

def analyze_eps_growth(data):
    """Analyze EPS consistency and growth over available years."""
    info = data["info"]
    income_stmt = data["income_stmt"]

    result = {
        "eps_values": [],
        "eps_growth_rate": None,
        "eps_consistent": False,
        "eps_score": 0,
    }

    try:
        if income_stmt is not None and not income_stmt.empty:
            net_income_row = None
            shares_row = None

            for label in ["Net Income", "Net Income Common Stockholders"]:
                if label in income_stmt.index:
                    net_income_row = income_stmt.loc[label]
                    break

            for label in [
                "Diluted Average Shares",
                "Basic Average Shares",
                "Ordinary Shares Number",
            ]:
                if label in income_stmt.index:
                    shares_row = income_stmt.loc[label]
                    break

            if net_income_row is not None and shares_row is not None:
                eps_series = (net_income_row / shares_row).dropna().sort_index()
                result["eps_values"] = [
                    (str(d.year), round(v, 2))
                    for d, v in eps_series.items()
                    if not np.isnan(v)
                ]

        if len(result["eps_values"]) >= 3:
            eps_vals = [v for _, v in result["eps_values"]]

            growth_years = sum(
                1 for i in range(1, len(eps_vals)) if eps_vals[i] > eps_vals[i - 1]
            )
            total_periods = len(eps_vals) - 1

            if total_periods > 0:
                consistency_ratio = growth_years / total_periods
                result["eps_consistent"] = consistency_ratio >= 0.65

                # CAGR
                if eps_vals[0] > 0 and eps_vals[-1] > 0:
                    years = len(eps_vals) - 1
                    cagr = (eps_vals[-1] / eps_vals[0]) ** (1 / years) - 1
                    result["eps_growth_rate"] = round(cagr * 100, 2)

                # Score: 0-100
                score = consistency_ratio * 50
                if result["eps_growth_rate"] and result["eps_growth_rate"] > 0:
                    score += min(result["eps_growth_rate"] * 2.5, 50)
                result["eps_score"] = round(score)
    except Exception:
        pass

    return result

# ── Return on Equity ───────────────────────────────────────

def analyze_roe(data):
    """Analyze Return on Equity and debt levels."""
    info = data["info"]
    balance_sheet = data["balance_sheet"]
    income_stmt = data["income_stmt"]

    result = {
        "roe": None,
        "roe_values": [],
        "debt_to_equity": None,
        "roe_high": False,
        "debt_reasonable": False,
        "roe_score": 0,
    }

    try:
        roe_info = info.get("returnOnEquity", None)
        if roe_info:
            result["roe"] = round(roe_info * 100, 2)

        # Historical ROE from statements
        if (
            income_stmt is not None
            and not income_stmt.empty
            and balance_sheet is not None
            and not balance_sheet.empty
        ):
            net_income_row = None
            equity_row = None

            for label in ["Net Income", "Net Income Common Stockholders"]:
                if label in income_stmt.index:
                    net_income_row = income_stmt.loc[label]
                    break

            for label in [
                "Stockholders Equity",
                "Total Stockholder Equity",
                "Common Stock Equity",
            ]:
                if label in balance_sheet.index:
                    equity_row = balance_sheet.loc[label]
                    break

            if net_income_row is not None and equity_row is not None:
                common_dates = net_income_row.dropna().index.intersection(
                    equity_row.dropna().index
                )
                for d in sorted(common_dates):
                    eq = equity_row[d]
                    ni = net_income_row[d]
                    if eq > 0:
                        roe_val = round((ni / eq) * 100, 2)
                        result["roe_values"].append((str(d.year), roe_val))

        # Debt to equity
        d_e = info.get("debtToEquity", None)
        if d_e is not None:
            result["debt_to_equity"] = round(d_e, 2)
            result["debt_reasonable"] = d_e < 150

        # Evaluate
        current_roe = result["roe"]
        if current_roe is None and result["roe_values"]:
            current_roe = result["roe_values"][-1][1]
            result["roe"] = current_roe

        if current_roe and current_roe > 15:
            result["roe_high"] = True

        # Score
        score = 0
        if current_roe:
            if current_roe > 30:
                score += 50
            elif current_roe > 20:
                score += 40
            elif current_roe > 15:
                score += 30
            elif current_roe > 10:
                score += 15

        if result["debt_reasonable"]:
            score += 25
        elif result["debt_to_equity"] is not None and result["debt_to_equity"] < 200:
            score += 10

        # Consistency bonus
        if len(result["roe_values"]) >= 3:
            high_roe_years = sum(1 for _, v in result["roe_values"] if v > 15)
            if high_roe_years == len(result["roe_values"]):
                score += 25
            elif high_roe_years / len(result["roe_values"]) > 0.7:
                score += 15

        result["roe_score"] = min(round(score), 100)
    except Exception:
        pass

    return result

# ── Free Cash Flow ─────────────────────────────────────────

def analyze_free_cash_flow(data):
    """Analyze Free Cash Flow strength and consistency."""
    info = data["info"]
    cash_flow = data["cash_flow"]

    result = {
        "fcf_values": [],
        "fcf_current": None,
        "fcf_yield": None,
        "fcf_positive_streak": 0,
        "fcf_growing": False,
        "fcf_score": 0,
    }

    try:
        if cash_flow is not None and not cash_flow.empty:
            fcf_row = None

            # Try direct FCF
            if "Free Cash Flow" in cash_flow.index:
                fcf_row = cash_flow.loc["Free Cash Flow"]

            if fcf_row is None:
                operating_cf = None
                capex = None

                for label in [
                    "Operating Cash Flow",
                    "Total Cash From Operating Activities",
                ]:
                    if label in cash_flow.index:
                        operating_cf = cash_flow.loc[label]
                        break

                for label in ["Capital Expenditure", "Capital Expenditures"]:
                    if label in cash_flow.index:
                        capex = cash_flow.loc[label]
                        break

                if operating_cf is not None and capex is not None:
                    common = operating_cf.dropna().index.intersection(
                        capex.dropna().index
                    )
                    fcf_dict = {d: operating_cf[d] + capex[d] for d in common}
                    fcf_row = pd.Series(fcf_dict)
                elif operating_cf is not None:
                    fcf_row = operating_cf

            if fcf_row is not None:
                fcf_sorted = fcf_row.dropna().sort_index()
                result["fcf_values"] = [
                    (str(d.year), round(v / 1e9, 2)) for d, v in fcf_sorted.items()
                ]

                if result["fcf_values"]:
                    result["fcf_current"] = result["fcf_values"][-1][1]

                    market_cap = data["market_cap"]
                    if market_cap and market_cap > 0:
                        result["fcf_yield"] = round(
                            (result["fcf_current"] * 1e9 / market_cap) * 100, 2
                        )

                    fcf_vals = [v for _, v in result["fcf_values"]]
                    streak = 0
                    for v in reversed(fcf_vals):
                        if v > 0:
                            streak += 1
                        else:
                            break
                    result["fcf_positive_streak"] = streak

                    if (
                        len(fcf_vals) >= 3
                        and fcf_vals[-1] > fcf_vals[0]
                        and fcf_vals[0] > 0
                    ):
                        result["fcf_growing"] = True

        # Fallback to info
        fcf_info = info.get("freeCashflow", None)
        if fcf_info and result["fcf_current"] is None:
            result["fcf_current"] = round(fcf_info / 1e9, 2)
            market_cap = data["market_cap"]
            if market_cap and market_cap > 0:
                result["fcf_yield"] = round((fcf_info / market_cap) * 100, 2)

        # Score
        score = 0
        if result["fcf_current"] and result["fcf_current"] > 0:
            score += 30
        if result["fcf_positive_streak"] >= 4:
            score += 25
        elif result["fcf_positive_streak"] >= 3:
            score += 15
        if result["fcf_growing"]:
            score += 25
        if result["fcf_yield"] and result["fcf_yield"] > 3:
            score += 20
        elif result["fcf_yield"] and result["fcf_yield"] > 2:
            score += 10

        result["fcf_score"] = min(round(score), 100)
    except Exception:
        pass

    return result

# ── Balance Sheet ──────────────────────────────────────────

def analyze_balance_sheet(data):
    """Analyze balance sheet health using four mechanical checks.

    Sub-score components (0-100):
        Current Ratio      — current assets / current liabilities  (up to 25 pts)
        Cash / Debt         — cash & equivalents / total debt       (up to 25 pts)
        Retained Earnings   — growing over available years          (up to 25 pts)
        Goodwill % of Assets — low goodwill relative to total assets (up to 25 pts)
    """
    balance_sheet = data["balance_sheet"]

    result = {
        "current_ratio": None,
        "cash_to_debt": None,
        "retained_earnings_growing": None,
        "retained_earnings_values": [],
        "goodwill_pct": None,
        "balance_score": 0,
    }

    try:
        if balance_sheet is None or balance_sheet.empty:
            return result

        # Helper: find first matching row label
        def _find(labels):
            for label in labels:
                if label in balance_sheet.index:
                    return balance_sheet.loc[label]
            return None

        # ── 1. Current Ratio ────────────────────────────────────────
        current_assets = _find([
            "Current Assets",
            "Total Current Assets",
        ])
        current_liabilities = _find([
            "Current Liabilities",
            "Total Current Liabilities",
        ])

        if current_assets is not None and current_liabilities is not None:
            # Use most recent column
            ca = current_assets.dropna()
            cl = current_liabilities.dropna()
            if len(ca) > 0 and len(cl) > 0:
                latest_ca = ca.iloc[0]  # columns are newest-first in yfinance
                latest_cl = cl.iloc[0]
                if latest_cl > 0:
                    result["current_ratio"] = round(latest_ca / latest_cl, 2)

        # ── 2. Cash / Total Debt ────────────────────────────────────
        cash = _find([
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
            "Cash Financial",
            "Cash",
        ])
        total_debt = _find([
            "Total Debt",
            "Total Non Current Liabilities Net Minority Interest",
            "Long Term Debt",
        ])

        if cash is not None and total_debt is not None:
            c = cash.dropna()
            d = total_debt.dropna()
            if len(c) > 0 and len(d) > 0:
                latest_cash = c.iloc[0]
                latest_debt = d.iloc[0]
                if latest_debt > 0:
                    result["cash_to_debt"] = round(latest_cash / latest_debt, 2)
                elif latest_cash > 0:
                    # No debt but has cash — excellent
                    result["cash_to_debt"] = 9.99  # cap for display

        # ── 3. Retained Earnings Trend ──────────────────────────────
        retained = _find([
            "Retained Earnings",
            "Retained Earnings (Accumulated Deficit)",
        ])

        if retained is not None:
            re_sorted = retained.dropna().sort_index()  # oldest first
            result["retained_earnings_values"] = [
                (str(d.year), round(v / 1e9, 2)) for d, v in re_sorted.items()
            ]
            if len(result["retained_earnings_values"]) >= 2:
                vals = [v for _, v in result["retained_earnings_values"]]
                result["retained_earnings_growing"] = vals[-1] > vals[0]

        # ── 4. Goodwill % of Total Assets ───────────────────────────
        goodwill = _find([
            "Goodwill",
            "Goodwill And Other Intangible Assets",
        ])
        total_assets = _find([
            "Total Assets",
        ])

        if goodwill is not None and total_assets is not None:
            gw = goodwill.dropna()
            ta = total_assets.dropna()
            if len(gw) > 0 and len(ta) > 0:
                latest_gw = gw.iloc[0]
                latest_ta = ta.iloc[0]
                if latest_ta > 0:
                    result["goodwill_pct"] = round((latest_gw / latest_ta) * 100, 1)

        # ── Scoring ─────────────────────────────────────────────────
        score = 0

        # Current Ratio: >2.0 excellent, >1.5 good, >1.0 ok
        cr = result["current_ratio"]
        if cr is not None:
            if cr >= 2.0:
                score += 25
            elif cr >= 1.5:
                score += 20
            elif cr >= 1.0:
                score += 10
            # Below 1.0: 0 pts — liquidity risk

        # Cash / Debt: >1.0 can pay off all debt, >0.5 reasonable, >0.25 ok
        cd = result["cash_to_debt"]
        if cd is not None:
            if cd >= 1.0:
                score += 25
            elif cd >= 0.5:
                score += 20
            elif cd >= 0.25:
                score += 10

        # Retained Earnings: growing = compounding machine
        if result["retained_earnings_growing"] is True:
            re_vals = [v for _, v in result["retained_earnings_values"]]
            # Check how consistent the growth is
            growth_years = sum(1 for i in range(1, len(re_vals)) if re_vals[i] > re_vals[i - 1])
            total_periods = len(re_vals) - 1
            if total_periods > 0 and growth_years / total_periods >= 0.75:
                score += 25  # consistently growing
            else:
                score += 15  # growing overall but not every year
        elif result["retained_earnings_growing"] is False:
            score += 0  # declining retained earnings

        # Goodwill: <10% excellent, <20% ok, <30% caution, >=30% red flag
        gw = result["goodwill_pct"]
        if gw is not None:
            if gw < 10:
                score += 25
            elif gw < 20:
                score += 15
            elif gw < 30:
                score += 5
            # >=30%: 0 pts — heavy acquisition risk
        else:
            # No goodwill on balance sheet — either no acquisitions or N/A
            # Give benefit of the doubt (likely no major acquisitions)
            score += 20

        result["balance_score"] = min(round(score), 100)

    except Exception:
        pass

    return result

# ── Dividend ───────────────────────────────────────────────

def analyze_dividends(data):
    """Analyze dividend quality and sustainability.

    Scoring philosophy (growth-friendly):
      - No dividend → 50/100 (neutral — reinvesting in growth is fine)
      - Sustainable dividend (payout ≤60%) → 75-100
      - Moderate dividend (payout 60-80%) → 50-75
      - Unsustainable dividend (payout >80%) → 0-40 (WARNING)

    Returns dict with dividend_score 0-100 and supporting metrics.
    """
    info = data.get("info", {})
    cash_flow = data.get("cash_flow")

    # ── Gather metrics ───────────────────────────────────────────
    # Compute yield from rate/price (most reliable)
    annual_div = info.get("dividendRate", 0) or 0    # $ per share annual
    current_price = data.get("current_price", 0) or 0

    if annual_div > 0 and current_price > 0:
        div_yield_pct = round((annual_div / current_price) * 100, 2)
    else:
        div_yield_pct = 0.0

    payout_ratio = info.get("payoutRatio")           # decimal (0.35 = 35%)
    if payout_ratio:
        payout_pct = round(payout_ratio * 100, 1)
    else:
        payout_pct = None

    # ── Dividend history from cash flow ──────────────────────────
    div_values = []
    div_growing = False
    if cash_flow is not None and not cash_flow.empty:
        # "Cash Dividends Paid" is typically negative
        for label in ["Cash Dividends Paid", "Payment Of Dividends",
                       "Common Stock Dividend Paid"]:
            if label in cash_flow.index:
                row = cash_flow.loc[label].dropna().sort_index()
                for col in row.index:
                    year = col.year if hasattr(col, "year") else col
                    val = float(row[col])
                    # Make positive for readability (dividends paid are negative)
                    div_values.append((year, round(abs(val) / 1e9, 2)))
                break

    div_values.sort(key=lambda x: x[0])

    if len(div_values) >= 2:
        # Growing if latest > earliest
        growing_count = sum(
            1 for i in range(1, len(div_values))
            if div_values[i][1] >= div_values[i - 1][1]
        )
        div_growing = growing_count >= len(div_values) // 2

    # ── Consecutive years of increase ────────────────────────────
    consec_increases = 0
    if len(div_values) >= 2:
        for i in range(len(div_values) - 1, 0, -1):
            if div_values[i][1] > div_values[i - 1][1]:
                consec_increases += 1
            else:
                break

    # ── Score calculation (growth-friendly) ──────────────────────
    pays_dividend = div_yield_pct > 0 or annual_div > 0

    if not pays_dividend:
        # ── No dividend: neutral baseline (50/100) ──────────────
        # Company reinvests everything into growth — that's OK.
        score = 50
    else:
        # ── Pays dividend: score based on sustainability ────────
        score = 0

        # 1. Payout ratio sustainability (up to 40 pts)
        #    This is the KEY metric — unsustainable = danger signal
        if payout_pct is not None:
            if payout_pct <= 40:
                score += 40   # Very sustainable
            elif payout_pct <= 60:
                score += 35   # Sustainable
            elif payout_pct <= 80:
                score += 20   # Watch closely
            elif payout_pct <= 100:
                score += 5    # Risky
            # >100% = 0 pts (paying out more than earnings — danger!)
        else:
            score += 20  # Unknown payout — cautious half credit

        # 2. Dividend yield quality (up to 25 pts)
        if div_yield_pct >= 3.0:
            score += 25
        elif div_yield_pct >= 2.0:
            score += 20
        elif div_yield_pct >= 1.0:
            score += 15
        elif div_yield_pct >= 0.5:
            score += 10
        elif div_yield_pct > 0:
            score += 5

        # 3. Dividend growth / consistency (up to 20 pts)
        if consec_increases >= 4:
            score += 20
        elif consec_increases >= 2:
            score += 12
        elif div_growing:
            score += 8
        elif pays_dividend:
            score += 3  # At least pays

        # 4. Base credit for being a dividend payer (15 pts)
        score += 15

    return {
        "dividend_score": score,
        "pays_dividend": pays_dividend,
        "dividend_yield_pct": div_yield_pct,
        "payout_ratio_pct": payout_pct,
        "annual_dividend": annual_div,
        "dividend_growing": div_growing,
        "consecutive_increases": consec_increases,
        "dividend_values": div_values,
    }

# ── DCF Valuation ──────────────────────────────────────────

def calculate_dcf_intrinsic_value(data, fcf_analysis):
    """Calculate intrinsic value using a conservative DCF model."""
    result = {
        "intrinsic_value": None,
        "current_price": None,
        "margin_of_safety": None,
        "upside_pct": None,
        "undervalued": False,
    }

    try:
        info = data["info"]
        current_price = data["current_price"]
        if not current_price or current_price <= 0:
            return result

        result["current_price"] = round(current_price, 2)

        # FCF per share
        fcf_total = None
        if fcf_analysis["fcf_current"]:
            fcf_total = fcf_analysis["fcf_current"] * 1e9
        elif info.get("freeCashflow"):
            fcf_total = info["freeCashflow"]

        if not fcf_total or fcf_total <= 0:
            return result

        shares = info.get("sharesOutstanding", None)
        if not shares or shares <= 0:
            return result

        fcf_per_share = fcf_total / shares

        # DCF assumptions from config
        params = get_dcf_params()
        growth_rate_high = params["growth_rate_high"]
        growth_rate_low = params["growth_rate_low"]
        terminal_growth = params["terminal_growth"]
        discount_rate = params["discount_rate"]
        margin_required = params.get("margin_required", 0.15)

        # Project FCF
        projected_fcf = []
        fcf = fcf_per_share

        for _ in range(5):
            fcf *= 1 + growth_rate_high
            projected_fcf.append(fcf)

        for _ in range(5):
            fcf *= 1 + growth_rate_low
            projected_fcf.append(fcf)

        # Terminal value
        terminal_value = (
            projected_fcf[-1]
            * (1 + terminal_growth)
            / (discount_rate - terminal_growth)
        )

        # Discount to present
        pv_fcfs = sum(
            cf / (1 + discount_rate) ** i for i, cf in enumerate(projected_fcf, 1)
        )
        pv_terminal = terminal_value / (1 + discount_rate) ** 10

        intrinsic_value = pv_fcfs + pv_terminal

        result["intrinsic_value"] = round(intrinsic_value, 2)
        result["margin_of_safety"] = round(
            ((intrinsic_value - current_price) / intrinsic_value) * 100, 2
        )
        result["upside_pct"] = round(
            ((intrinsic_value / current_price) - 1) * 100, 2
        )
        result["undervalued"] = intrinsic_value > current_price * (1 + margin_required)
    except Exception:
        pass

    return result

# ── Revenue Growth ─────────────────────────────────────────

def analyze_revenue_growth(data):
    """Analyze revenue growth trend.

    Returns dict with:
        revenue_values: [(year, revenue_in_billions), ...]
        revenue_cagr: compound annual growth rate
        revenue_growing: True if revenue has a positive trend
        revenue_consistent: True if >50% of years show growth
        revenue_score: 0-100 score
    """
    result = {
        "revenue_values": [],
        "revenue_cagr": None,
        "revenue_growing": False,
        "revenue_consistent": False,
        "revenue_score": 0,
    }

    try:
        income_stmt = data.get("income_stmt")
        if income_stmt is None or income_stmt.empty:
            return result

        # Find Total Revenue row
        rev_row = None
        for label in ["Total Revenue", "Revenue", "Operating Revenue"]:
            if label in income_stmt.index:
                rev_row = income_stmt.loc[label]
                break

        if rev_row is None:
            return result

        # Extract year → revenue pairs (in billions)
        revenues = []
        for col in sorted(rev_row.index):
            val = rev_row[col]
            if val is not None and val == val:  # not NaN
                year = col.year if hasattr(col, "year") else col
                revenues.append((year, round(float(val) / 1e9, 2)))

        if len(revenues) < 2:
            return result

        result["revenue_values"] = revenues

        # Count year-over-year growth
        yoy_increases = 0
        for i in range(1, len(revenues)):
            if revenues[i][1] > revenues[i - 1][1]:
                yoy_increases += 1

        consistency_ratio = yoy_increases / (len(revenues) - 1)
        result["revenue_consistent"] = consistency_ratio >= 0.50

        # Overall growing?
        first_rev = revenues[0][1]
        last_rev = revenues[-1][1]
        result["revenue_growing"] = last_rev > first_rev and first_rev > 0

        # CAGR
        if first_rev > 0 and last_rev > 0 and len(revenues) > 1:
            years = len(revenues) - 1
            cagr = ((last_rev / first_rev) ** (1 / years) - 1) * 100
            result["revenue_cagr"] = round(cagr, 2)

        # Score (0-100):
        #   Consistency (up to 40): what fraction of years showed growth
        #   CAGR magnitude (up to 40): 2.5 pts per 1% CAGR, capped at 40
        #   Growing overall (20): bonus if latest > earliest
        score = 0

        # Consistency
        score += min(consistency_ratio * 40, 40)

        # CAGR magnitude
        if result["revenue_cagr"] and result["revenue_cagr"] > 0:
            score += min(result["revenue_cagr"] * 2.5, 40)

        # Overall growth
        if result["revenue_growing"]:
            score += 20

        result["revenue_score"] = min(round(score), 100)

    except Exception:
        pass

    return result
