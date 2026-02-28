"""Calculate total returns (price + dividends) for positions vs SPY benchmark.

Uses yfinance adjusted history for accurate total return calculations.
"""

import yfinance as yf
from datetime import date, datetime


def _get_price(symbol):
    """Get current price for a symbol."""
    try:
        t = yf.Ticker(symbol)
        info = t.info
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        return None


def _get_dividends_since(symbol, since_date):
    """Get total dividends per share paid since a date."""
    try:
        t = yf.Ticker(symbol)
        divs = t.dividends
        if divs.empty:
            return 0.0
        # Filter to dividends after the buy date
        since = datetime.strptime(since_date, "%Y-%m-%d")
        # Dividends index is timezone-aware, convert
        filtered = divs[divs.index >= since.strftime("%Y-%m-%d")]
        return float(filtered.sum())
    except Exception:
        return 0.0


def _get_total_return(symbol, start_date):
    """Get total return % for a symbol since start_date using adjusted history.

    Returns (total_return_pct, price_only) or (None, None) on failure.
    """
    try:
        t = yf.Ticker(symbol)
        hist = t.history(start=start_date)
        if hist.empty or len(hist) < 2:
            return None, None

        # yfinance .history() Close is adjusted for splits and dividends
        start_price = float(hist["Close"].iloc[0])
        end_price = float(hist["Close"].iloc[-1])

        # Total return from adjusted close
        total_return = (end_price / start_price - 1) * 100

        # For price-only return, we need to add back dividends
        divs_total = float(hist["Dividends"].sum())
        price_return = ((end_price - divs_total) / start_price - 1) * 100 if divs_total else total_return

        return total_return, price_return
    except Exception:
        return None, None


def calculate_portfolio_returns(positions):
    """Calculate returns for all positions with SPY benchmark.

    Args:
        positions: list from get_positions() — each has symbol, shares, avg_cost, first_buy_date

    Returns:
        {
            "positions": [{symbol, shares, avg_cost, current_price, total_cost,
                           current_value, dividends, price_pnl, total_pnl,
                           price_return_pct, total_return_pct, holding_days}],
            "portfolio": {total_cost, current_value, total_dividends,
                          price_pnl, total_pnl, price_return_pct, total_return_pct},
            "benchmark": {symbol, return_pct, start_date},
            "alpha": float  # portfolio total return - SPY total return
        }
    """
    if not positions:
        return None

    results = []
    earliest_date = None

    for pos in positions:
        sym = pos["symbol"]
        shares = pos["shares"]
        avg_cost = pos["avg_cost"]
        buy_date = pos["first_buy_date"]

        if earliest_date is None or buy_date < earliest_date:
            earliest_date = buy_date

        current_price = _get_price(sym)
        dividends_per_share = _get_dividends_since(sym, buy_date)

        if current_price is None:
            results.append({
                "symbol": sym,
                "shares": shares,
                "avg_cost": avg_cost,
                "current_price": None,
                "total_cost": shares * avg_cost,
                "current_value": None,
                "dividends": None,
                "price_pnl": None,
                "total_pnl": None,
                "price_return_pct": None,
                "total_return_pct": None,
                "holding_days": (date.today() - datetime.strptime(buy_date, "%Y-%m-%d").date()).days,
            })
            continue

        total_cost = shares * avg_cost
        current_value = shares * current_price
        total_dividends = shares * dividends_per_share

        price_pnl = current_value - total_cost
        total_pnl = price_pnl + total_dividends

        price_return_pct = (current_price / avg_cost - 1) * 100
        total_return_pct = ((current_price + dividends_per_share) / avg_cost - 1) * 100

        holding_days = (date.today() - datetime.strptime(buy_date, "%Y-%m-%d").date()).days

        results.append({
            "symbol": sym,
            "shares": shares,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "total_cost": total_cost,
            "current_value": current_value,
            "dividends": total_dividends,
            "price_pnl": price_pnl,
            "total_pnl": total_pnl,
            "price_return_pct": price_return_pct,
            "total_return_pct": total_return_pct,
            "holding_days": holding_days,
        })

    # Portfolio totals
    valid = [r for r in results if r["current_price"] is not None]
    total_cost = sum(r["total_cost"] for r in valid)
    current_value = sum(r["current_value"] for r in valid)
    total_dividends = sum(r["dividends"] for r in valid)
    price_pnl = current_value - total_cost
    total_pnl = price_pnl + total_dividends

    portfolio_summary = {
        "total_cost": total_cost,
        "current_value": current_value,
        "total_dividends": total_dividends,
        "price_pnl": price_pnl,
        "total_pnl": total_pnl,
        "price_return_pct": (price_pnl / total_cost * 100) if total_cost else 0,
        "total_return_pct": (total_pnl / total_cost * 100) if total_cost else 0,
    }

    # SPY benchmark (total return over same period)
    benchmark = {"symbol": "SPY", "return_pct": None, "start_date": earliest_date}
    if earliest_date:
        spy_return, _ = _get_total_return("SPY", earliest_date)
        benchmark["return_pct"] = spy_return

    alpha = None
    if benchmark["return_pct"] is not None and portfolio_summary["total_return_pct"]:
        alpha = portfolio_summary["total_return_pct"] - benchmark["return_pct"]

    return {
        "positions": results,
        "portfolio": portfolio_summary,
        "benchmark": benchmark,
        "alpha": alpha,
    }
