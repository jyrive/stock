"""Shared utilities — data fetching, storage, formatting, caching."""

from .data import load_tickers, get_financial_data
from .formatting import print_results, print_summary_table, print_legend, flatten_result

__all__ = [
    "load_tickers",
    "get_financial_data",
    "print_results",
    "print_summary_table",
    "print_legend",
    "flatten_result",
]
