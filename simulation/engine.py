"""Portfolio simulator — manages virtual cash, holdings, and transaction log.

Supports both forward auto-trading and historical backtesting.
Keeps a completely separate portfolio from the manual paper-trading
system (utils/positions.py), so experiments never interfere with your
real tracking.

Key concepts:
    SimPortfolio  — in-memory portfolio state (cash, holdings, log)
    SimTransaction — one buy/sell event with full context
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import math


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class SimTransaction:
    """A single simulated buy or sell."""
    date: str                  # ISO date string
    symbol: str
    action: str                # "BUY" or "SELL"
    shares: float
    price: float
    value: float               # shares * price
    verdict: str               # verdict at time of trade
    fund_score: Optional[float] = None
    tech_score: Optional[float] = None
    macro_score: Optional[float] = None
    reason: str = ""           # human-readable reason
    dividends_collected: float = 0.0  # dividends received while holding


@dataclass
class Holding:
    """An open position in the simulated portfolio."""
    symbol: str
    shares: float
    avg_cost: float
    total_cost: float
    first_buy_date: str
    dividends_collected: float = 0.0


@dataclass
class SimPortfolio:
    """Complete simulation state."""
    name: str = "simulation"
    starting_cash: float = 100_000.0
    cash: float = 100_000.0
    holdings: Dict[str, Holding] = field(default_factory=dict)
    transactions: List[SimTransaction] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    # Configuration
    max_position_pct: float = 0.10     # max 10% of portfolio per stock
    max_positions: int = 20            # max 20 simultaneous holdings
    commission: float = 0.0            # per-trade commission
    stop_loss_pct: float = 0.20        # sell if position drops 20%
    take_profit_pct: float = 0.0       # 0 = disabled
    rebalance_on_sell: bool = False     # redistribute cash after sells

    @property
    def total_value(self) -> float:
        """Total portfolio value (cash + holdings at cost)."""
        return self.cash + sum(h.total_cost for h in self.holdings.values())

    def portfolio_value_at_prices(self, prices: Dict[str, float]) -> float:
        """Total portfolio value at given market prices."""
        holdings_value = sum(
            h.shares * prices.get(h.symbol, h.avg_cost)
            for h in self.holdings.values()
        )
        return self.cash + holdings_value

    def holding_weight(self, symbol: str, prices: Dict[str, float]) -> float:
        """Current weight of a holding as fraction of total portfolio."""
        total = self.portfolio_value_at_prices(prices)
        if total <= 0 or symbol not in self.holdings:
            return 0.0
        h = self.holdings[symbol]
        return (h.shares * prices.get(symbol, h.avg_cost)) / total


# ── Position sizing ──────────────────────────────────────────────────

def compute_position_size(
    portfolio: SimPortfolio,
    symbol: str,
    price: float,
    verdict_pct_lo: float,
    verdict_pct_hi: float,
    macro_multiplier: float,
    prices: Dict[str, float],
) -> int:
    """Determine how many shares to buy.

    1. Target allocation = midpoint of verdict range * macro multiplier
    2. Cap at max_position_pct of portfolio value
    3. Cap at available cash
    4. Round down to whole shares

    Returns number of shares (0 if trade should not be made).
    """
    if price <= 0:
        return 0

    total_value = portfolio.portfolio_value_at_prices(prices)

    # Target: midpoint of verdict range, adjusted by macro
    target_pct = ((verdict_pct_lo + verdict_pct_hi) / 2) / 100.0 * macro_multiplier

    # Already-held weight
    current_weight = portfolio.holding_weight(symbol, prices)
    additional_pct = max(0, min(target_pct, portfolio.max_position_pct) - current_weight)

    if additional_pct <= 0.005:  # less than 0.5% — not worth trading
        return 0

    target_dollars = total_value * additional_pct
    target_dollars = min(target_dollars, portfolio.cash - portfolio.commission)

    if target_dollars < price:
        return 0

    shares = int(target_dollars / price)
    return shares


# ── Trade execution ──────────────────────────────────────────────────

def execute_buy(
    portfolio: SimPortfolio,
    symbol: str,
    shares: int,
    price: float,
    trade_date: str,
    verdict: str,
    fund_score: Optional[float] = None,
    tech_score: Optional[float] = None,
    macro_score: Optional[float] = None,
    reason: str = "",
) -> Optional[SimTransaction]:
    """Execute a buy and update portfolio state."""
    if shares <= 0 or price <= 0:
        return None

    cost = shares * price + portfolio.commission
    if cost > portfolio.cash:
        # Reduce shares to fit
        shares = int((portfolio.cash - portfolio.commission) / price)
        if shares <= 0:
            return None
        cost = shares * price + portfolio.commission

    portfolio.cash -= cost

    if symbol in portfolio.holdings:
        h = portfolio.holdings[symbol]
        new_total_cost = h.total_cost + shares * price
        new_shares = h.shares + shares
        h.avg_cost = new_total_cost / new_shares
        h.total_cost = new_total_cost
        h.shares = new_shares
    else:
        portfolio.holdings[symbol] = Holding(
            symbol=symbol,
            shares=shares,
            avg_cost=price,
            total_cost=shares * price,
            first_buy_date=trade_date,
        )

    txn = SimTransaction(
        date=trade_date,
        symbol=symbol,
        action="BUY",
        shares=shares,
        price=price,
        value=shares * price,
        verdict=verdict,
        fund_score=fund_score,
        tech_score=tech_score,
        macro_score=macro_score,
        reason=reason,
    )
    portfolio.transactions.append(txn)
    return txn


def execute_sell(
    portfolio: SimPortfolio,
    symbol: str,
    shares: float,
    price: float,
    trade_date: str,
    verdict: str,
    fund_score: Optional[float] = None,
    tech_score: Optional[float] = None,
    macro_score: Optional[float] = None,
    reason: str = "",
) -> Optional[SimTransaction]:
    """Execute a sell and update portfolio state."""
    if symbol not in portfolio.holdings:
        return None

    h = portfolio.holdings[symbol]
    sell_shares = min(shares, h.shares)
    if sell_shares <= 0:
        return None

    proceeds = sell_shares * price - portfolio.commission
    portfolio.cash += proceeds

    # Reduce position
    cost_removed = sell_shares * h.avg_cost
    h.shares -= sell_shares
    h.total_cost -= cost_removed

    txn = SimTransaction(
        date=trade_date,
        symbol=symbol,
        action="SELL",
        shares=sell_shares,
        price=price,
        value=sell_shares * price,
        verdict=verdict,
        fund_score=fund_score,
        tech_score=tech_score,
        macro_score=macro_score,
        reason=reason,
        dividends_collected=h.dividends_collected,
    )
    portfolio.transactions.append(txn)

    # Remove if fully sold
    if h.shares < 0.001:
        del portfolio.holdings[symbol]

    return txn


def execute_sell_all(
    portfolio: SimPortfolio,
    symbol: str,
    price: float,
    trade_date: str,
    verdict: str,
    fund_score: Optional[float] = None,
    tech_score: Optional[float] = None,
    macro_score: Optional[float] = None,
    reason: str = "",
) -> Optional[SimTransaction]:
    """Sell entire position in a symbol."""
    if symbol not in portfolio.holdings:
        return None
    return execute_sell(
        portfolio, symbol, portfolio.holdings[symbol].shares,
        price, trade_date, verdict, fund_score, tech_score, macro_score, reason,
    )


# ── Dividend crediting ───────────────────────────────────────────────

def credit_dividends(portfolio: SimPortfolio, symbol: str, div_per_share: float, ex_date: str):
    """Credit dividends to a holding (adds to cash and tracks total)."""
    if symbol not in portfolio.holdings or div_per_share <= 0:
        return 0.0
    h = portfolio.holdings[symbol]
    amount = h.shares * div_per_share
    portfolio.cash += amount
    h.dividends_collected += amount
    return amount


# ── Snapshot / equity curve ──────────────────────────────────────────

def record_snapshot(portfolio: SimPortfolio, snap_date: str, prices: Dict[str, float]):
    """Record a portfolio snapshot for the equity curve."""
    total = portfolio.portfolio_value_at_prices(prices)
    portfolio.equity_curve.append({
        "date": snap_date,
        "total_value": total,
        "cash": portfolio.cash,
        "holdings_value": total - portfolio.cash,
        "num_holdings": len(portfolio.holdings),
    })


# ── Stop-loss / take-profit checks ──────────────────────────────────

def check_exit_signals(
    portfolio: SimPortfolio,
    prices: Dict[str, float],
) -> List[Tuple[str, str]]:
    """Check all holdings for stop-loss or take-profit triggers.

    Returns list of (symbol, reason) tuples for positions to sell.
    """
    exits = []
    for symbol, h in portfolio.holdings.items():
        price = prices.get(symbol)
        if price is None:
            continue

        pnl_pct = (price / h.avg_cost - 1) if h.avg_cost > 0 else 0

        if portfolio.stop_loss_pct > 0 and pnl_pct <= -portfolio.stop_loss_pct:
            exits.append((symbol, f"Stop-loss triggered ({pnl_pct:+.1%} vs -{portfolio.stop_loss_pct:.0%})"))

        if portfolio.take_profit_pct > 0 and pnl_pct >= portfolio.take_profit_pct:
            exits.append((symbol, f"Take-profit triggered ({pnl_pct:+.1%} vs +{portfolio.take_profit_pct:.0%})"))

    return exits


# ── Performance metrics ──────────────────────────────────────────────

def compute_metrics(portfolio: SimPortfolio) -> dict:
    """Compute performance metrics from the equity curve.

    Returns dict with total_return, annualized_return, max_drawdown,
    sharpe_ratio, win_rate, total_trades, total_dividends.
    """
    curve = portfolio.equity_curve
    if not curve:
        return {}

    start_val = portfolio.starting_cash
    end_val = curve[-1]["total_value"]
    total_return = (end_val / start_val - 1) * 100

    # Time span
    start_date = datetime.strptime(curve[0]["date"], "%Y-%m-%d")
    end_date = datetime.strptime(curve[-1]["date"], "%Y-%m-%d")
    days = (end_date - start_date).days
    years = days / 365.25 if days > 0 else 1

    annualized = ((end_val / start_val) ** (1 / years) - 1) * 100 if years > 0 else 0

    # Max drawdown
    peak = start_val
    max_dd = 0
    for snap in curve:
        val = snap["total_value"]
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (using weekly returns if enough data)
    sharpe = None
    if len(curve) >= 5:
        values = [s["total_value"] for s in curve]
        returns = [(values[i] / values[i - 1] - 1) for i in range(1, len(values))]
        if returns:
            import numpy as np
            mean_ret = np.mean(returns)
            std_ret = np.std(returns, ddof=1)
            if std_ret > 0:
                # Annualize: assume weekly snapshots
                periods_per_year = max(1, 365.25 / max(1, days / len(returns)))
                sharpe = (mean_ret / std_ret) * math.sqrt(periods_per_year)

    # Win rate (from closed trades)
    buys = {}
    wins = 0
    losses = 0
    total_dividends = 0.0
    for txn in portfolio.transactions:
        if txn.action == "BUY":
            buys.setdefault(txn.symbol, []).append(txn)
        elif txn.action == "SELL":
            # Check if profitable (including dividends)
            total_sell = txn.value + txn.dividends_collected
            cost_basis = txn.shares * (buys.get(txn.symbol, [{}])[0].price if buys.get(txn.symbol) else txn.price)
            if total_sell >= cost_basis:
                wins += 1
            else:
                losses += 1
            total_dividends += txn.dividends_collected

    # Add uncollected dividends from current holdings
    for h in portfolio.holdings.values():
        total_dividends += h.dividends_collected

    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else None

    return {
        "total_return_pct": round(total_return, 2),
        "annualized_return_pct": round(annualized, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
        "win_rate_pct": round(win_rate, 1) if win_rate is not None else None,
        "total_trades": len(portfolio.transactions),
        "closed_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "total_dividends": round(total_dividends, 2),
        "final_value": round(end_val, 2),
        "starting_cash": round(start_val, 2),
        "days": days,
        "years": round(years, 2),
    }
