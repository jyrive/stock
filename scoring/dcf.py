"""DCF valuation: calculate intrinsic value and margin of safety."""

from utils.config import get_dcf_params


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
