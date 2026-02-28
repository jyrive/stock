#!/usr/bin/env python3
"""
Unified CLI — single entry point for the Buffett Stock Screener toolkit.

Usage:
    python stock.py analyze [TICKERS...]       Fundamental analysis (EPS, ROE, FCF, BAL, DIV, DCF)
    python stock.py technical [TICKERS...]     Technical entry-timing signals (RSI, SMA, BB, MACD)
    python stock.py screen [PRESET]            Discover candidates via Finviz
    python stock.py history [TICKER|--movers]  Browse score history from SQLite
    python stock.py deepdive TICKER            Manual due-diligence checklist
    python stock.py chart TICKER [TICKER...]   Generate score trend chart
    python stock.py cache [clear|stats]        Manage API cache

    python stock.py portfolio [sub]            Manage & analyze stocks you OWN
    python stock.py watchlist [sub]            Manage & analyze stocks you WATCH
    python stock.py discover [--analyze]       Find new investment ideas (Finviz)
    python stock.py compare <A> <B>            Side-by-side comparison

    python stock.py daily                      Quick morning check (~30s)
    python stock.py weekly                     Portfolio + watchlist review (~2min)
    python stock.py monthly                    Full review + discover (~5min)

    python stock.py                            Show this help
"""

import sys


def _help():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           BUFFETT STOCK SCREENER — Unified CLI                      ║
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

  screen [preset]                Discover new candidates via Finviz
                                 Presets: buffett, high_roe, fcf_machines, ...
                                 Use 'screen --list' to see all presets.

  history [ticker|--movers]      Browse historical scores from SQLite
                                 No args = latest scores + movers
                                 Ticker = score history over time
                                 --movers = biggest score changes

  deepdive TICKER                Manual due-diligence checklist
                                 Tailored Buffett-style research guide
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
  portfolio                      Analyze stocks you OWN + alerts
  portfolio list|add|remove      Manage portfolio tickers
  portfolio buy TICKER           Move from watchlist → portfolio
  portfolio sell TICKER          Move to watchlist (keep watching)

  watchlist                      Analyze & rank stocks you WATCH
  watchlist list|add|remove      Manage watchlist tickers

  discover                       Scan all Finviz presets, find new ideas
  discover --analyze             Also auto-analyze top candidates

  compare portfolio watchlist    Side-by-side comparison
  compare AAPL,MSFT GOOGL,META  Compare two ticker groups
  compare portfolio other.txt   Compare vs external file

  ── Workflows ─────────────────────────────────────────
  daily                          Quick morning check (~30s)
                                 Portfolio summary + alerts (compact)

  weekly                         Weekly review (~2min)
                                 Portfolio + watchlist summaries,
                                 buying opportunities, score movers

  monthly                        Full review (~5min)
                                 Discover + full portfolio analysis
                                 + watchlist + compare + CSV export

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
  python stock.py analyze                      # uses tickers.txt
  python stock.py analyze AAPL --summary       # compact summary only
  python stock.py screen high_roe
  python stock.py history AAPL
  python stock.py history --movers
  python stock.py deepdive V
  python stock.py chart AAPL MSFT
  python stock.py cache stats
  python stock.py technical AAPL                  # entry timing signals
  python stock.py technical portfolio              # check portfolio entries
  python stock.py alerts
""")


def cmd_analyze(args):
    """Run fundamental analysis."""
    # Reuse analyze.py logic by importing its main
    sys.argv = ["analyze.py"] + args
    from commands.analyze import main
    main()


def cmd_screen(args):
    """Run Finviz discovery."""
    sys.argv = ["screen.py"] + args
    from commands.screen import main
    main()


def cmd_history(args):
    """Browse score history."""
    sys.argv = ["history.py"] + args
    from commands.history import main
    main()


def cmd_deepdive(args):
    """Run deep-dive guide."""
    if not args:
        print("Usage: python stock.py deepdive TICKER")
        print("Example: python stock.py deepdive AAPL")
        return
    sys.argv = ["deepdive.py"] + args
    from commands.deepdive import main
    main()


def cmd_chart(args):
    """Generate score trend chart."""
    if not args:
        print("Usage: python stock.py chart TICKER [TICKER...]")
        print("Example: python stock.py chart AAPL MSFT")
        return

    from utils.chart import chart_from_db
    symbols = [s.upper().strip() for s in args]
    chart_from_db(symbols)


def cmd_cache(args):
    """Manage API cache."""
    from utils.cache import clear_cache, cache_stats

    if not args or args[0] == "stats":
        cache_stats()
    elif args[0] == "clear":
        clear_cache()
    else:
        print(f"Unknown cache command: {args[0]}")
        print("Usage: python stock.py cache [clear|stats]")


def cmd_alerts(args):
    """Run price target alerts."""
    sys.argv = ["alerts.py"] + args
    from commands.alerts import main
    main()


def cmd_portfolio(args):
    """Manage and analyze portfolio."""
    sys.argv = ["portfolio.py"] + args
    from commands.portfolio import main
    main()


def cmd_watchlist(args):
    """Manage and analyze watchlist."""
    sys.argv = ["watchlist.py"] + args
    from commands.watchlist import main
    main()


def cmd_discover(args):
    """Find new investment ideas via Finviz."""
    sys.argv = ["discover.py"] + args
    from commands.discover import main
    main()


def cmd_compare(args):
    """Side-by-side comparison."""
    sys.argv = ["compare.py"] + args
    from commands.compare import main
    main()


def cmd_technical(args):
    """Technical entry-timing analysis."""
    sys.argv = ["technical.py"] + args
    from commands.technical import main
    main()


def cmd_daily(args):
    """Daily portfolio check."""
    from commands.workflow import daily
    daily()


def cmd_weekly(args):
    """Weekly review."""
    from commands.workflow import weekly
    weekly()


def cmd_monthly(args):
    """Monthly full review."""
    from commands.workflow import monthly
    monthly()


def cmd_config(args):
    """Manage configuration."""
    from utils.config import save_default_config, load_config, CONFIG_PATH

    if not args or args[0] == "show":
        cfg = load_config()
        import json
        print(json.dumps(cfg, indent=2))
    elif args[0] == "init":
        save_default_config()
    elif args[0] == "path":
        print(CONFIG_PATH)
    else:
        print(f"Unknown config command: {args[0]}")
        print("Usage: python stock.py config [show|init|path]")


COMMANDS = {
    "analyze": cmd_analyze,
    "screen": cmd_screen,
    "history": cmd_history,
    "deepdive": cmd_deepdive,
    "chart": cmd_chart,
    "cache": cmd_cache,
    "config": cmd_config,
    "alerts": cmd_alerts,
    "portfolio": cmd_portfolio,
    "watchlist": cmd_watchlist,
    "discover": cmd_discover,
    "compare": cmd_compare,
    "technical": cmd_technical,
    "daily": cmd_daily,
    "weekly": cmd_weekly,
    "monthly": cmd_monthly,
}

# Aliases
COMMANDS["a"] = cmd_analyze
COMMANDS["s"] = cmd_screen
COMMANDS["h"] = cmd_history
COMMANDS["d"] = cmd_deepdive
COMMANDS["c"] = cmd_chart
COMMANDS["p"] = cmd_portfolio
COMMANDS["t"] = cmd_technical
COMMANDS["w"] = cmd_watchlist


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "help"):
        _help()
        return

    command = args[0].lower()
    rest = args[1:]

    if command in COMMANDS:
        COMMANDS[command](rest)
    else:
        # If args look like tickers (all caps, short), assume 'analyze'
        if all(len(a) <= 6 and a.replace("-", "").isalpha() for a in args):
            cmd_analyze(args)
        else:
            print(f"Unknown command: '{command}'")
            print(f"Available: {', '.join(k for k in COMMANDS if len(k) > 1)}")
            print("Run 'python stock.py --help' for full usage.")


if __name__ == "__main__":
    main()
