"""Analysis functions: EPS growth, ROE, Free Cash Flow, and DCF valuation."""

import numpy as np
import pandas as pd


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

                    if len(fcf_vals) >= 3 and fcf_vals[-1] > fcf_vals[0] and fcf_vals[0] > 0:
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

        # DCF assumptions (conservative Buffett-style)
        growth_rate_high = 0.08  # 8% for years 1-5
        growth_rate_low = 0.03  # 3% for years 6-10
        terminal_growth = 0.025  # 2.5% terminal growth
        discount_rate = 0.10  # 10% required return

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
            projected_fcf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
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
        result["undervalued"] = intrinsic_value > current_price * 1.15
    except Exception:
        pass

    return result
