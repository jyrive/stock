"""backtest command — long-term investor strategy replay.

Philosophy:
    Fundamentals decide WHAT to buy and WHEN to sell.
    Technical analysis boosts ENTRY CONFIDENCE (sizing, not yes/no).
    Macro is super important — drives overall allocation sizing.
    Hold through technical weakness (you're not a trader).
    Sell only when fundamentals break or stop-loss triggers.

Walk through history week-by-week, apply the rules, track results.
Reports monthly/yearly performance in both USD and EUR.

Limitations:
    Fundamental scores use CURRENT data (look-ahead bias).
    In reality scores would be computed from each quarter's data.
    Technical + macro scores are historically accurate.

Usage:
    python stock.py backtest AAPL MSFT --period 2y
    python stock.py backtest --watchlist --period 1y
    python stock.py backtest --portfolio --period 3y
    python stock.py backtest --all --period 2y --cash 50000
    python stock.py backtest --runs                    List past runs
    python stock.py backtest --show 3                  Show run #3
"""

import sys
import math
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from datasources.market import get_price_history, get_macro_history
from utils.config import config, enable_cache

# ═══════════════════════════════════════════════════════════════════════
#  Argument parsing
# ═══════════════════════════════════════════════════════════════════════

def _parse_period(period_str):
    """Parse '1y', '2y', '6m', '90d' or 'YYYY-MM-DD' → ISO start date."""
    period_str = period_str.lower().strip()
    today = date.today()

    if period_str.endswith("y"):
        years = int(period_str[:-1])
        start = today.replace(year=today.year - years)
    elif period_str.endswith("m"):
        months = int(period_str[:-1])
        year = today.year + (today.month - months - 1) // 12
        month = (today.month - months - 1) % 12 + 1
        start = today.replace(year=year, month=month)
    elif period_str.endswith("d"):
        days = int(period_str[:-1])
        start = today - timedelta(days=days)
    else:
        try:
            start = datetime.strptime(period_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"  Invalid period: {period_str}. Use '1y', '6m', '90d', or 'YYYY-MM-DD'.")
            return None
    return start.isoformat()

def _resolve_tickers(args):
    """Resolve ticker arguments and flags."""
    from utils.lists import portfolio_list, watchlist_list

    tickers = []
    flags = {}
    i = 0
    while i < len(args):
        arg = args[i]
        low = arg.lower()

        if low in ("--portfolio", "-p"):
            tickers.extend(portfolio_list())
        elif low in ("--watchlist", "-w"):
            tickers.extend(watchlist_list())
        elif low in ("--all", "-a"):
            tickers.extend(portfolio_list())
            tickers.extend(watchlist_list())
        elif low == "--period" and i + 1 < len(args):
            flags["period"] = args[i + 1]; i += 1
        elif low == "--cash" and i + 1 < len(args):
            flags["cash"] = float(args[i + 1]); i += 1
        elif low == "--runs":
            flags["show_runs"] = True
        elif low == "--show" and i + 1 < len(args):
            flags["show_run_id"] = int(args[i + 1]); i += 1
        elif low == "--weekly":
            flags["frequency"] = "weekly"
        elif low == "--monthly":
            flags["frequency"] = "monthly"
        elif low == "--no-html":
            flags["html"] = False
        elif not arg.startswith("--"):
            tickers.append(arg.upper().strip())
        i += 1

    seen = set()
    unique = []
    for t in tickers:
        t = t.upper()
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique, flags

# ═══════════════════════════════════════════════════════════════════════
#  Data fetching
# ═══════════════════════════════════════════════════════════════════════

def _fetch_historical_data(tickers, start_date, end_date=None):
    """Fetch full price+dividend history for all tickers."""
    histories = {}
    for sym in tickers:
        try:
            hist = get_price_history(sym, start=start_date, end=end_date)
            if hist is not None and not hist.empty:
                histories[sym] = hist
        except Exception as e:
            print(f"  Warning: could not fetch {sym}: {e}")
        time.sleep(0.1)
    return histories

def _fetch_eurusd(start_date, end_date=None):
    """Fetch EUR/USD exchange rate history.

    Returns {date_str: rate} where rate = USD per 1 EUR.
    To convert USD→EUR: EUR_amount = USD_amount / rate.
    """
    try:
        hist = get_price_history("EURUSD=X", start=start_date, end=end_date)
        if hist is None or hist.empty:
            return {}
        rates = {}
        for idx, row in hist.iterrows():
            d = idx.strftime("%Y-%m-%d")
            rates[d] = float(row["Close"])
        return rates
    except Exception:
        return {}

def _get_eur_rate(rates_dict, target_date, fallback=1.10):
    """Get EUR/USD rate for a date (or nearest prior date)."""
    if not rates_dict:
        return fallback
    for offset in range(11):
        d = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=offset)).strftime("%Y-%m-%d")
        if d in rates_dict:
            return rates_dict[d]
    return fallback

def _usd_to_eur(usd, rate):
    """Convert USD to EUR.  rate = USD per 1 EUR."""
    return usd / rate if rate > 0 else usd

# ═══════════════════════════════════════════════════════════════════════
#  Scoring — reuses real modules
# ═══════════════════════════════════════════════════════════════════════

def _compute_technical(closes_array):
    """Compute technical score from numpy array of closes."""
    if len(closes_array) < 30:
        return None
    from analysis.technical import rsi, sma, bollinger_bands, macd, compute_tech_score

    current = float(closes_array[-1])
    ta = {}
    ta["rsi_14"] = rsi(closes_array)

    sma200 = sma(closes_array, 200)
    ta["price_vs_sma200_pct"] = (current / sma200 - 1) * 100 if sma200 and sma200 > 0 else None

    bb_l, bb_m, bb_u = bollinger_bands(closes_array)
    ta["bb_position"] = (current - bb_l) / (bb_u - bb_l) if bb_l is not None and bb_u and bb_u > bb_l else None

    lookback = min(252, len(closes_array))
    recent = closes_array[-lookback:]
    h52, l52 = float(np.max(recent)), float(np.min(recent))
    ta["week52_position"] = (current - l52) / (h52 - l52) if h52 > l52 else None

    ta["macd"] = macd(closes_array)
    return compute_tech_score(ta)

def _compute_macro(hist_date):
    """Compute macro score at a historical date using VIX + S&P 500."""
    from analysis.macro import score_vix, score_sp500_vs_200, score_sp500_52w

    try:
        start = (datetime.strptime(hist_date, "%Y-%m-%d") - timedelta(days=300)).strftime("%Y-%m-%d")
        end = (datetime.strptime(hist_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        vix_hist = get_macro_history("^VIX", start=start, end=end)
        vix_current = float(vix_hist["Close"].iloc[-1]) if vix_hist is not None and not vix_hist.empty else None
        vix_score = score_vix(vix_current)

        sp_hist = get_macro_history("^GSPC", start=start, end=end)
        sp_pct, sp_52w_pos = None, None
        if sp_hist is not None and not sp_hist.empty:
            sp_closes = sp_hist["Close"].values.astype(float)
            sp_current = float(sp_closes[-1])
            if len(sp_closes) >= 200:
                sp_pct = (sp_current / float(np.mean(sp_closes[-200:])) - 1) * 100
            lb = min(252, len(sp_closes))
            sp_h, sp_l = float(np.max(sp_closes[-lb:])), float(np.min(sp_closes[-lb:]))
            if sp_h > sp_l:
                sp_52w_pos = (sp_current - sp_l) / (sp_h - sp_l) * 100

        raw = vix_score + score_sp500_vs_200(sp_pct) + score_sp500_52w(sp_52w_pos) + 12 + 7
        return min(100, max(0, raw))
    except Exception:
        return 50

# ═══════════════════════════════════════════════════════════════════════
#  Long-term investor strategy
# ═══════════════════════════════════════════════════════════════════════

def _investor_should_buy(fund_score, tech_score, macro_score, params):
    """Long-term investor buy logic.

    Decision tree:
      1. Fundamentals >= threshold?  → ELIGIBLE to buy
      2. If eligible, HOW MUCH:
         - Base allocation from params
         - Tech boosts/reduces sizing (confidence layer)
         - Macro scales overall (environment layer)

    Returns (should_buy, target_pct, reason)
    """
    threshold = params.get("fund_buy_threshold", 45)
    if fund_score is None or fund_score < threshold:
        return False, 0, ""

    base_pct = params.get("base_position_pct", 0.06)
    tech_inf = params.get("tech_influence", 0.3)
    macro_inf = params.get("macro_influence", 0.5)

    # Technical confidence factor: 0.7 → 1.3
    if tech_score is not None:
        tech_factor = 0.7 + 0.6 * max(0, min(1, (tech_score - 20) / 60))
    else:
        tech_factor = 1.0
    tech_factor = 1.0 + (tech_factor - 1.0) * tech_inf

    # Macro factor: 0.5 → 1.25
    if macro_score is not None:
        if macro_score >= 70:
            macro_factor = 1.25
        elif macro_score >= 50:
            macro_factor = 1.0
        elif macro_score >= 35:
            macro_factor = 0.75
        else:
            macro_factor = 0.5
    else:
        macro_factor = 1.0
    macro_factor = 1.0 + (macro_factor - 1.0) * macro_inf

    target = base_pct * tech_factor * macro_factor
    target = max(0.02, min(target, params.get("max_position_pct", 0.10)))

    parts = [f"Fund {fund_score:.0f}≥{threshold}"]
    if tech_score is not None:
        parts.append(f"Tech {tech_score:.0f}→{tech_factor:.2f}x")
    if macro_score is not None:
        parts.append(f"Macro {macro_score:.0f}→{macro_factor:.2f}x")
    return True, target, " · ".join(parts)

def _investor_should_sell(fund_score, holding, current_price, params):
    """Long-term investor sell logic.

    ONLY sell when:
      1. Fundamentals deteriorate below sell threshold
      2. Stop-loss triggers (crisis protection)

    Do NOT sell because:
      - Technical indicators look weak
      - Short-term market dip
    """
    sell_threshold = params.get("fund_sell_threshold", 30)
    if fund_score is not None and fund_score < sell_threshold:
        return True, f"Fundamentals {fund_score:.0f} < {sell_threshold}"

    stop_loss = params.get("stop_loss_pct", 0.25)
    if stop_loss > 0 and holding and current_price and holding["avg_cost"] > 0:
        pnl = current_price / holding["avg_cost"] - 1
        if pnl <= -stop_loss:
            return True, f"Stop-loss ({pnl:+.1%} vs -{stop_loss:.0%})"

    return False, ""

# ═══════════════════════════════════════════════════════════════════════
#  Inline portfolio tracker
# ═══════════════════════════════════════════════════════════════════════

def _make_portfolio(cash):
    """Create a minimal portfolio dict (no dataclass dependencies)."""
    return {
        "starting_cash": cash,
        "cash": cash,
        "holdings": {},       # symbol → {shares, avg_cost, total_cost, first_buy, dividends}
        "transactions": [],   # list of dicts
        "equity_curve": [],   # list of {date, value_usd, cash, n_holdings}
        # Friction cost tracking
        "total_spread_cost": 0.0,      # cumulative spread/slippage
        "total_commission": 0.0,        # cumulative broker fees
        "total_dividend_tax": 0.0,      # cumulative dividend withholding
        "total_capital_gains_tax": 0.0, # cumulative realized gains tax
    }

def _portfolio_value(port, prices):
    hv = sum(h["shares"] * prices.get(sym, h["avg_cost"]) for sym, h in port["holdings"].items())
    return port["cash"] + hv

def _portfolio_weight(port, sym, prices):
    total = _portfolio_value(port, prices)
    if total <= 0 or sym not in port["holdings"]:
        return 0
    h = port["holdings"][sym]
    return h["shares"] * prices.get(sym, 0) / total

def _buy(port, sym, shares, price, trade_date, reason="", params=None):
    # Apply spread: you buy at ask (slightly above mid)
    spread_pct = (params or {}).get("spread_pct", 0.10) / 100
    commission = (params or {}).get("commission_eur", 0.0)
    effective_price = price * (1 + spread_pct)
    cost = shares * effective_price
    total_cost_with_comm = cost + commission
    if total_cost_with_comm > port["cash"]:
        shares = int((port["cash"] - commission) / effective_price)
        if shares <= 0:
            return None
        cost = shares * effective_price
        total_cost_with_comm = cost + commission
    spread_cost = shares * price * spread_pct
    port["cash"] -= total_cost_with_comm
    port["total_spread_cost"] += spread_cost
    port["total_commission"] += commission
    if sym in port["holdings"]:
        h = port["holdings"][sym]
        new_total = h["total_cost"] + cost
        new_shares = h["shares"] + shares
        h["avg_cost"] = new_total / new_shares
        h["total_cost"] = new_total
        h["shares"] = new_shares
    else:
        port["holdings"][sym] = {
            "shares": shares, "avg_cost": effective_price, "total_cost": cost,
            "first_buy": trade_date, "dividends": 0.0,
        }
    txn = {"date": trade_date, "symbol": sym, "action": "BUY",
           "shares": shares, "price": effective_price, "value_usd": cost,
           "spread_cost": round(spread_cost, 2),
           "commission": round(commission, 2), "reason": reason}
    port["transactions"].append(txn)
    return txn

def _sell_all(port, sym, price, trade_date, reason="", params=None):
    if sym not in port["holdings"]:
        return None
    h = port["holdings"][sym]
    # Apply spread: you sell at bid (slightly below mid)
    spread_pct = (params or {}).get("spread_pct", 0.10) / 100
    commission = (params or {}).get("commission_eur", 0.0)
    cg_tax_pct = (params or {}).get("capital_gains_tax_pct", 30.0) / 100
    effective_price = price * (1 - spread_pct)
    proceeds = h["shares"] * effective_price
    spread_cost = h["shares"] * price * spread_pct
    # Capital gains tax (only on profit, not on losses)
    gain = proceeds - h["total_cost"]
    cg_tax = max(0, gain * cg_tax_pct)  # no tax on losses
    net_proceeds = proceeds - cg_tax - commission
    port["cash"] += net_proceeds
    port["total_spread_cost"] += spread_cost
    port["total_commission"] += commission
    port["total_capital_gains_tax"] += cg_tax
    pnl_pct = (effective_price / h["avg_cost"] - 1) * 100 if h["avg_cost"] > 0 else 0
    txn = {"date": trade_date, "symbol": sym, "action": "SELL",
           "shares": h["shares"], "price": effective_price, "value_usd": net_proceeds,
           "reason": reason, "pnl_pct": pnl_pct,
           "dividends": h["dividends"],
           "spread_cost": round(spread_cost, 2),
           "commission": round(commission, 2),
           "capital_gains_tax": round(cg_tax, 2)}
    port["transactions"].append(txn)
    del port["holdings"][sym]
    return txn

def _credit_dividend(port, sym, div_per_share, params=None):
    if sym not in port["holdings"] or div_per_share <= 0:
        return 0
    h = port["holdings"][sym]
    gross = h["shares"] * div_per_share
    # Withholding tax on dividends
    tax_pct = (params or {}).get("dividend_tax_pct", 25.5) / 100
    tax = gross * tax_pct
    net = gross - tax
    port["cash"] += net
    h["dividends"] += net
    port["total_dividend_tax"] += tax
    return net

def _snapshot(port, snap_date, prices):
    port["equity_curve"].append({
        "date": snap_date,
        "value_usd": _portfolio_value(port, prices),
        "cash": port["cash"],
        "n_holdings": len(port["holdings"]),
    })

# ═══════════════════════════════════════════════════════════════════════
#  Monthly / yearly return computation
# ═══════════════════════════════════════════════════════════════════════

def _compute_periodic_returns(equity_curve, eur_rates):
    """Compute monthly + yearly returns from equity curve."""
    if len(equity_curve) < 2:
        return [], []

    by_month = {}
    for snap in equity_curve:
        ym = snap["date"][:7]
        by_month.setdefault(ym, []).append(snap)

    months = sorted(by_month.keys())
    prev_value = equity_curve[0]["value_usd"]
    monthly = []
    for ym in months:
        snaps = by_month[ym]
        end_snap = snaps[-1]
        end_value = end_snap["value_usd"]
        ret_pct = (end_value / prev_value - 1) * 100 if prev_value > 0 else 0
        year, month = int(ym[:4]), int(ym[5:7])
        rate = _get_eur_rate(eur_rates, end_snap["date"])
        monthly.append({
            "year": year, "month": month,
            "return_pct": round(ret_pct, 2),
            "value_usd": round(end_value, 2),
            "value_eur": round(_usd_to_eur(end_value, rate), 2),
        })
        prev_value = end_value

    # Yearly
    yearly = []
    yr_prev = equity_curve[0]["value_usd"]
    year_data = {}
    for m in monthly:
        year_data[m["year"]] = m  # last month of each year
    for yr in sorted(year_data.keys()):
        m = year_data[yr]
        ret = (m["value_usd"] / yr_prev - 1) * 100 if yr_prev > 0 else 0
        yearly.append({
            "year": yr, "return_pct": round(ret, 2),
            "value_usd": round(m["value_usd"], 2),
            "value_eur": round(m["value_eur"], 2),
            "dividends_eur": 0,
        })
        yr_prev = m["value_usd"]

    return monthly, yearly

# ═══════════════════════════════════════════════════════════════════════
#  Metrics
# ═══════════════════════════════════════════════════════════════════════

def _compute_metrics(port, eur_rates):
    """Compute performance metrics."""
    curve = port["equity_curve"]
    if not curve:
        return {}

    start_val = port["starting_cash"]
    end_val = curve[-1]["value_usd"]
    total_return = (end_val / start_val - 1) * 100

    start_dt = datetime.strptime(curve[0]["date"], "%Y-%m-%d")
    end_dt = datetime.strptime(curve[-1]["date"], "%Y-%m-%d")
    days = (end_dt - start_dt).days
    years = days / 365.25 if days > 0 else 1
    annualized = ((end_val / start_val) ** (1 / years) - 1) * 100 if years > 0 else 0

    # Max drawdown
    peak = start_val
    max_dd = 0
    for snap in curve:
        v = snap["value_usd"]
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)

    # Sharpe
    sharpe = 0
    if len(curve) >= 5:
        values = [s["value_usd"] for s in curve]
        returns = [(values[i] / values[i - 1] - 1) for i in range(1, len(values))]
        if returns:
            mean_r = np.mean(returns)
            std_r = np.std(returns, ddof=1)
            if std_r > 0:
                ppyr = max(1, 365.25 / max(1, days / len(returns)))
                sharpe = (mean_r / std_r) * math.sqrt(ppyr)

    # Win/loss
    wins = losses = 0
    total_divs = 0.0
    for txn in port["transactions"]:
        if txn["action"] == "SELL":
            if txn.get("pnl_pct", 0) >= 0:
                wins += 1
            else:
                losses += 1
            total_divs += txn.get("dividends", 0)
    for h in port["holdings"].values():
        total_divs += h.get("dividends", 0)

    closed = wins + losses
    win_rate = (wins / closed * 100) if closed > 0 else None

    end_rate = _get_eur_rate(eur_rates, curve[-1]["date"])
    final_eur = _usd_to_eur(end_val, end_rate)
    divs_eur = _usd_to_eur(total_divs, end_rate)

    # Friction cost totals
    spread_cost = port.get("total_spread_cost", 0)
    commission_cost = port.get("total_commission", 0)
    div_tax = port.get("total_dividend_tax", 0)
    cg_tax = port.get("total_capital_gains_tax", 0)
    total_friction = spread_cost + commission_cost + div_tax + cg_tax
    friction_eur = _usd_to_eur(total_friction, end_rate)

    return {
        "total_return_pct": round(total_return, 2),
        "annualized_return_pct": round(annualized, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "win_rate_pct": round(win_rate, 1) if win_rate is not None else None,
        "wins": wins, "losses": losses,
        "total_trades": len(port["transactions"]),
        "total_dividends_usd": round(total_divs, 2),
        "total_dividends_eur": round(divs_eur, 2),
        "final_value_usd": round(end_val, 2),
        "final_value_eur": round(final_eur, 2),
        "days": days, "years": round(years, 2),
        # Friction costs
        "spread_cost_usd": round(spread_cost, 2),
        "commission_cost_usd": round(commission_cost, 2),
        "dividend_tax_usd": round(div_tax, 2),
        "capital_gains_tax_usd": round(cg_tax, 2),
        "total_friction_usd": round(total_friction, 2),
        "total_friction_eur": round(friction_eur, 2),
    }

# ═══════════════════════════════════════════════════════════════════════
#  Main backtest engine
# ═══════════════════════════════════════════════════════════════════════

def run_backtest(args):
    """Execute a historical backtest with long-term investor logic."""
    from utils.benchmark import get_benchmark_returns

    tickers, flags = _resolve_tickers(args)

    if flags.get("show_runs"):
        _show_runs(); return
    if flags.get("show_run_id"):
        _show_run(flags["show_run_id"]); return

    if not tickers:
        print("  No tickers specified.  Usage:")
        print("    python stock.py backtest AAPL MSFT --period 2y")
        print("    python stock.py backtest --watchlist --period 1y")
        return

    period = flags.get("period", "1y")
    start_date = _parse_period(period)
    if not start_date:
        return

    frequency = flags.get("frequency", "weekly")
    end_date = date.today().isoformat()
    generate_html = flags.get("html", True)

    enable_cache()

    # ── Strategy parameters ──────────────────────────────────────
    sim_cfg = config().get("simulation", {})
    starting_cash = flags.get("cash", sim_cfg.get("starting_cash", 100_000))
    params = {
        "starting_cash": starting_cash,
        "fund_buy_threshold": sim_cfg.get("fund_buy_threshold", 45),
        "fund_sell_threshold": sim_cfg.get("fund_sell_threshold", 30),
        "base_position_pct": sim_cfg.get("base_position_pct", 0.06),
        "max_position_pct": sim_cfg.get("max_position_pct", 0.10),
        "max_positions": sim_cfg.get("max_positions", 20),
        "stop_loss_pct": sim_cfg.get("stop_loss_pct", 0.25),
        "tech_influence": sim_cfg.get("tech_influence", 0.3),
        "macro_influence": sim_cfg.get("macro_influence", 0.5),
        "eval_frequency": frequency,
        # ── Friction costs ──
        # Spread/slippage: realistic bid-ask cost per trade
        "spread_pct": sim_cfg.get("spread_pct", 0.10),          # 0.10% per trade
        # Dividend withholding tax (Finland: 25.5% on foreign divs)
        "dividend_tax_pct": sim_cfg.get("dividend_tax_pct", 25.5),
        # Capital gains tax (Finland: 30% on gains, 0% on losses)
        "capital_gains_tax_pct": sim_cfg.get("capital_gains_tax_pct", 30.0),
        # Broker commission per trade in EUR
        "commission_eur": sim_cfg.get("commission_eur", 0.0),
    }

    port = _make_portfolio(starting_cash)

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           BACKTEST — Long-Term Investor                     ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")
    print(f"  Period:       {start_date} → {end_date} ({period})")
    print(f"  Tickers:      {', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''} ({len(tickers)})")
    print(f"  Capital:      ${starting_cash:,.0f}")
    print(f"  Strategy:     Fund ≥{params['fund_buy_threshold']} → buy, "
          f"<{params['fund_sell_threshold']} → sell")
    print(f"  Tech weight:  {params['tech_influence']*100:.0f}%  (sizing confidence)")
    print(f"  Macro weight: {params['macro_influence']*100:.0f}%  (environment sizing)")
    print(f"  Stop-loss:    {params['stop_loss_pct']*100:.0f}%")
    print(f"  Spread:       {params['spread_pct']:.2f}% per trade")
    print(f"  Dividend tax: {params['dividend_tax_pct']:.1f}%   (withholding)")
    print(f"  CG tax:       {params['capital_gains_tax_pct']:.1f}%   (on realized gains)")
    if params['commission_eur'] > 0:
        print(f"  Commission:   €{params['commission_eur']:.2f} per trade")
    print(f"  Note:         Fund scores use CURRENT data (look-ahead bias).")
    print(f"                Technical + macro are historically accurate.\n")

    # ── 1. Fetch price data ──────────────────────────────────────
    print(f"  Fetching historical data...")
    lookback_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=300)).strftime("%Y-%m-%d")
    histories = _fetch_historical_data(tickers, lookback_start, end_date)

    available = [t for t in tickers if t in histories]
    missing = [t for t in tickers if t not in histories]
    if missing:
        print(f"  Warning: no data for {', '.join(missing[:5])}")
    if not available:
        print("  No historical data. Exiting.")
        return
    print(f"  Got price data for {len(available)} tickers")

    # ── 2. Fundamental scores ────────────────────────────────────
    DEFAULT_FUND = 55
    try:
        from utils.scores_db import get_latest_scores
        fund_scores = {r["symbol"]: r.get("fundamental_score") for r in get_latest_scores()}
    except Exception:
        fund_scores = {}

    unscored = [t for t in available if t not in fund_scores or fund_scores[t] is None]
    for t in unscored:
        fund_scores[t] = DEFAULT_FUND
    scored_real = [t for t in available if t not in unscored]
    if scored_real:
        parts = [f"{t}({fund_scores[t]:.0f})" for t in scored_real[:6]]
        print(f"  Real fund scores: {', '.join(parts)}"
              + (f" +{len(scored_real)-6} more" if len(scored_real) > 6 else ""))
    if unscored:
        print(f"  Default fund score ({DEFAULT_FUND}) for: {', '.join(unscored[:6])}"
              + (f" +{len(unscored)-6} more" if len(unscored) > 6 else ""))

    # ── 3. EUR/USD conversion ────────────────────────────────────
    print(f"  Fetching EUR/USD rates...")
    eur_rates = _fetch_eurusd(start_date, end_date)
    if eur_rates:
        print(f"  EUR/USD: {len(eur_rates)} data points")
    else:
        print(f"  EUR/USD unavailable, using 1.10 default")

    # ── 4. Evaluation dates ──────────────────────────────────────
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    eval_dates = []
    current_dt = start_dt
    step = timedelta(weeks=1) if frequency == "weekly" else timedelta(weeks=4)
    while current_dt <= end_dt:
        eval_dates.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += step
    if eval_dates[-1] != end_date:
        eval_dates.append(end_date)

    print(f"\n  Running simulation ({len(eval_dates)} evaluation points)...\n")

    # ── 5. Simulation loop ───────────────────────────────────────
    macro_cache = {}
    total_divs = 0
    buy_count = sell_count = 0

    for idx, eval_date in enumerate(eval_dates):
        pct = (idx + 1) / len(eval_dates) * 100
        if idx % max(1, len(eval_dates) // 20) == 0 or idx == len(eval_dates) - 1:
            print(f"  [{idx+1}/{len(eval_dates)}] {eval_date}  ({pct:.0f}%)", end="\r")

        # Current prices
        prices = {}
        for sym in available:
            hist = histories[sym]
            mask = hist.index.strftime("%Y-%m-%d") <= eval_date
            if mask.any():
                prices[sym] = float(hist[mask]["Close"].iloc[-1])
        if not prices:
            continue

        # Macro (cached per month)
        mm = eval_date[:7]
        if mm not in macro_cache:
            macro_cache[mm] = _compute_macro(eval_date)
        macro_score = macro_cache[mm]

        # Credit dividends
        prev_date = eval_dates[idx - 1] if idx > 0 else start_date
        for sym in list(port["holdings"].keys()):
            if sym in histories:
                hist = histories[sym]
                mask = (hist.index.strftime("%Y-%m-%d") > prev_date) & \
                       (hist.index.strftime("%Y-%m-%d") <= eval_date)
                div_sum = float(hist.loc[mask, "Dividends"].sum()) if mask.any() else 0
                if div_sum > 0:
                    total_divs += _credit_dividend(port, sym, div_sum, params)

        # Evaluate each ticker
        for sym in available:
            price = prices.get(sym)
            if not price:
                continue

            # Technical score
            hist = histories[sym]
            mask = hist.index.strftime("%Y-%m-%d") <= eval_date
            if not mask.any():
                continue
            closes = hist[mask]["Close"].values.astype(float)
            tech_score = _compute_technical(closes)
            fund_score = fund_scores.get(sym)

            # ── SELL CHECK (for held positions) ──────────────────
            if sym in port["holdings"]:
                should_sell, sell_reason = _investor_should_sell(
                    fund_score, port["holdings"][sym], price, params,
                )
                if should_sell:
                    txn = _sell_all(port, sym, price, eval_date, sell_reason, params)
                    if txn:
                        sell_count += 1
                    continue  # don't re-buy same tick

            # ── BUY CHECK ────────────────────────────────────────
            if len(port["holdings"]) >= params["max_positions"] and sym not in port["holdings"]:
                continue

            should_buy, target_pct, buy_reason = _investor_should_buy(
                fund_score, tech_score, macro_score, params,
            )
            if not should_buy:
                continue

            current_weight = _portfolio_weight(port, sym, prices)
            additional_pct = max(0, target_pct - current_weight)
            if additional_pct < 0.005:
                continue

            total_value = _portfolio_value(port, prices)
            target_dollars = total_value * additional_pct
            target_dollars = min(target_dollars, port["cash"])
            if target_dollars < price:
                continue

            shares = int(target_dollars / price)
            if shares > 0:
                txn = _buy(port, sym, shares, price, eval_date, buy_reason, params)
                if txn:
                    buy_count += 1

        # Record snapshot
        _snapshot(port, eval_date, prices)

    print()  # clear progress line

    # ── 6. Compute results ───────────────────────────────────────
    metrics = _compute_metrics(port, eur_rates)
    monthly, yearly = _compute_periodic_returns(port["equity_curve"], eur_rates)

    # Dividends per year in EUR
    div_by_year = {}
    for txn in port["transactions"]:
        if txn["action"] == "SELL":
            yr = int(txn["date"][:4])
            rate = _get_eur_rate(eur_rates, txn["date"])
            div_by_year[yr] = div_by_year.get(yr, 0) + _usd_to_eur(txn.get("dividends", 0), rate)
    for h in port["holdings"].values():
        ed = port["equity_curve"][-1]["date"] if port["equity_curve"] else end_date
        rate = _get_eur_rate(eur_rates, ed)
        yr = int(ed[:4])
        div_by_year[yr] = div_by_year.get(yr, 0) + _usd_to_eur(h.get("dividends", 0), rate)
    for y in yearly:
        y["dividends_eur"] = round(div_by_year.get(y["year"], 0), 0)

    # Benchmarks
    benchmarks_list = sim_cfg.get("benchmarks", ["SPY", "QQQ", "VT"])
    print(f"\n  Fetching benchmark data...")
    bench_returns = get_benchmark_returns(benchmarks_list, start_date, end_date)

    # ── 7. Print terminal summary ────────────────────────────────
    _print_summary(metrics, params, start_date, end_date, period,
                   buy_count, sell_count, total_divs, bench_returns, monthly, eur_rates)

    # ── 8. HTML report ───────────────────────────────────────────
    if generate_html:
        _generate_report(
            port, metrics, monthly, yearly, bench_returns,
            params, tickers, start_date, end_date, period, eur_rates,
            histories,
        )

# ═══════════════════════════════════════════════════════════════════════
#  Terminal output
# ═══════════════════════════════════════════════════════════════════════

def _print_summary(metrics, params, start_date, end_date, period,
                   buy_count, sell_count, total_divs, bench_returns, monthly, eur_rates):
    """Print concise terminal summary."""
    ret = metrics.get("total_return_pct", 0)
    G = "\033[92m"; R = "\033[91m"; W = "\033[0m"
    color = G if ret >= 0 else R

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           RESULTS                                          ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    print(f"  Period:        {start_date} → {end_date}")
    print(f"  Total return:  {color}{ret:+.1f}%{W}  "
          f"({metrics.get('annualized_return_pct', 0):+.1f}% annualized)")
    print(f"  Final value:   €{metrics.get('final_value_eur', 0):,.0f}  "
          f"(${metrics.get('final_value_usd', 0):,.0f})")
    print(f"  Max drawdown:  -{metrics.get('max_drawdown_pct', 0):.1f}%")
    print(f"  Sharpe ratio:  {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  Trades:        {buy_count + sell_count} "
          f"({buy_count} buys, {sell_count} sells)")
    if metrics.get("win_rate_pct") is not None:
        print(f"  Win rate:      {metrics['win_rate_pct']:.0f}%  "
              f"({metrics.get('wins', 0)}W / {metrics.get('losses', 0)}L)")
    print(f"  Dividends:     €{metrics.get('total_dividends_eur', 0):,.0f}")

    # Friction costs breakdown
    friction_total = metrics.get("total_friction_eur", 0)
    if friction_total > 0:
        print(f"\n  ── Cost of Active Investing ──")
        if metrics.get("spread_cost_usd", 0) > 0:
            sc = _usd_to_eur(metrics["spread_cost_usd"], _get_eur_rate(eur_rates, end_date))
            print(f"  Spread/slippage:  €{sc:>8,.0f}")
        if metrics.get("commission_cost_usd", 0) > 0:
            cc = _usd_to_eur(metrics["commission_cost_usd"], _get_eur_rate(eur_rates, end_date))
            print(f"  Commissions:      €{cc:>8,.0f}")
        if metrics.get("dividend_tax_usd", 0) > 0:
            dt = _usd_to_eur(metrics["dividend_tax_usd"], _get_eur_rate(eur_rates, end_date))
            print(f"  Dividend tax:     €{dt:>8,.0f}")
        if metrics.get("capital_gains_tax_usd", 0) > 0:
            gt = _usd_to_eur(metrics["capital_gains_tax_usd"], _get_eur_rate(eur_rates, end_date))
            print(f"  Capital gains tax:€{gt:>8,.0f}")
        print(f"  {'─' * 30}")
        print(f"  Total friction:   €{friction_total:>8,.0f}  "
              f"({friction_total / params['starting_cash'] * _get_eur_rate(eur_rates, end_date) * 100:.1f}% of starting capital)")

    # Benchmarks
    print(f"\n  ── Benchmarks ──")
    for sym, data in bench_returns.items():
        br = data.get("total_return_pct")
        if br is not None:
            alpha = ret - br
            ac = G if alpha >= 0 else R
            print(f"  {sym:8s} {br:+.1f}%   alpha: {ac}{alpha:+.1f}%{W}")

    # Recent monthly returns
    recent = monthly[-12:] if len(monthly) > 12 else monthly
    if recent:
        print(f"\n  ── Monthly Returns (recent) ──")
        for m in recent:
            r = m["return_pct"]
            mc = G if r >= 0 else R
            print(f"  {m['year']}-{m['month']:02d}  {mc}{r:+5.1f}%{W}  "
                  f"€{m['value_eur']:>10,.0f}")

    print()

# ═══════════════════════════════════════════════════════════════════════
#  HTML report generation
# ═══════════════════════════════════════════════════════════════════════

def _generate_report(port, metrics, monthly, yearly, bench_returns,
                     params, tickers, start_date, end_date, period,
                     eur_rates, histories):
    """Build data dict and generate HTML report."""
    from simulation.report import generate_html_report, save_report

    # Equity curve with EUR
    eq_eur = []
    for snap in port["equity_curve"]:
        rate = _get_eur_rate(eur_rates, snap["date"])
        eq_eur.append({
            "date": snap["date"],
            "value_usd": snap["value_usd"],
            "value_eur": _usd_to_eur(snap["value_usd"], rate),
        })

    # Trades with EUR
    trades_eur = []
    for txn in port["transactions"]:
        rate = _get_eur_rate(eur_rates, txn["date"])
        trades_eur.append({**txn, "value_eur": round(_usd_to_eur(txn.get("value_usd", 0), rate), 0)})

    # Final holdings
    holdings_data = []
    last_date = port["equity_curve"][-1]["date"] if port["equity_curve"] else end_date
    rate = _get_eur_rate(eur_rates, last_date)
    total_val = port["equity_curve"][-1]["value_usd"] if port["equity_curve"] else params["starting_cash"]
    for sym, h in sorted(port["holdings"].items()):
        # Get latest price from history
        cp = h["avg_cost"]
        if sym in histories:
            last_hist = histories[sym]
            if not last_hist.empty:
                cp = float(last_hist["Close"].iloc[-1])
        val_usd = h["shares"] * cp
        holdings_data.append({
            "symbol": sym, "shares": h["shares"],
            "avg_cost": h["avg_cost"], "current_price": cp,
            "value_eur": round(_usd_to_eur(val_usd, rate), 0),
            "pnl_pct": round((cp / h["avg_cost"] - 1) * 100, 1) if h["avg_cost"] > 0 else 0,
            "weight_pct": round(val_usd / total_val * 100, 1) if total_val > 0 else 0,
        })

    report_data = {
        "title": f"Backtest Report — {period}",
        "period": {"start": start_date, "end": end_date},
        "parameters": params,
        "tickers": tickers,
        "metrics": metrics,
        "equity_curve": eq_eur,
        "monthly_returns": monthly,
        "yearly_returns": yearly,
        "benchmarks": bench_returns,
        "trades": trades_eur,
        "holdings": holdings_data,
        "strategy_note": (
            f"<strong>Long-term investor strategy with realistic friction:</strong> "
            f"Buy when fundamentals ≥ {params['fund_buy_threshold']}, "
            f"sell only when fundamentals < {params['fund_sell_threshold']} or stop-loss triggers. "
            f"Technical analysis adjusts entry sizing ({params['tech_influence']*100:.0f}% influence). "
            f"Macro environment drives allocation ({params['macro_influence']*100:.0f}% influence). "
            f"<br><strong>Costs modeled:</strong> "
            f"{params['spread_pct']:.2f}% spread per trade, "
            f"{params['dividend_tax_pct']:.1f}% dividend withholding tax, "
            f"{params['capital_gains_tax_pct']:.1f}% capital gains tax on realized profits."
        ),
    }

    html = generate_html_report(report_data)

    import os
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    filename = f"backtest_{period}_{len(tickers)}stocks_{date.today().isoformat()}.html"
    filepath = os.path.join(output_dir, filename)
    saved = save_report(html, filepath)

    print(f"  HTML report: {saved}")

    try:
        import subprocess
        subprocess.Popen(["open", saved], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  Opened in browser")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════
#  Past runs management
# ═══════════════════════════════════════════════════════════════════════

def _show_runs():
    """List all backtest runs."""
    from simulation.database import list_runs
    runs = list_runs(run_type="backtest", limit=30)
    if not runs:
        print("  No backtest runs found.")
        return
    print(f"\n  {'ID':>4s} {'Name':35s} {'Period':25s} {'Return':>10s} {'Value':>12s}")
    print(f"  {'─' * 90}")
    for r in runs:
        period_str = f"{r['start_date']} → {r.get('end_date', '?')}"
        ret_str = f"{r['total_return_pct']:+.1f}%" if r.get("total_return_pct") is not None else "N/A"
        val_str = f"${r['final_value']:,.0f}" if r.get("final_value") else "N/A"
        print(f"  {r['id']:>4d} {r['name']:35s} {period_str:25s} {ret_str:>10s} {val_str:>12s}")
    print(f"\n  View details:  python stock.py backtest --show <ID>\n")

def _show_run(run_id):
    """Show detailed results of a past run."""
    from simulation.database import get_run
    import json

    data = get_run(run_id)
    if not data:
        print(f"  Run #{run_id} not found.")
        return

    run = data["run"]
    txns = data["transactions"]

    print(f"\n  Run #{run_id}: {run['name']}")
    print(f"  Period: {run['start_date']} → {run.get('end_date', '?')}")
    print(f"  Capital: ${run['starting_cash']:,.0f} → ${run.get('final_value', 0):,.0f}")
    if run.get("total_return_pct") is not None:
        ret = run["total_return_pct"]
        color = "\033[92m" if ret >= 0 else "\033[91m"
        print(f"  Return: {color}{ret:+.2f}%\033[0m")
    if txns:
        print(f"\n  Transactions ({len(txns)}):")
        for t in txns[:30]:
            icon = "🟢" if t["action"] == "BUY" else "🔴"
            print(f"  {t['date']}  {icon} {t['action']:4s} {t['symbol']:6s}  "
                  f"{t['shares']:>6.0f} @ ${t['price']:>8.2f}  {t.get('reason', '')}")
    print()

# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if not args:
        print("Usage: python stock.py backtest AAPL MSFT --period 2y")
        print("       python stock.py backtest --watchlist --period 1y")
        print("       python stock.py backtest --all --period 2y")
        print("       python stock.py backtest --runs")
        print("       python stock.py backtest --show <ID>")
        return

    if args[0].lower() == "--runs":
        _show_runs(); return
    if args[0].lower() == "--show" and len(args) > 1:
        _show_run(int(args[1])); return

    run_backtest(args)
