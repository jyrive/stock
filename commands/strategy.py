"""strategy command: reporting, analysis, and rule-improvement insights.

Provides comprehensive reports on auto-trade and backtest performance,
compares against benchmarks with total-return accounting, and analyzes
which scoring components best predict winners vs losers.

Usage:
    python stock.py strategy                    Dashboard overview
    python stock.py strategy report [run_id]    Detailed report for a run
    python stock.py strategy compare            Compare recent runs
    python stock.py strategy rules              Rule effectiveness analysis
    python stock.py strategy journal            Trade journal with reasoning
"""

import sys
import json
from datetime import date

def _get_run_data(run_id=None):
    """Load a run from the database."""
    from simulation.database import get_run, get_latest_autotrade_run, list_runs

    if run_id:
        return get_run(run_id)

    # Default to latest autotrade, then latest backtest
    data = get_latest_autotrade_run()
    if data:
        return data

    runs = list_runs(limit=1)
    if runs:
        return get_run(runs[0]["id"])

    return None

def dashboard(args):
    """Show a strategy dashboard overview."""
    from simulation.database import list_runs

    at_runs = list_runs(run_type="autotrade", limit=5)
    bt_runs = list_runs(run_type="backtest", limit=5)

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           STRATEGY DASHBOARD                               ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    if not at_runs and not bt_runs:
        print("  No simulation runs found yet.")
        print("  Start with: python stock.py autotrade")
        print("  Or:         python stock.py backtest --watchlist --period 1y\n")
        return

    # Auto-trade summary
    if at_runs:
        print("  📊 AUTO-TRADE RUNS")
        print(f"  {'─' * 55}")
        for r in at_runs:
            ret = r.get("total_return_pct")
            ret_str = f"{ret:+.1f}%" if ret is not None else "N/A"
            val_str = f"${r.get('final_value', 0):,.0f}" if r.get("final_value") else "N/A"
            color = "\033[92m" if (ret or 0) >= 0 else "\033[91m"
            print(f"    #{r['id']:3d}  {r['name'][:30]:30s}  {color}{ret_str:>8s}\033[0m  {val_str:>10s}")
        print()

    # Backtest summary
    if bt_runs:
        print("  🔬 BACKTEST RUNS")
        print(f"  {'─' * 55}")
        for r in bt_runs:
            ret = r.get("total_return_pct")
            ret_str = f"{ret:+.1f}%" if ret is not None else "N/A"
            val_str = f"${r.get('final_value', 0):,.0f}" if r.get("final_value") else "N/A"
            color = "\033[92m" if (ret or 0) >= 0 else "\033[91m"
            print(f"    #{r['id']:3d}  {r['name'][:30]:30s}  {color}{ret_str:>8s}\033[0m  {val_str:>10s}")
        print()

    # Best and worst
    all_runs = at_runs + bt_runs
    valid = [r for r in all_runs if r.get("total_return_pct") is not None]
    if valid:
        best = max(valid, key=lambda r: r["total_return_pct"])
        worst = min(valid, key=lambda r: r["total_return_pct"])
        print(f"  Best run:  #{best['id']} {best['name'][:25]}  {best['total_return_pct']:+.1f}%")
        print(f"  Worst run: #{worst['id']} {worst['name'][:25]}  {worst['total_return_pct']:+.1f}%")

    print(f"\n  Commands:")
    print(f"    python stock.py strategy report [ID]     Detailed report")
    print(f"    python stock.py strategy rules            Rule analysis")
    print(f"    python stock.py strategy journal [ID]     Trade journal")
    print(f"    python stock.py strategy compare          Compare runs\n")

def report(args):
    """Generate a detailed strategy report for a run."""
    from utils.benchmark import get_benchmark_returns, compute_alpha, print_benchmark_comparison
    from utils.config import config

    run_id = int(args[0]) if args else None
    data = _get_run_data(run_id)

    if not data:
        print("  No run data found. Run a backtest or autotrade first.")
        return

    run = data["run"]
    metrics = json.loads(run.get("metrics_json", "{}"))
    txns = data["transactions"]
    curve = data["equity_curve"]
    holdings = data["holdings"]

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           STRATEGY REPORT — Run #{run['id']}                        ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    # Overview
    print(f"  Type: {run['run_type'].upper()}")
    print(f"  Name: {run['name']}")
    print(f"  Period: {run['start_date']} → {run.get('end_date', 'ongoing')}")

    ret = run.get("total_return_pct", 0)
    color = "\033[92m" if ret >= 0 else "\033[91m"
    print(f"\n  ── Performance ────────────────────────────────────────────")
    print(f"  Starting capital: ${run['starting_cash']:,.0f}")
    print(f"  Final value:      ${run.get('final_value', 0):,.0f}")
    print(f"  Total return:     {color}{ret:+.2f}%\033[0m")
    if metrics.get("annualized_return_pct") is not None:
        print(f"  Annualized:       {metrics['annualized_return_pct']:+.2f}%")
    if metrics.get("max_drawdown_pct") is not None:
        print(f"  Max drawdown:     {metrics['max_drawdown_pct']:.1f}%")
    if metrics.get("sharpe_ratio") is not None:
        print(f"  Sharpe ratio:     {metrics['sharpe_ratio']:.2f}")

    # Trading stats
    buys = [t for t in txns if t["action"] == "BUY"]
    sells = [t for t in txns if t["action"] == "SELL"]

    print(f"\n  ── Trading Activity ──────────────────────────────────────")
    print(f"  Total trades:     {len(txns)} ({len(buys)} buys, {len(sells)} sells)")
    if metrics.get("win_rate_pct") is not None:
        print(f"  Win rate:         {metrics['win_rate_pct']:.0f}%  ({metrics.get('wins', 0)}W / {metrics.get('losses', 0)}L)")
    if metrics.get("total_dividends", 0) > 0:
        print(f"  Dividends:        ${metrics['total_dividends']:,.2f}")

    # Turnover
    total_bought = sum(t["value"] for t in buys)
    total_sold = sum(t["value"] for t in sells)
    if metrics.get("days") and metrics["days"] > 0:
        years = metrics["days"] / 365.25
        turnover = (total_sold / run["starting_cash"]) / years if years > 0 else 0
        print(f"  Annual turnover:  {turnover:.1f}x")

    # Verdict distribution
    if txns:
        print(f"\n  ── Verdict Distribution (at trade time) ─────────────────")
        verdict_counts = {}
        for t in txns:
            v = t.get("verdict", "N/A")
            verdict_counts[v] = verdict_counts.get(v, 0) + 1
        for v in sorted(verdict_counts.keys(), key=lambda x: verdict_counts[x], reverse=True):
            bar = "█" * min(30, verdict_counts[v])
            print(f"  {v:12s} {verdict_counts[v]:3d}  {bar}")

    # Per-stock P&L
    if sells:
        print(f"\n  ── Per-Stock P&L (closed trades) ────────────────────────")
        stock_pnl = {}
        buy_tracker = {}  # symbol -> list of (shares, price)

        for t in txns:
            sym = t["symbol"]
            if t["action"] == "BUY":
                buy_tracker.setdefault(sym, []).append((t["shares"], t["price"]))
            elif t["action"] == "SELL":
                cost = 0
                sell_shares = t["shares"]
                # FIFO cost basis
                while sell_shares > 0 and buy_tracker.get(sym):
                    b_shares, b_price = buy_tracker[sym][0]
                    used = min(sell_shares, b_shares)
                    cost += used * b_price
                    sell_shares -= used
                    if used >= b_shares:
                        buy_tracker[sym].pop(0)
                    else:
                        buy_tracker[sym][0] = (b_shares - used, b_price)

                pnl = t["value"] - cost + t.get("dividends", 0)
                stock_pnl[sym] = stock_pnl.get(sym, 0) + pnl

        # Sort by P&L
        sorted_pnl = sorted(stock_pnl.items(), key=lambda x: x[1], reverse=True)
        print(f"  {'Symbol':8s} {'P&L':>10s}")
        print(f"  {'─' * 20}")
        for sym, pnl in sorted_pnl[:15]:
            color = "\033[92m" if pnl >= 0 else "\033[91m"
            print(f"  {sym:8s} {color}${pnl:>+9,.0f}\033[0m")
        if len(sorted_pnl) > 15:
            print(f"  ... and {len(sorted_pnl) - 15} more")

    # Benchmark comparison
    if run.get("start_date"):
        sim_cfg = config().get("simulation", {})
        benchmarks = sim_cfg.get("benchmarks", ["SPY", "QQQ", "VT"])
        print(f"\n  Fetching benchmarks...")
        bench = get_benchmark_returns(benchmarks, run["start_date"], run.get("end_date"))
        alpha = compute_alpha(ret, bench)
        print_benchmark_comparison(metrics, bench, alpha)

    # Current holdings
    if holdings:
        print(f"  Open positions ({len(holdings)}):")
        for h in sorted(holdings, key=lambda x: x["symbol"]):
            div_str = f" +${h.get('dividends', 0):,.0f} div" if h.get("dividends", 0) > 0 else ""
            print(f"    {h['symbol']:8s} {h['shares']:>6.1f} shares @ ${h['avg_cost']:.2f}{div_str}")

    print()

def trade_journal(args):
    """Show a chronological trade journal with reasoning."""
    run_id = int(args[0]) if args else None
    data = _get_run_data(run_id)

    if not data:
        print("  No run data found.")
        return

    txns = data["transactions"]
    if not txns:
        print("  No trades recorded.")
        return

    run = data["run"]
    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           TRADE JOURNAL — Run #{run['id']}                          ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    current_date = ""
    for t in txns:
        if t["date"] != current_date:
            current_date = t["date"]
            print(f"\n  ── {current_date} ──────────────────────────────────────────")

        icon = "🟢 BUY " if t["action"] == "BUY" else "🔴 SELL"
        scores = []
        if t.get("fund_score") is not None:
            scores.append(f"F:{t['fund_score']:.0f}")
        if t.get("tech_score") is not None:
            scores.append(f"T:{t['tech_score']:.0f}")
        if t.get("macro_score") is not None:
            scores.append(f"M:{t['macro_score']:.0f}")
        score_str = " | ".join(scores) if scores else ""

        print(f"    {icon} {t['symbol']:6s}  {t['shares']:>6.1f} shares @ ${t['price']:>8.2f}  (${t['value']:>8,.0f})")
        print(f"           Verdict: {t.get('verdict', 'N/A'):12s}  [{score_str}]")
        if t.get("reason"):
            print(f"           Reason:  {t['reason']}")
        if t.get("dividends", 0) > 0:
            print(f"           Dividends collected: ${t['dividends']:,.2f}")

    print()

def analyze_rules(args):
    """Analyze which scoring rules predict winners vs losers.

    Correlates scores at buy-time with subsequent trade outcomes
    to highlight which scoring components are most predictive.
    """
    from simulation.database import list_runs, get_run

    # Gather all completed trades from all runs
    all_trades = []
    runs = list_runs(limit=50)

    for r in runs:
        data = get_run(r["id"])
        if not data:
            continue

        txns = data["transactions"]
        buy_tracker = {}

        for t in txns:
            sym = t["symbol"]
            if t["action"] == "BUY":
                buy_tracker.setdefault(sym, []).append(t)
            elif t["action"] == "SELL":
                # Match with most recent buy
                if buy_tracker.get(sym):
                    buy = buy_tracker[sym].pop(0)
                    pnl_pct = (t["price"] / buy["price"] - 1) * 100 if buy["price"] > 0 else 0
                    div_pct = (t.get("dividends", 0) / (buy["shares"] * buy["price"])) * 100 if buy["price"] > 0 else 0
                    total_return = pnl_pct + div_pct
                    all_trades.append({
                        "symbol": sym,
                        "buy_date": buy["date"],
                        "sell_date": t["date"],
                        "buy_price": buy["price"],
                        "sell_price": t["price"],
                        "verdict_at_buy": buy.get("verdict", "N/A"),
                        "verdict_at_sell": t.get("verdict", "N/A"),
                        "fund_score": buy.get("fund_score"),
                        "tech_score": buy.get("tech_score"),
                        "macro_score": buy.get("macro_score"),
                        "pnl_pct": pnl_pct,
                        "div_pct": div_pct,
                        "total_return_pct": total_return,
                        "is_winner": total_return >= 0,
                    })

    if not all_trades:
        print("  No completed trades found for analysis.")
        print("  Run backtests first: python stock.py backtest --watchlist --period 2y")
        return

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           RULE EFFECTIVENESS ANALYSIS                       ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    winners = [t for t in all_trades if t["is_winner"]]
    losers = [t for t in all_trades if not t["is_winner"]]

    print(f"  Total closed trades analyzed: {len(all_trades)}")
    print(f"  Winners: {len(winners)} ({len(winners) / len(all_trades) * 100:.0f}%)")
    print(f"  Losers:  {len(losers)} ({len(losers) / len(all_trades) * 100:.0f}%)")

    avg_win = sum(t["total_return_pct"] for t in winners) / len(winners) if winners else 0
    avg_loss = sum(t["total_return_pct"] for t in losers) / len(losers) if losers else 0
    print(f"  Avg winner: {avg_win:+.1f}%")
    print(f"  Avg loser:  {avg_loss:+.1f}%")

    # ── Verdict effectiveness
    print(f"\n  ── Verdict at Buy Time → Outcome ────────────────────────")
    verdict_stats = {}
    for t in all_trades:
        v = t["verdict_at_buy"]
        if v not in verdict_stats:
            verdict_stats[v] = {"wins": 0, "losses": 0, "returns": []}
        if t["is_winner"]:
            verdict_stats[v]["wins"] += 1
        else:
            verdict_stats[v]["losses"] += 1
        verdict_stats[v]["returns"].append(t["total_return_pct"])

    print(f"  {'Verdict':12s} {'Trades':>7s} {'Win%':>7s} {'Avg Ret':>9s} {'Recommendation':>20s}")
    print(f"  {'─' * 58}")

    for v in ("STRONG BUY", "BUY", "ACCUMULATE", "NEUTRAL", "WATCH", "HOLD", "AVOID"):
        if v not in verdict_stats:
            continue
        s = verdict_stats[v]
        total = s["wins"] + s["losses"]
        win_pct = s["wins"] / total * 100 if total > 0 else 0
        avg_ret = sum(s["returns"]) / len(s["returns"]) if s["returns"] else 0
        # Recommendation
        if win_pct >= 60 and avg_ret > 0:
            rec = "✅ Keep"
        elif win_pct < 40 or avg_ret < -5:
            rec = "❌ Tighten criteria"
        else:
            rec = "🔍 Review"
        color = "\033[92m" if avg_ret >= 0 else "\033[91m"
        print(f"  {v:12s} {total:>7d} {win_pct:>6.0f}% {color}{avg_ret:>+8.1f}%\033[0m {rec:>20s}")

    # ── Score component analysis
    print(f"\n  ── Score Component → Outcome Correlation ─────────────────")
    print(f"  Higher score at buy time → better returns?")
    print()

    for score_name, score_key in [
        ("Fundamental", "fund_score"),
        ("Technical", "tech_score"),
        ("Macro", "macro_score"),
    ]:
        scored_trades = [t for t in all_trades if t.get(score_key) is not None]
        if len(scored_trades) < 5:
            continue

        # Split into high/low halves
        scored_trades.sort(key=lambda x: x[score_key])
        mid = len(scored_trades) // 2
        low_half = scored_trades[:mid]
        high_half = scored_trades[mid:]

        avg_low = sum(t["total_return_pct"] for t in low_half) / len(low_half)
        avg_high = sum(t["total_return_pct"] for t in high_half) / len(high_half)
        low_win = sum(1 for t in low_half if t["is_winner"]) / len(low_half) * 100
        high_win = sum(1 for t in high_half if t["is_winner"]) / len(high_half) * 100

        # Score ranges
        low_range = f"{scored_trades[0][score_key]:.0f}-{scored_trades[mid-1][score_key]:.0f}"
        high_range = f"{scored_trades[mid][score_key]:.0f}-{scored_trades[-1][score_key]:.0f}"

        predictive = "✅ Predictive" if avg_high > avg_low + 2 else "⚠️  Weak" if abs(avg_high - avg_low) < 2 else "❌ Inverse!"
        direction = "↑" if avg_high > avg_low else "↓"

        print(f"  {score_name}:")
        print(f"    Low  ({low_range:>8s}): {avg_low:>+6.1f}% avg ret, {low_win:.0f}% win rate")
        print(f"    High ({high_range:>8s}): {avg_high:>+6.1f}% avg ret, {high_win:.0f}% win rate")
        print(f"    {direction} {predictive}")
        print()

    # ── Recommendations
    print(f"  ── Recommendations ──────────────────────────────────────")
    print()

    # Check if veto is too aggressive or not aggressive enough
    veto_trades = [t for t in all_trades if t["verdict_at_buy"] == "WATCH"]
    if veto_trades:
        veto_win = sum(1 for t in veto_trades if t["is_winner"]) / len(veto_trades) * 100
        if veto_win > 60:
            print("  💡 WATCH-verdict trades are winning — consider RELAXING the veto")
            print("     threshold (currently <25) to allow more trades through.")
        elif veto_win < 30:
            print("  ✅ WATCH-verdict veto is working — it correctly blocks bad trades.")

    # Check if macro multiplier helps
    macro_trades = [t for t in all_trades if t.get("macro_score") is not None]
    if len(macro_trades) >= 10:
        high_macro = [t for t in macro_trades if t["macro_score"] >= 60]
        low_macro = [t for t in macro_trades if t["macro_score"] < 40]
        if high_macro and low_macro:
            high_ret = sum(t["total_return_pct"] for t in high_macro) / len(high_macro)
            low_ret = sum(t["total_return_pct"] for t in low_macro) / len(low_macro)
            if high_ret > low_ret + 3:
                print("  ✅ Macro filter is adding value — high-macro trades outperform.")
            elif abs(high_ret - low_ret) < 2:
                print("  ⚠️  Macro filter shows little impact — consider reducing macro weight.")
            else:
                print("  ❌ Higher macro scores correlate with WORSE returns.")
                print("     Consider inverting or removing the macro multiplier.")

    # Check stop-loss effectiveness
    stop_trades = [t for t in all_trades if "stop-loss" in t.get("verdict_at_sell", "").lower()
                   or "stop" in (t.get("verdict_at_sell", "")).lower()]
    if len(stop_trades) >= 3:
        avoided_further_loss = sum(1 for t in stop_trades if t["total_return_pct"] < -10)
        print(f"\n  Stop-loss fired {len(stop_trades)} times. "
              f"{avoided_further_loss} may have prevented larger losses.")

    print()

def compare_runs(args):
    """Compare multiple simulation runs side by side."""
    from simulation.database import list_runs

    runs = list_runs(limit=10)
    if len(runs) < 2:
        print("  Need at least 2 runs to compare. Run more backtests first.")
        return

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           RUN COMPARISON                                    ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    print(f"  {'ID':>4s} {'Type':10s} {'Return':>10s} {'Ann.Ret':>10s} {'Max DD':>10s} {'Sharpe':>8s} {'Trades':>8s} {'Win%':>7s}")
    print(f"  {'─' * 70}")

    for r in runs:
        metrics = json.loads(r.get("metrics_json", "{}")) if r.get("metrics_json") else {}
        ret = r.get("total_return_pct")
        ret_str = f"{ret:+.1f}%" if ret is not None else "N/A"
        ann = metrics.get("annualized_return_pct")
        ann_str = f"{ann:+.1f}%" if ann is not None else "N/A"
        dd = metrics.get("max_drawdown_pct")
        dd_str = f"{dd:.1f}%" if dd is not None else "N/A"
        sharpe = metrics.get("sharpe_ratio")
        sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "N/A"
        trades = metrics.get("total_trades", 0)
        win = metrics.get("win_rate_pct")
        win_str = f"{win:.0f}%" if win is not None else "N/A"

        color = "\033[92m" if (ret or 0) >= 0 else "\033[91m"
        print(f"  {r['id']:>4d} {r['run_type']:10s} {color}{ret_str:>10s}\033[0m {ann_str:>10s} {dd_str:>10s} {sharpe_str:>8s} {trades:>8d} {win_str:>7s}")

    print()

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        dashboard([])
        return

    subcmd = args[0].lower()

    if subcmd == "report":
        report(args[1:])
    elif subcmd == "compare":
        compare_runs(args[1:])
    elif subcmd in ("rules", "effectiveness"):
        analyze_rules(args[1:])
    elif subcmd == "journal":
        trade_journal(args[1:])
    else:
        dashboard(args)
