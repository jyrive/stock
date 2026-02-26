"""EPS growth analysis: consistency and CAGR over available years."""

import numpy as np


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
