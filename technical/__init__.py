"""Technical analysis — entry-timing indicators.

Independently fetches price history via yfinance and computes
RSI, moving averages, Bollinger Bands, MACD, and 52-week range
to produce a Technical Score (0–100).
"""

from .analysis import analyze_technical

__all__ = ["analyze_technical"]
