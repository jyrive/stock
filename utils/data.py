"""Data fetching: load tickers from file and fetch financial data from yfinance."""

import os
import sys

import yfinance as yf

# Default ticker file path (project root)
DEFAULT_TICKER_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tickers.txt"
)


def load_tickers(filepath=None):
    """Load tickers from a text file. One ticker per line, # for comments."""
    path = filepath or DEFAULT_TICKER_FILE
    if not os.path.exists(path):
        print(f"Error: Ticker file not found: {path}")
        print("Create a file with one ticker per line. Lines starting with # are comments.")
        sys.exit(1)

    tickers = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Support comma-separated tickers on one line
            for t in line.split(","):
                t = t.strip().upper()
                if t:
                    tickers.append(t)

    if not tickers:
        print(f"Error: No tickers found in {path}")
        sys.exit(1)

    return tickers


def get_financial_data(ticker_symbol):
    """Fetch comprehensive financial data for a company via yfinance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        if not info or "marketCap" not in info:
            return None

        return {
            "symbol": ticker_symbol,
            "name": info.get("longName", info.get("shortName", ticker_symbol)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "current_price": info.get(
                "currentPrice", info.get("regularMarketPrice", 0)
            ),
            "trailing_pe": info.get("trailingPE", None),
            "forward_pe": info.get("forwardPE", None),
            "info": info,
            "income_stmt": ticker.income_stmt,
            "balance_sheet": ticker.balance_sheet,
            "cash_flow": ticker.cash_flow,
        }
    except Exception as e:
        print(f"  Error fetching {ticker_symbol}: {e}")
        return None
