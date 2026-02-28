"""Buffett Stock Screener package."""

from .data import load_tickers, get_financial_data
from .eps import analyze_eps_growth
from .roe import analyze_roe
from .fcf import analyze_free_cash_flow
from .balance import analyze_balance_sheet
from .dividend import analyze_dividends
from .dcf import calculate_dcf_intrinsic_value
from .output import print_results, print_summary_table, print_legend, flatten_result

__all__ = [
    "load_tickers",
    "get_financial_data",
    "analyze_eps_growth",
    "analyze_roe",
    "analyze_free_cash_flow",
    "analyze_balance_sheet",
    "analyze_dividends",
    "calculate_dcf_intrinsic_value",
    "print_results",
    "print_summary_table",
    "print_legend",
    "flatten_result",
]
