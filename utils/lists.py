"""Ticker list management and data fetching.

Portfolio/watchlist files live in the project root.  Format: one ticker
per line, # comments allowed, blank lines ignored.  Files are
auto-created on first use.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTFOLIO_PATH = os.path.join(_PROJECT_ROOT, "portfolio.txt")
WATCHLIST_PATH = os.path.join(_PROJECT_ROOT, "watchlist.txt")


def _ensure_file(path, header):
    """Create the file with a header comment if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(f"# {header}\n")
            f.write("# One ticker per line.  Lines starting with # are comments.\n\n")


def _read_tickers(path):
    """Read tickers from a file, preserving order, ignoring comments."""
    _ensure_file(path, os.path.basename(path))
    tickers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for t in line.split(","):
                t = t.strip().upper()
                if t and t not in tickers:
                    tickers.append(t)
    return tickers


def _write_tickers(path, tickers, header):
    """Rewrite the file with the given tickers (preserves header comment)."""
    with open(path, "w") as f:
        f.write(f"# {header}\n")
        f.write("# One ticker per line.  Lines starting with # are comments.\n\n")
        for t in tickers:
            f.write(f"{t}\n")


# ── Portfolio ────────────────────────────────────────────────────────


def portfolio_list():
    """Return list of portfolio tickers."""
    return _read_tickers(PORTFOLIO_PATH)


def portfolio_add(symbols):
    """Add symbols to portfolio.  Returns list of actually added."""
    current = _read_tickers(PORTFOLIO_PATH)
    added = []
    for s in symbols:
        s = s.upper().strip()
        if s and s not in current:
            current.append(s)
            added.append(s)
    _write_tickers(PORTFOLIO_PATH, current, "Portfolio — stocks you OWN")
    return added


def portfolio_remove(symbols):
    """Remove symbols from portfolio.  Returns list of actually removed."""
    current = _read_tickers(PORTFOLIO_PATH)
    removed = []
    for s in symbols:
        s = s.upper().strip()
        if s in current:
            current.remove(s)
            removed.append(s)
    _write_tickers(PORTFOLIO_PATH, current, "Portfolio — stocks you OWN")
    return removed


# ── Watchlist ────────────────────────────────────────────────────────


def watchlist_list():
    """Return list of watchlist tickers."""
    return _read_tickers(WATCHLIST_PATH)


def watchlist_add(symbols):
    """Add symbols to watchlist.  Returns list of actually added."""
    current = _read_tickers(WATCHLIST_PATH)
    added = []
    for s in symbols:
        s = s.upper().strip()
        if s and s not in current:
            current.append(s)
            added.append(s)
    _write_tickers(WATCHLIST_PATH, current, "Watchlist — stocks you're WATCHING")
    return added


def watchlist_remove(symbols):
    """Remove symbols from watchlist.  Returns list of actually removed."""
    current = _read_tickers(WATCHLIST_PATH)
    removed = []
    for s in symbols:
        s = s.upper().strip()
        if s in current:
            current.remove(s)
            removed.append(s)
    _write_tickers(WATCHLIST_PATH, current, "Watchlist — stocks you're WATCHING")
    return removed


# ── Ticker resolution ────────────────────────────────────────────────


def resolve_tickers(args, *, with_remaining=False, default_all=False):
    """Resolve CLI arguments to a deduplicated ticker list.

    Recognises ``--portfolio``/``-p``/``portfolio``,
    ``--watchlist``/``-w``/``watchlist``, ``--all``/``-a``,
    ``--tickers``/``-t TICK …``, and bare ``TICK`` arguments.

    Returns a deduplicated ``list[str]`` (order-preserved).
    If *with_remaining* is True, returns ``(tickers, remaining)``
    where *remaining* holds unrecognised ``--flag`` arguments.
    If *default_all* is True and no tickers are found, falls back to
    the combined watchlist + portfolio.
    """
    tickers: list[str] = []
    remaining: list[str] = []

    i = 0
    while i < len(args):
        arg = args[i]
        low = arg.lower()

        if low in ("--portfolio", "-p", "portfolio"):
            tickers.extend(portfolio_list())
        elif low in ("--watchlist", "-w", "watchlist"):
            tickers.extend(watchlist_list())
        elif low in ("--all", "-a"):
            tickers.extend(portfolio_list())
            tickers.extend(watchlist_list())
        elif low in ("--tickers", "-t"):
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                tickers.append(args[i].upper())
                i += 1
            continue
        elif not arg.startswith("-"):
            tickers.append(arg.upper().strip())
        else:
            remaining.append(args[i])
        i += 1

    if default_all and not tickers:
        tickers = watchlist_list() + portfolio_list()

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return (unique, remaining) if with_remaining else unique


# ── Cross-list helpers ───────────────────────────────────────────────


def move_to_portfolio(symbols):
    """Move symbols from watchlist → portfolio (bought it)."""
    removed = watchlist_remove(symbols)
    added = portfolio_add(symbols)
    return added


def move_to_watchlist(symbols):
    """Move symbols from portfolio → watchlist (sold it, still watching)."""
    removed = portfolio_remove(symbols)
    added = watchlist_add(symbols)
    return added


# ── File loading ─────────────────────────────────────────────────────


def load_tickers(filepath):
    """Load tickers from a text file. One ticker per line, # for comments."""
    if not os.path.exists(filepath):
        print(f"Error: Ticker file not found: {filepath}")
        print("Create a file with one ticker per line. Lines starting with # are comments.")
        sys.exit(1)

    tickers = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for t in line.split(","):
                t = t.strip().upper()
                if t:
                    tickers.append(t)

    if not tickers:
        print(f"Error: No tickers found in {filepath}")
        sys.exit(1)

    return tickers


# ── Data fetching ────────────────────────────────────────────────────


def get_financial_data(ticker_symbol, snapshot=True, mode=None):
    """Fetch comprehensive financial data for a company.

    Uses the provider dispatch layer which handles caching automatically:
      - mode="auto" (default): use DB cache if fresh, else fetch live
      - mode="live":           always fetch from remote provider
      - mode="cache":          DB only, no network

    When snapshot=True (default) and mode is not "cache", the provider
    also persists fundamentals and quarterly financials to the datastore.
    """
    from datasources.provider import get_fundamentals

    # In live/auto mode, the provider.get_fundamentals already caches
    data = get_fundamentals(ticker_symbol, mode=mode)
    return data
