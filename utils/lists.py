"""Ticker list management: portfolio.txt and watchlist.txt add/remove/list.

Both files live in the project root alongside tickers.txt.  Format is the
same: one ticker per line, # comments allowed, blank lines ignored.
"""

import os

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
