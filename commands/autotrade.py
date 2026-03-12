"""autotrade command: automated paper-trading using verdict signals.

Scans your watchlist (and optionally portfolio), computes verdicts,
and automatically executes paper buys/sells based on the verdict engine.

This is a FORWARD-LOOKING auto-trader — it makes decisions today and
records them. For historical replay, see the 'backtest' command.

Usage:
    python stock.py autotrade                    Run auto-trade cycle on watchlist
    python stock.py autotrade --portfolio        Include portfolio tickers too
    python stock.py autotrade --tickers AAPL MSFT  Specific tickers
    python stock.py autotrade status             Show current sim portfolio
    python stock.py autotrade history            Show transaction history
    python stock.py autotrade reset              Reset simulation portfolio
    python stock.py autotrade runs               List all saved runs
"""

import sys
import time
from datetime import date

from utils.config import config, enable_cache

def _get_sim_config():
    """Load simulation settings from config."""
    cfg = config()
    return cfg.get("simulation", {})

def _create_portfolio():
    """Create a fresh SimPortfolio from config."""
    from simulation.engine import SimPortfolio

    sim_cfg = _get_sim_config()
    return SimPortfolio(
        name=f"autotrade_{date.today().isoformat()}",
        starting_cash=sim_cfg.get("starting_cash", 100_000),
        cash=sim_cfg.get("starting_cash", 100_000),
        max_position_pct=sim_cfg.get("max_position_pct", 0.10),
        max_positions=sim_cfg.get("max_positions", 20),
        commission=sim_cfg.get("commission", 0.0),
        stop_loss_pct=sim_cfg.get("stop_loss_pct", 0.20),
        take_profit_pct=sim_cfg.get("take_profit_pct", 0.0),
    )

def _load_or_create_portfolio():
    """Load the latest auto-trade portfolio, or create a new one."""
    from simulation.database import get_latest_autotrade_run
    from simulation.engine import SimPortfolio, Holding

    run_data = get_latest_autotrade_run()
    if run_data is None:
        return _create_portfolio(), True  # is_new=True

    # Reconstruct portfolio from saved state
    import json
    run = run_data["run"]
    cfg = json.loads(run.get("config_json", "{}"))

    portfolio = SimPortfolio(
        name=run["name"],
        starting_cash=run["starting_cash"],
        cash=0,  # will be set from equity curve
        max_position_pct=cfg.get("max_position_pct", 0.10),
        max_positions=cfg.get("max_positions", 20),
        commission=cfg.get("commission", 0.0),
        stop_loss_pct=cfg.get("stop_loss_pct", 0.20),
        take_profit_pct=cfg.get("take_profit_pct", 0.0),
    )

    # Restore holdings
    for h in run_data["holdings"]:
        portfolio.holdings[h["symbol"]] = Holding(
            symbol=h["symbol"],
            shares=h["shares"],
            avg_cost=h["avg_cost"],
            total_cost=h["total_cost"],
            first_buy_date=h["first_buy_date"],
            dividends_collected=h.get("dividends", 0),
        )

    # Restore cash from last equity curve entry
    if run_data["equity_curve"]:
        last = run_data["equity_curve"][-1]
        portfolio.cash = last["cash"]
    else:
        # Estimate from starting cash - total cost
        total_cost = sum(h.total_cost for h in portfolio.holdings.values())
        portfolio.cash = portfolio.starting_cash - total_cost

    # Restore equity curve
    portfolio.equity_curve = [
        {"date": e["date"], "total_value": e["total_value"],
         "cash": e["cash"], "holdings_value": e["holdings_value"],
         "num_holdings": e["num_holdings"]}
        for e in run_data["equity_curve"]
    ]

    return portfolio, False

def _resolve_tickers(args):
    """Determine which tickers to scan."""
    from utils.lists import resolve_tickers
    return resolve_tickers(args, with_remaining=True, default_all=True)

def _get_current_prices(tickers):
    """Fetch current prices for all tickers."""
    from datasources.market import get_current_prices
    return get_current_prices(tickers)

def run_autotrade(args):
    """Execute one auto-trading cycle."""
    from simulation.engine import (
        SimPortfolio, compute_position_size, execute_buy, execute_sell_all,
        check_exit_signals, record_snapshot, credit_dividends, compute_metrics,
    )
    from analysis.verdict import compute_verdict, should_buy, should_sell
    from analysis.technical import analyze_technical
    from analysis.macro import analyze_macro
    from utils.benchmark import get_dividends_between
    from simulation.database import save_simulation

    tickers, _ = _resolve_tickers(args)
    if not tickers:
        print("  No tickers to auto-trade. Add stocks to your watchlist first.")
        return

    enable_cache()

    # Load or create portfolio
    portfolio, is_new = _load_or_create_portfolio()
    today = date.today().isoformat()

    if is_new:
        print(f"\n  🆕 New auto-trade portfolio created (${portfolio.starting_cash:,.0f})")
    else:
        print(f"\n  📂 Continuing auto-trade portfolio '{portfolio.name}'")
        print(f"     Cash: ${portfolio.cash:,.2f}  |  Holdings: {len(portfolio.holdings)}")

    # 1. Fetch macro (shared)
    print("\n  Fetching macro environment...")
    macro = analyze_macro()
    macro_score = macro["macro_score"]

    # 2. Get fundamental scores from DB
    try:
        from utils.scores_db import get_latest_scores
        fund_scores = {r["symbol"]: r.get("fundamental_score") for r in get_latest_scores()}
    except Exception:
        fund_scores = {}

    # 3. Fetch prices for all tickers + held positions
    all_syms = list(set(tickers + list(portfolio.holdings.keys())))
    print(f"  Fetching prices for {len(all_syms)} symbols...")
    prices = _get_current_prices(all_syms)

    # 4. Credit dividends for held positions
    div_total = 0
    for sym in list(portfolio.holdings.keys()):
        h = portfolio.holdings[sym]
        # Check dividends since last run
        last_date = portfolio.equity_curve[-1]["date"] if portfolio.equity_curve else h.first_buy_date
        divs = get_dividends_between(sym, last_date, today)
        if divs > 0:
            amt = credit_dividends(portfolio, sym, divs, today)
            if amt > 0:
                div_total += amt
                print(f"  💰 Dividend: {sym} ${amt:.2f}")

    if div_total > 0:
        print(f"  Total dividends credited: ${div_total:.2f}")

    # 5. Check stop-loss / take-profit on existing holdings
    exits = check_exit_signals(portfolio, prices)
    sell_count = 0
    for sym, reason in exits:
        price = prices.get(sym)
        if price:
            fund = fund_scores.get(sym)
            ta = analyze_technical(sym)
            tech = ta.get("tech_score") if ta else None
            v = compute_verdict(fund, tech, macro_score)

            txn = execute_sell_all(
                portfolio, sym, price, today, v["verdict"],
                fund, tech, macro_score, reason,
            )
            if txn:
                sell_count += 1
                pnl = txn.value - txn.shares * portfolio.holdings.get(sym, type("", (), {"avg_cost": price})).avg_cost if sym in portfolio.holdings else 0
                print(f"  🔴 SELL {sym}: {txn.shares:.0f} shares @ ${price:.2f} — {reason}")
            time.sleep(0.3)

    # 6. Evaluate verdicts and execute trades
    print(f"\n  Evaluating {len(tickers)} tickers...\n")

    buy_count = 0
    verdicts_summary = []

    for i, sym in enumerate(tickers, 1):
        ta = analyze_technical(sym)
        tech_score = ta.get("tech_score", 0) if ta else None
        fund_score = fund_scores.get(sym)

        v = compute_verdict(fund_score, tech_score, macro_score)
        verdict = v["verdict"]
        price = prices.get(sym)

        # Check sell signal for held positions
        if sym in portfolio.holdings and price:
            # Get previous verdict if available
            prev_verdict = None
            for txn in reversed(portfolio.transactions):
                if txn.symbol == sym:
                    prev_verdict = txn.verdict
                    break

            do_sell, sell_reason = should_sell(v, prev_verdict)
            if do_sell:
                txn = execute_sell_all(
                    portfolio, sym, price, today, verdict,
                    fund_score, tech_score, macro_score, sell_reason,
                )
                if txn:
                    sell_count += 1
                    print(f"  🔴 SELL {sym}: {txn.shares:.0f} shares @ ${price:.2f} — {sell_reason}")
                continue

        # Check buy signal
        do_buy, action, buy_reason = should_buy(v)

        if do_buy and price and price > 0:
            # Don't buy if we're already at max positions
            if len(portfolio.holdings) >= portfolio.max_positions and sym not in portfolio.holdings:
                verdicts_summary.append((sym, verdict, "⏭️  Max positions reached"))
                continue

            # Skip if action is ADD but we don't hold it yet
            if action == "ADD" and sym not in portfolio.holdings:
                verdicts_summary.append((sym, verdict, "↗️  Would accumulate (no position yet)"))
                continue

            shares = compute_position_size(
                portfolio, sym, price,
                v["position_lo"], v["position_hi"], v["multiplier"],
                prices,
            )
            if shares > 0:
                txn = execute_buy(
                    portfolio, sym, shares, price, today, verdict,
                    fund_score, tech_score, macro_score, buy_reason,
                )
                if txn:
                    buy_count += 1
                    print(f"  🟢 BUY  {sym}: {txn.shares:.0f} shares @ ${price:.2f} (${txn.value:,.0f}) — {buy_reason}")
            else:
                verdicts_summary.append((sym, verdict, "💰 Insufficient allocation"))
        else:
            icon = {"NEUTRAL": "⚪", "WATCH": "👀", "HOLD": "✋", "AVOID": "🚫"}.get(verdict, "·")
            verdicts_summary.append((sym, verdict, f"{icon}  No action"))

        if i < len(tickers):
            time.sleep(0.3)

    # 7. Record snapshot
    record_snapshot(portfolio, today, prices)

    # 8. Save to database
    run_id = save_simulation(portfolio, run_type="autotrade")

    # 9. Print summary
    metrics = compute_metrics(portfolio)
    total_value = portfolio.portfolio_value_at_prices(prices)

    print(f"\n  {'═' * 60}")
    print(f"  AUTO-TRADE SUMMARY — {today}")
    print(f"  {'═' * 60}")
    print(f"  Actions: {buy_count} buys, {sell_count} sells")
    print(f"  Portfolio: ${total_value:,.2f}  (Cash: ${portfolio.cash:,.2f})")
    print(f"  Holdings: {len(portfolio.holdings)} positions")
    if metrics.get("total_return_pct") is not None:
        ret = metrics["total_return_pct"]
        color = "\033[92m" if ret >= 0 else "\033[91m"
        print(f"  Return: {color}{ret:+.2f}%\033[0m  (since {portfolio.equity_curve[0]['date'] if portfolio.equity_curve else 'today'})")
    if metrics.get("total_dividends", 0) > 0:
        print(f"  Dividends collected: ${metrics['total_dividends']:,.2f}")
    print(f"  Run saved (ID: {run_id})")

    # Show non-action verdicts
    if verdicts_summary:
        print(f"\n  Other verdicts:")
        for sym, verdict, note in verdicts_summary[:15]:
            print(f"    {sym:6s} {verdict:12s} {note}")
        if len(verdicts_summary) > 15:
            print(f"    ... and {len(verdicts_summary) - 15} more")

    print()

def show_status(args):
    """Show current auto-trade portfolio status."""
    from simulation.database import get_latest_autotrade_run
    from simulation.engine import compute_metrics

    run_data = get_latest_autotrade_run()
    if not run_data:
        print("  No auto-trade portfolio found. Run 'python stock.py autotrade' to start.")
        return

    import json
    run = run_data["run"]
    metrics = json.loads(run.get("metrics_json", "{}"))

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           AUTO-TRADE PORTFOLIO STATUS                       ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    print(f"  Portfolio: {run['name']}")
    print(f"  Period: {run['start_date']} → {run.get('end_date', 'ongoing')}")
    print(f"  Starting cash: ${run['starting_cash']:,.2f}")
    if run.get("final_value"):
        print(f"  Current value: ${run['final_value']:,.2f}")
    if run.get("total_return_pct") is not None:
        ret = run["total_return_pct"]
        color = "\033[92m" if ret >= 0 else "\033[91m"
        print(f"  Total return: {color}{ret:+.2f}%\033[0m")

    # Metrics
    if metrics:
        if metrics.get("sharpe_ratio") is not None:
            print(f"  Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
        if metrics.get("max_drawdown_pct") is not None:
            print(f"  Max drawdown: {metrics['max_drawdown_pct']:.1f}%")
        if metrics.get("win_rate_pct") is not None:
            print(f"  Win rate: {metrics['win_rate_pct']:.0f}%  ({metrics.get('wins', 0)}W / {metrics.get('losses', 0)}L)")
        if metrics.get("total_dividends", 0) > 0:
            print(f"  Dividends: ${metrics['total_dividends']:,.2f}")

    # Holdings
    holdings = run_data["holdings"]
    if holdings:
        print(f"\n  Open positions ({len(holdings)}):")
        print(f"  {'Symbol':8s} {'Shares':>8s} {'Avg Cost':>10s} {'Value':>10s} {'Verdict':>12s}")
        print(f"  {'─' * 50}")

        # Get current prices
        prices = _get_current_prices([h["symbol"] for h in holdings])

        for h in sorted(holdings, key=lambda x: x["symbol"]):
            sym = h["symbol"]
            current = prices.get(sym)
            value_str = f"${current * h['shares']:,.0f}" if current else "N/A"
            print(f"  {sym:8s} {h['shares']:>8.1f} ${h['avg_cost']:>9.2f} {value_str:>10s} {h.get('last_verdict', 'N/A'):>12s}")
    else:
        print("\n  No open positions.")

    print()

def show_history(args):
    """Show transaction history for auto-trade."""
    from simulation.database import get_latest_autotrade_run

    run_data = get_latest_autotrade_run()
    if not run_data:
        print("  No auto-trade history found.")
        return

    txns = run_data["transactions"]
    if not txns:
        print("  No transactions yet.")
        return

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           AUTO-TRADE TRANSACTION HISTORY                    ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    print(f"  {'Date':12s} {'Action':6s} {'Symbol':8s} {'Shares':>8s} {'Price':>10s} {'Value':>10s} {'Verdict':>12s} Reason")
    print(f"  {'─' * 90}")

    for t in txns:
        icon = "🟢" if t["action"] == "BUY" else "🔴"
        print(f"  {t['date']:12s} {icon} {t['action']:4s} {t['symbol']:8s} "
              f"{t['shares']:>8.1f} ${t['price']:>9.2f} ${t['value']:>9.0f} "
              f"{t.get('verdict', ''):>12s} {t.get('reason', '')}")

    print(f"\n  Total transactions: {len(txns)}")
    print()

def show_runs(args):
    """List all saved simulation runs."""
    from simulation.database import list_runs

    runs = list_runs(limit=30)
    if not runs:
        print("  No simulation runs found.")
        return

    print(f"\n  {'ID':>4s} {'Type':12s} {'Name':30s} {'Period':25s} {'Return':>10s} {'Value':>12s}")
    print(f"  {'─' * 95}")

    for r in runs:
        period = f"{r['start_date']} → {r.get('end_date', '?')}"
        ret_str = f"{r['total_return_pct']:+.1f}%" if r.get("total_return_pct") is not None else "N/A"
        val_str = f"${r['final_value']:,.0f}" if r.get("final_value") else "N/A"
        print(f"  {r['id']:>4d} {r['run_type']:12s} {r['name']:30s} {period:25s} {ret_str:>10s} {val_str:>12s}")

    print()

def reset_portfolio(args):
    """Reset the auto-trade portfolio (start fresh)."""
    from simulation.database import list_runs, delete_run

    runs = list_runs(run_type="autotrade")
    if not runs:
        print("  No auto-trade portfolio to reset.")
        return

    # Delete latest run
    latest = runs[0]
    confirm = input(f"  Delete auto-trade run '{latest['name']}' (ID: {latest['id']})? [y/N] ").strip().lower()
    if confirm == "y":
        delete_run(latest["id"])
        print("  Auto-trade portfolio reset. Run 'python stock.py autotrade' to start fresh.")
    else:
        print("  Cancelled.")

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        run_autotrade([])
        return

    subcmd = args[0].lower()

    if subcmd == "status":
        show_status(args[1:])
    elif subcmd == "history":
        show_history(args[1:])
    elif subcmd == "runs":
        show_runs(args[1:])
    elif subcmd == "reset":
        reset_portfolio(args[1:])
    else:
        # Everything else passed to run_autotrade
        run_autotrade(args)
