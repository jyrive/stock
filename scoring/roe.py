"""Return on Equity analysis: ROE trends and debt levels."""


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
