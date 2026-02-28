"""Backwards-compatibility shim — use fundamental/, technical/, macro/, verdict/ directly.

This package re-exports from the new domain packages so existing code
continues to work during the transition.
"""

# Re-export fundamental scorers
from fundamental.eps import analyze_eps_growth
from fundamental.roe import analyze_roe
from fundamental.fcf import analyze_free_cash_flow
from fundamental.balance import analyze_balance_sheet
from fundamental.dividend import analyze_dividends
from fundamental.dcf import calculate_dcf_intrinsic_value
from fundamental.revenue import analyze_revenue_growth

__all__ = [
    "analyze_eps_growth",
    "analyze_roe",
    "analyze_free_cash_flow",
    "analyze_balance_sheet",
    "analyze_dividends",
    "calculate_dcf_intrinsic_value",
    "analyze_revenue_growth",
]
