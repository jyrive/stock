"""Dividend analysis: payout ratio, growth, yield, and consistency."""


def analyze_dividends(data):
    """Analyze dividend quality and sustainability.

    Sub-scores (25 pts each, total 100):
      - Pays a dividend at all              (25)
      - Payout ratio ≤60%                   (25)
      - Dividend yield ≥1%                  (25)
      - Dividend growing (5-yr history)     (25)

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

    # ── Score calculation ────────────────────────────────────────
    score = 0

    # 1. Pays a dividend (25 pts)
    pays_dividend = div_yield_pct > 0 or annual_div > 0
    if pays_dividend:
        score += 25

    # 2. Payout ratio sustainable (25 pts)
    if payout_pct is not None:
        if payout_pct <= 40:
            score += 25
        elif payout_pct <= 60:
            score += 20
        elif payout_pct <= 80:
            score += 10
        # >80% = 0 pts (unsustainable)
    elif not pays_dividend:
        score += 0  # No dividend, no payout score
    else:
        score += 12  # Unknown payout — half credit

    # 3. Dividend yield quality (25 pts)
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

    # 4. Dividend growth (25 pts)
    if consec_increases >= 4:
        score += 25  # 4+ consecutive years of growth
    elif consec_increases >= 2:
        score += 15
    elif div_growing:
        score += 10
    elif pays_dividend:
        score += 5  # At least pays something

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
