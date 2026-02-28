"""Free Cash Flow analysis: consistency, growth, and yield."""

import pandas as pd


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
