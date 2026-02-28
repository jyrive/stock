"""Revenue growth analysis: confirms organic demand vs. buyback-driven EPS.

Revenue growth is tracked alongside EPS to ensure earnings growth comes
from real demand, not just share buybacks or cost-cutting.
"""


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
