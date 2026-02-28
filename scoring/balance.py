"""Balance sheet health analysis: liquidity, debt coverage, retained earnings, goodwill."""


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
