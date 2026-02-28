"""Macro-economic environment analysis — global market context.

Independently fetches global indicators via yfinance and scores
the macro environment for equity investing (0–100).
"""

from .analysis import analyze_macro

__all__ = ["analyze_macro"]
