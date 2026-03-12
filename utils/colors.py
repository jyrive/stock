"""Terminal color helpers — ANSI 256-color with auto-detection.

Colors are disabled when stdout is not a TTY (piped output).
"""

import os
import sys

# ── Auto-detect color support ────────────────────────────────────
_NO_COLOR = os.environ.get("NO_COLOR") is not None
_FORCE_COLOR = os.environ.get("FORCE_COLOR") is not None
USE_COLOR = _FORCE_COLOR or (not _NO_COLOR and hasattr(sys.stdout, "isatty") and sys.stdout.isatty())


def _ansi(code):
    """Return ANSI escape sequence if colors are enabled."""
    return f"\033[{code}m" if USE_COLOR else ""


# ── Basic styles ─────────────────────────────────────────────────
RESET = _ansi(0)
BOLD = _ansi(1)
DIM = _ansi(2)

# ── Foreground colors ───────────────────────────────────────────
GREEN = _ansi(32)
YELLOW = _ansi(33)
RED = _ansi(31)
CYAN = _ansi(36)
WHITE = _ansi(37)
BRIGHT_GREEN = _ansi(92)
BRIGHT_RED = _ansi(91)
BRIGHT_YELLOW = _ansi(93)
BRIGHT_CYAN = _ansi(96)
GRAY = _ansi(90)


# ── Semantic helpers ─────────────────────────────────────────────
def good(text):
    """Green — strong metric."""
    return f"{GREEN}{text}{RESET}"


def warn(text):
    """Yellow — borderline metric."""
    return f"{YELLOW}{text}{RESET}"


def bad(text):
    """Red — weak metric."""
    return f"{RED}{text}{RESET}"


def highlight(text):
    """Bold cyan — emphasis."""
    return f"{BOLD}{CYAN}{text}{RESET}"


def dim(text):
    """Gray — de-emphasized."""
    return f"{GRAY}{text}{RESET}"


def score_color(value, high=70, mid=40):
    """Color a score value: green ≥high, yellow ≥mid, red <mid."""
    if value is None:
        return dim("-")
    s = f"{value:.1f}" if isinstance(value, float) else str(value)
    if value >= high:
        return good(s)
    if value >= mid:
        return warn(s)
    return bad(s)


def pct_color(value, high=15, mid=0):
    """Color a percentage: green ≥high, yellow ≥mid, red <mid."""
    if value is None:
        return dim("-")
    s = f"{value:.1f}%"
    if value >= high:
        return good(s)
    if value >= mid:
        return warn(s)
    return bad(s)


def uv_color(undervalued):
    """Color the undervalued indicator."""
    if undervalued:
        return good("✅")
    return bad("❌")


def ratio_color(value, good_thresh, warn_thresh, fmt=".1f"):
    """Color a ratio value with custom thresholds."""
    if value is None:
        return dim("-")
    s = f"{value:{fmt}}"
    if value >= good_thresh:
        return good(s)
    if value >= warn_thresh:
        return warn(s)
    return bad(s)
