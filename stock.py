#!/usr/bin/env python3
"""
Unified CLI — single entry point for the Stock Screener toolkit.

Usage:
    python stock.py analyze [TICKERS...]       Fundamental analysis (EPS, ROE, FCF, BAL, DIV, DCF)
    python stock.py technical [TICKERS...]     Technical entry-timing signals (RSI, SMA, BB, MACD)
    python stock.py macro                      Global macro environment dashboard
    python stock.py verdict [TICKERS...]       Triangulated verdict (Fund+Tech+Macro)
    python stock.py screen [PRESET]            Discover candidates via Finviz
    python stock.py history [TICKER|--movers]  Browse score history from SQLite
    python stock.py deepdive TICKER            Manual due-diligence checklist
    python stock.py chart TICKER [TICKER...]   Generate score trend chart
    python stock.py cache [clear|stats]        Manage API cache

    python stock.py portfolio [sub]            Manage & analyze stocks you OWN
    python stock.py watchlist [sub]            Manage & analyze stocks you WATCH
    python stock.py discover [--analyze]       Find new investment ideas (Finviz)
    python stock.py compare <A> <B>            Side-by-side comparison

    python stock.py autotrade                  Auto-trade using verdict signals
    python stock.py backtest [TICKERS] --period 2y  Historical strategy backtest
    python stock.py strategy                   Strategy reports & rule analysis

    python stock.py daily                      Quick morning check (~30s)
    python stock.py weekly                     Portfolio + watchlist review (~2min)
    python stock.py monthly                    Full review + discover (~5min)

    python stock.py                            Show this help
"""

import sys


def _help():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           STOCK SCREENER — Unified CLI                      ║
╚══════════════════════════════════════════════════════════════════════╝

Commands:

  analyze [tickers|file.txt]     Deep fundamental analysis
                                 Scores EPS, ROE, FCF, Balance Sheet,
                                 Dividends, and DCF intrinsic value.
                                 Saves results to scores.db.

  technical [tickers|portfolio|  Technical entry-timing analysis
    watchlist]                   RSI(14), SMA(50/200), Bollinger Bands,
                                 MACD crossover, 52-week position.
                                 Tech Score 0-100 (higher = buy signal).

  macro [--compact]              Global macro environment dashboard
                                 VIX, yields, S&P/STOXX/Nikkei/EM,
                                 commodities, USD. Macro Score 0-100.
                                 --compact for one-section summary.

  verdict [tickers|--portfolio|  Triangulated verdict — convergence of
    --watchlist|--all]           Fundamental + Technical + Macro scores.
                                 Zone each score, check pairwise
                                 convergence, produce verdict + sizing.

  screen [preset]                Discover new candidates via Finviz
                                 Presets: quality, high_roe, fcf_machines, ...
                                 Use 'screen --list' to see all presets.

  history [ticker|--movers]      Browse historical scores from SQLite
                                 No args = latest scores + movers
                                 Ticker = score history over time
                                 --movers = biggest score changes

  deepdive TICKER                Manual due-diligence checklist
                                 Tailored fundamental research guide
                                 with 10 sections based on actual data.

  chart TICKER [TICKER...]       Generate score trend chart (PNG)
                                 Requires 2+ data points per ticker.

  cache [clear|stats]            Manage yfinance API response cache

  config [show|init|path]        Manage configuration
                                 show = display current settings
                                 init = create config.yaml with defaults
                                 path = show config file location

  alerts                         Price target alerts
                                 Shows undervalued stocks, bargains,
                                 and significant score drops.

  ── Portfolio / Watchlist ──────────────────────────────
  portfolio                      Analyze stocks you OWN + alerts + P&L
  portfolio list|add|remove      Manage portfolio tickers
  portfolio buy AAPL --shares 10 Paper buy (auto-fetches price)
  portfolio sell AAPL --shares 5 Paper sell
  portfolio pnl                  P&L + total return vs SPY
  portfolio positions            Show open positions
  portfolio transactions         Transaction history

  watchlist                      Analyze & rank stocks you WATCH
  watchlist list|add|remove      Manage watchlist tickers

  discover                       Scan all Finviz presets, find new ideas
  discover --analyze             Also auto-analyze top candidates

  compare portfolio watchlist    Side-by-side comparison
  compare AAPL,MSFT GOOGL,META  Compare two ticker groups
  compare portfolio other.txt   Compare vs external file

  ── Simulation / Auto-Trading ─────────────────────────
  autotrade                      Run auto-trade cycle on watchlist
  autotrade status               Show sim portfolio status
  autotrade history              Show sim transaction history
  autotrade reset                Reset sim portfolio

  backtest AAPL MSFT --period 2y Historical backtest with verdict rules
  backtest --watchlist --period 1y  Backtest your watchlist
  backtest --runs                List saved backtest runs
  backtest --show <ID>           Show backtest details

  strategy                       Strategy dashboard overview
  strategy report [ID]           Detailed performance report
  strategy rules                 Rule effectiveness analysis
  strategy journal [ID]          Trade journal with reasoning
  strategy compare               Compare simulation runs

  ── Workflows ─────────────────────────────────────────
  daily                          Quick morning check (~30s)
                                 Portfolio summary + alerts (compact)

  weekly                         Weekly review (~2min)
                                 Portfolio + watchlist summaries,
                                 buying opportunities, score movers

  monthly                        Full review (~5min)
                                 Discover + full portfolio analysis
                                 + watchlist + compare + CSV export

  ── Data & ML ─────────────────────────────────────────
  collect [tickers]              Collect data for continuous learning
  collect --backfill             Backfill 5y prices + quarterly data
  collect --macro                Refresh macro indicators only
  collect --stats                Show data coverage report

  study                          ML parameter correlation study
  study --quick                  Quick mode (15 tickers)
  study --tickers 50             Larger universe

  ── Recommended Frequency ─────────────────────────────
  daily        → every 1–2 days  (your money, compact)
  weekly       → weekly          (entry points)
  monthly      → bi-weekly       (new ideas + full review)
  discover     → on demand

Examples:
  python stock.py daily                        # quick morning check
  python stock.py weekly                       # weekly review
  python stock.py monthly                      # full monthly review
  python stock.py analyze AAPL MSFT GOOGL
  python stock.py analyze                      # uses portfolio + watchlist
  python stock.py analyze AAPL --summary       # compact summary only
  python stock.py screen high_roe
  python stock.py history AAPL
  python stock.py history --movers
  python stock.py deepdive V
  python stock.py chart AAPL MSFT
  python stock.py cache stats
  python stock.py technical AAPL                  # entry timing signals
  python stock.py technical portfolio              # check portfolio entries
  python stock.py macro                            # global macro dashboard
  python stock.py macro --compact                  # compact macro summary
  python stock.py verdict AAPL                     # triangulated verdict
  python stock.py verdict --portfolio              # portfolio verdicts
  python stock.py alerts
  python stock.py autotrade                        # auto-trade cycle
  python stock.py autotrade status                 # sim portfolio status
  python stock.py backtest --watchlist --period 2y  # 2-year backtest
  python stock.py backtest AAPL MSFT --period 1y   # backtest specific stocks
  python stock.py strategy                         # strategy dashboard
  python stock.py strategy rules                   # which rules work?
""")


# ── Command dispatch ─────────────────────────────────────────────────

# Standard commands: call module.main(args)
_CMD_MODULES = {
    "analyze": "commands.analyze",
    "screen": "commands.discover",
    "history": "commands.history",
    "deepdive": "commands.deepdive",
    "alerts": "commands.alerts",
    "portfolio": "commands.portfolio",
    "watchlist": "commands.watchlist",
    "discover": "commands.discover",
    "compare": "commands.compare",
    "technical": "commands.technical",
    "macro": "commands.macro",
    "verdict": "commands.verdict",
    "autotrade": "commands.autotrade",
    "backtest": "commands.backtest",
    "study": "commands.study",
    "collect": "commands.collect",
    "report": "commands.report",
    "strategy": "commands.strategy",
}

# Single-letter aliases
_ALIASES = {
    "a": "analyze", "s": "screen", "h": "history", "d": "deepdive",
    "c": "chart", "p": "portfolio", "t": "technical", "m": "macro",
    "v": "verdict", "w": "watchlist",
}


def _run_command(command, args):
    """Dispatch a command: lazy-import its module and call main(args)."""
    from importlib import import_module

    command = _ALIASES.get(command, command)

    # Standard commands: import module, call main(args)
    if command in _CMD_MODULES:
        import_module(_CMD_MODULES[command]).main(args)
        return True

    # Workflow shortcuts (no args — call function directly)
    if command in ("daily", "weekly", "monthly"):
        getattr(import_module("commands.workflow"), command)()
        return True

    # Chart (inline — no commands/ module)
    if command == "chart":
        if not args:
            print("Usage: python stock.py chart TICKER [TICKER...]")
            return True
        from utils.chart import chart_from_db
        chart_from_db([s.upper().strip() for s in args])
        return True

    # Cache management (inline)
    if command == "cache":
        from utils.config import clear_cache, cache_stats
        if not args or args[0] == "stats":
            cache_stats()
        elif args[0] == "clear":
            clear_cache()
        else:
            print(f"Unknown cache command: {args[0]}")
        return True

    # Config management (inline)
    if command == "config":
        from utils.config import save_default_config, load_config, CONFIG_PATH
        if not args or args[0] == "show":
            import json
            print(json.dumps(load_config(), indent=2))
        elif args[0] == "init":
            save_default_config()
        elif args[0] == "path":
            print(CONFIG_PATH)
        else:
            print(f"Unknown config command: {args[0]}")
        return True

    return False


def main():
    import warnings
    warnings.filterwarnings("ignore")

    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "help"):
        _help()
        return

    command = args[0].lower()
    rest = args[1:]

    if _run_command(command, rest):
        return

    # If args look like tickers (all caps, short), assume 'analyze'
    if all(len(a) <= 6 and a.replace("-", "").isalpha() for a in args):
        _run_command("analyze", args)
    else:
        all_cmds = sorted(set(list(_CMD_MODULES) + ["chart", "cache", "config", "daily", "weekly", "monthly"]))
        print(f"Unknown command: '{command}'")
        print(f"Available: {', '.join(all_cmds)}")
        print("Run 'python stock.py --help' for full usage.")


if __name__ == "__main__":
    main()
