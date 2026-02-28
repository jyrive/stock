#!/usr/bin/env python3
"""
Buffett Fundamental Analyzer

Deep-scores stocks on EPS growth, ROE, FCF, and DCF intrinsic value.
Saves results to scores.db for historical tracking.

Usage:
    python stock.py analyze              # analyze tickers from tickers.txt
    python stock.py analyze AAPL MSFT    # analyze specific tickers
    python stock.py analyze picks.txt    # analyze tickers from a custom file
"""

import sys
import time
import warnings

from scoring import (
    analyze_eps_growth,
    analyze_roe,
    analyze_free_cash_flow,
    analyze_balance_sheet,
    analyze_dividends,
    calculate_dcf_intrinsic_value,
    analyze_revenue_growth,
)
from utils.data import load_tickers, get_financial_data
from utils.formatting import print_results, print_summary_table, flatten_result
from utils.database import save_scores
from utils.cache import enable_cache
from utils.config import get_weights

warnings.filterwarnings("ignore")


def _compute_score(eps, roe, fcf, bal, div, dcf, rev=None):
    """Compute weighted Buffett score from sub-scores."""
    w = get_weights()
    rev_score = rev.get("revenue_score", 0) if rev else 0
    return round(
        eps["eps_score"] * w["eps"]
        + roe["roe_score"] * w["roe"]
        + fcf["fcf_score"] * w["fcf"]
        + bal["balance_score"] * w["balance"]
        + div["dividend_score"] * w["dividend"]
        + (25 if dcf["undervalued"] else 0) * w["dcf"]
        + rev_score * w.get("revenue", 0),
        1,
    )


def screen_stock(ticker_symbol, index, total):
    """Screen a single stock against all Buffett criteria."""
    print(f"  [{index}/{total}] Analyzing {ticker_symbol}...")

    data = get_financial_data(ticker_symbol)
    if data is None:
        return None

    eps = analyze_eps_growth(data)
    roe = analyze_roe(data)
    fcf = analyze_free_cash_flow(data)
    bal = analyze_balance_sheet(data)
    div = analyze_dividends(data)
    dcf = calculate_dcf_intrinsic_value(data, fcf)
    rev = analyze_revenue_growth(data)

    total_score = _compute_score(eps, roe, fcf, bal, div, dcf, rev)

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
        "balance_analysis": bal,
        "dividend_analysis": div,
        "dcf_analysis": dcf,
        "revenue_analysis": rev,
        "buffett_score": total_score,
    }


def main():
    # Parse flags
    export_csv = False
    export_xlsx = False
    summary_only = False
    remaining_args = []
    for arg in sys.argv[1:]:
        if arg == "--csv":
            export_csv = True
        elif arg in ("--xlsx", "--excel"):
            export_xlsx = True
        elif arg == "--summary":
            summary_only = True
        else:
            remaining_args.append(arg)

    if remaining_args:
        arg = remaining_args[0]
        if arg.endswith(".txt") or arg.endswith(".csv"):
            candidates = load_tickers(arg)
        else:
            candidates = [t.upper().strip() for t in remaining_args if t.strip()]
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

    enable_cache()

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

    if summary_only:
        flat = [flatten_result(r) for r in results]
        print_summary_table(flat, title="BUFFETT SCORE SUMMARY")
    else:
        print_results(results)

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

    # Export if requested
    if export_csv:
        from utils.export import export_csv as _export_csv
        _export_csv(results)
    if export_xlsx:
        from utils.export import export_excel
        export_excel(results)


if __name__ == "__main__":
    main()
