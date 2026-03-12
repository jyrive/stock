"""Benchmark comparison — total return for major indices.

Fetches total-return data (price appreciation + dividends) for market
benchmarks and computes comparative metrics against a simulated portfolio.

Supported benchmarks:
    SPY   — S&P 500 (US large-cap)
    QQQ   — Nasdaq-100 (US tech)
    VT    — Vanguard Total World Stock (global)
    IWDA  — iShares Core MSCI World (non-US global, European listing)
    AGG   — iShares Core US Aggregate Bond
"""

from datasources.market import get_price_history, get_dividends
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

DEFAULT_BENCHMARKS = ["SPY", "QQQ", "VT"]


def get_total_return_series(
    symbol: str,
    start_date: str,
    end_date: Optional[str] = None,
) -> List[dict]:
    """Fetch adjusted close series for a symbol (accounts for dividends + splits).

    Returns list of {date, price, total_return_pct} dicts.
    """
    try:
        hist = get_price_history(symbol, start=start_date, end=end_date)

        if hist is None or hist.empty or len(hist) < 2:
            return []

        base_price = float(hist["Close"].iloc[0])
        series = []
        for idx, row in hist.iterrows():
            dt = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            price = float(row["Close"])
            total_return = (price / base_price - 1) * 100
            series.append({
                "date": dt,
                "price": price,
                "total_return_pct": round(total_return, 4),
            })
        return series
    except Exception as e:
        print(f"  Warning: Could not fetch benchmark {symbol}: {e}")
        return []


def get_benchmark_returns(
    benchmarks: Optional[List[str]] = None,
    start_date: str = None,
    end_date: Optional[str] = None,
) -> Dict[str, dict]:
    """Fetch total-return summary for multiple benchmarks.

    Returns {symbol: {total_return_pct, annualized_pct, max_drawdown_pct, series}}.
    """
    benchmarks = benchmarks or DEFAULT_BENCHMARKS
    results = {}

    for sym in benchmarks:
        series = get_total_return_series(sym, start_date, end_date)
        if not series:
            results[sym] = {
                "total_return_pct": None,
                "annualized_pct": None,
                "max_drawdown_pct": None,
                "series": [],
            }
            continue

        total_return = series[-1]["total_return_pct"]

        # Annualize
        start = datetime.strptime(series[0]["date"], "%Y-%m-%d")
        end = datetime.strptime(series[-1]["date"], "%Y-%m-%d")
        days = (end - start).days
        years = days / 365.25 if days > 0 else 1
        start_price = series[0]["price"]
        end_price = series[-1]["price"]
        annualized = ((end_price / start_price) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Max drawdown
        peak = series[0]["price"]
        max_dd = 0
        for s in series:
            if s["price"] > peak:
                peak = s["price"]
            dd = (peak - s["price"]) / peak
            if dd > max_dd:
                max_dd = dd

        results[sym] = {
            "total_return_pct": round(total_return, 2),
            "annualized_pct": round(annualized, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "series": series,
        }

    return results


def compute_alpha(portfolio_return: float, benchmark_returns: Dict[str, dict]) -> Dict[str, float]:
    """Compute alpha (excess return) vs each benchmark."""
    alpha = {}
    for sym, data in benchmark_returns.items():
        if data["total_return_pct"] is not None:
            alpha[sym] = round(portfolio_return - data["total_return_pct"], 2)
        else:
            alpha[sym] = None
    return alpha


def get_dividends_between(symbol: str, start_date: str, end_date: str) -> float:
    """Get total dividends per share paid between two dates."""
    try:
        divs = get_dividends(symbol)
        if divs is None or divs.empty:
            return 0.0
        filtered = divs[(divs.index >= start_date) & (divs.index <= end_date)]
        return float(filtered.sum())
    except Exception:
        return 0.0


def print_benchmark_comparison(
    portfolio_metrics: dict,
    benchmark_returns: Dict[str, dict],
    alpha: Dict[str, float],
):
    """Print a formatted comparison table."""
    print("\n  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║           PORTFOLIO vs BENCHMARKS                          ║")
    print("  ╚══════════════════════════════════════════════════════════════╝\n")

    # Header
    print(f"  {'':20s} {'Total Ret':>10s} {'Annual':>10s} {'Max DD':>10s} {'Alpha':>10s}")
    print(f"  {'─' * 60}")

    # Portfolio row
    tr = portfolio_metrics.get("total_return_pct", 0)
    ar = portfolio_metrics.get("annualized_return_pct", 0)
    dd = portfolio_metrics.get("max_drawdown_pct", 0)
    _color = "\033[92m" if tr >= 0 else "\033[91m"
    print(f"  {'📊 Portfolio':20s} {_color}{tr:>+9.1f}%\033[0m {ar:>+9.1f}% {dd:>9.1f}%  {'':>10s}")

    # Benchmark rows
    for sym, data in benchmark_returns.items():
        if data["total_return_pct"] is None:
            print(f"  {sym:20s} {'N/A':>10s}")
            continue
        btr = data["total_return_pct"]
        bar = data["annualized_pct"]
        bdd = data["max_drawdown_pct"]
        a = alpha.get(sym)
        alpha_str = f"{a:>+9.1f}%" if a is not None else "N/A"
        _color = "\033[92m" if btr >= 0 else "\033[91m"
        print(f"  {sym:20s} {_color}{btr:>+9.1f}%\033[0m {bar:>+9.1f}% {bdd:>9.1f}% {alpha_str}")

    print()
