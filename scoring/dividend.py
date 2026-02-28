"""Dividend / capital-allocation analysis.

Growth-friendly scoring: companies that pay no dividend are NOT penalised
(they score a neutral 50/100).  The score primarily flags *bad* capital
allocation — unsustainable payout ratios are heavily penalised.
"""


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
