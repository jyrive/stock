#!/usr/bin/env python3
"""
Warren Buffett Style Stock Screener

Usage:
    python buffett_screener.py                    # screen tickers from tickers.txt
    python buffett_screener.py AAPL MSFT GOOGL    # screen specific tickers
    python buffett_screener.py my_picks.txt       # screen tickers from a custom file
"""

import sys
import time
import warnings

from screener import (
    load_tickers,
    get_financial_data,
    analyze_eps_growth,
    analyze_roe,
    analyze_free_cash_flow,
    calculate_dcf_intrinsic_value,
    print_results,
    save_results,
)
from screener.db import save_scores

warnings.filterwarnings("ignore")


def screen_stock(ticker_symbol, index, total):
    """Screen a single stock against all Buffett criteria."""
    print(f"  [{index}/{total}] Analyzing {ticker_symbol}...")

    data = get_financial_data(ticker_symbol)
    if data is None:
        return None

    eps = analyze_eps_growth(data)
    roe = analyze_roe(data)
    fcf = analyze_free_cash_flow(data)
    dcf = calculate_dcf_intrinsic_value(data, fcf)

    total_score = (
        eps["eps_score"] * 0.25
        + roe["roe_score"] * 0.25
        + fcf["fcf_score"] * 0.30
        + (25 if dcf["undervalued"] else 0) * 0.20
    )

    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "sector": data["sector"],
        "industry": data["industry"],
        "market_cap_b": round(data["market_cap"] / 1e9, 1) if data["market_cap"] else None,
        "current_price": data["current_price"],
        "trailing_pe": data["trailing_pe"],
        "eps_analysis": eps,
        "roe_analysis": roe,
        "fcf_analysis": fcf,
        "dcf_analysis": dcf,
        "buffett_score": round(total_score, 1),
    }


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith(".txt") or arg.endswith(".csv"):
            candidates = load_tickers(arg)
        else:
            candidates = [t.upper().strip() for t in sys.argv[1:] if t.strip()]
    else:
        candidates = load_tickers()

    # Interactive prompt if no tickers were resolved
    if not candidates:
        print("No tickers found in tickers.txt or command line.")
        raw = input("Enter ticker(s) to analyze (comma or space separated): ").strip()
        if not raw:
            print("No tickers entered. Exiting.")
            return
        candidates = [t.upper().strip() for t in raw.replace(",", " ").split() if t.strip()]

    print("=" * 80)
    print("WARREN BUFFETT STYLE STOCK SCREENER")
    print("=" * 80)
    print(f"\nScreening {len(candidates)} companies...\n")

    results = []
    for i, ticker in enumerate(candidates, 1):
        result = screen_stock(ticker, i, len(candidates))
        if result:
            results.append(result)
        time.sleep(0.3)

    results.sort(key=lambda x: x["buffett_score"], reverse=True)

    print_results(results)
    save_results(results)

    # Save to local SQLite database
    saved = save_scores(results)
    print(f"Scores saved to scores.db ({saved} stocks, date: {__import__('datetime').date.today()})")

    print(f"Total companies analyzed: {len(results)}")
    passing = sum(
        1 for r in results
        if r["eps_analysis"]["eps_consistent"]
        and r["roe_analysis"]["roe_high"]
        and r["fcf_analysis"]["fcf_score"] >= 50
    )
    print(f"Companies passing all key criteria: {passing}")


if __name__ == "__main__":
    main()
