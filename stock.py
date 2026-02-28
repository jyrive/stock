#!/usr/bin/env python3
"""
Unified CLI — single entry point for the Buffett Stock Screener toolkit.

Usage:
    python stock.py analyze [TICKERS...]       Fundamental analysis (EPS, ROE, FCF, BAL, DIV, DCF)
    python stock.py screen [PRESET]            Discover candidates via Finviz
    python stock.py history [TICKER|--movers]  Browse score history from SQLite
    python stock.py deepdive TICKER            Manual due-diligence checklist
    python stock.py chart TICKER [TICKER...]   Generate score trend chart
    python stock.py cache [clear|stats]        Manage API cache

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

Examples:
  python stock.py analyze AAPL MSFT GOOGL
  python stock.py analyze                      # uses tickers.txt
  python stock.py screen high_roe
  python stock.py history AAPL
  python stock.py history --movers
  python stock.py deepdive V
  python stock.py chart AAPL MSFT
  python stock.py cache stats
""")


def cmd_analyze(args):
    """Run fundamental analysis."""
    # Reuse analyze.py logic by importing its main
    sys.argv = ["analyze.py"] + args
    from analyze import main
    main()


def cmd_screen(args):
    """Run Finviz discovery."""
    sys.argv = ["screen.py"] + args
    from screen import main
    main()


def cmd_history(args):
    """Browse score history."""
    sys.argv = ["history.py"] + args
    from history import main
    main()


def cmd_deepdive(args):
    """Run deep-dive guide."""
    if not args:
        print("Usage: python stock.py deepdive TICKER")
        print("Example: python stock.py deepdive AAPL")
        return
    sys.argv = ["deepdive.py"] + args
    from deepdive import main
    main()


def cmd_chart(args):
    """Generate score trend chart."""
    if not args:
        print("Usage: python stock.py chart TICKER [TICKER...]")
        print("Example: python stock.py chart AAPL MSFT")
        return

    from screener.chart import chart_from_db
    symbols = [s.upper().strip() for s in args]
    chart_from_db(symbols)


def cmd_cache(args):
    """Manage API cache."""
    from screener.cache import clear_cache, cache_stats

    if not args or args[0] == "stats":
        cache_stats()
    elif args[0] == "clear":
        clear_cache()
    else:
        print(f"Unknown cache command: {args[0]}")
        print("Usage: python stock.py cache [clear|stats]")


COMMANDS = {
    "analyze": cmd_analyze,
    "screen": cmd_screen,
    "history": cmd_history,
    "deepdive": cmd_deepdive,
    "chart": cmd_chart,
    "cache": cmd_cache,
}

# Aliases
COMMANDS["a"] = cmd_analyze
COMMANDS["s"] = cmd_screen
COMMANDS["h"] = cmd_history
COMMANDS["d"] = cmd_deepdive
COMMANDS["c"] = cmd_chart


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
