"""Fundamental analysis — fundamental scoring modules.

Each module takes a ``data`` dict (from ``utils.data.get_financial_data``)
and returns an analysis dict with a score 0–100.
"""

from .eps import analyze_eps_growth
from .roe import analyze_roe
from .fcf import analyze_free_cash_flow
from .balance import analyze_balance_sheet
from .dividend import analyze_dividends
from .dcf import calculate_dcf_intrinsic_value
from .revenue import analyze_revenue_growth

__all__ = [
    "analyze_eps_growth",
    "analyze_roe",
    "analyze_free_cash_flow",
    "analyze_balance_sheet",
    "analyze_dividends",
    "calculate_dcf_intrinsic_value",
    "analyze_revenue_growth",
]
