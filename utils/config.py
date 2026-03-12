"""Configuration: load settings from config.yaml with sensible defaults.

Power users can tune DCF assumptions, scoring weights, and thresholds
without editing any Python code.
"""

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.yaml")

# ── Defaults ─────────────────────────────────────────────────────────

DEFAULTS = {
    # ── Scoring weights ──────────────────────────────────────────
    # How much each module contributes to the final fundamental score.
    # All six values MUST sum to 1.0 (auto-normalized if they don't).
    # Range per value: 0.0 – 1.0.  Set to 0 to ignore a module entirely.
    "weights": {
        "eps": 0.15,        # EPS growth & consistency weight
        "roe": 0.15,        # Return on Equity weight
        "fcf": 0.20,        # Free Cash Flow weight
        "balance": 0.15,    # Balance sheet health weight
        "dividend": 0.05,   # Dividend / capital-allocation weight (growth-friendly)
        "dcf": 0.15,        # DCF intrinsic-value weight
        "revenue": 0.15,    # Revenue growth weight (rewards organic growth)
    },

    # ── DCF model assumptions ────────────────────────────────────
    # Controls the Discounted Cash Flow valuation model.
    "dcf": {
        "growth_rate_high": 0.08,   # FCF growth rate for years 1-5.   Range: 0.0 – 0.25 (0% – 25%)
        "growth_rate_low": 0.03,    # FCF growth rate for years 6-10.  Range: 0.0 – 0.15 (0% – 15%)
        "terminal_growth": 0.025,   # Perpetual growth after yr 10.    Range: 0.01 – 0.04 (must be < discount_rate)
        "discount_rate": 0.10,      # Required annual return (WACC).   Range: 0.06 – 0.15 (6% – 15%)
        "margin_required": 0.15,    # Margin of safety to flag "undervalued".  Range: 0.0 – 0.50 (0% – 50%)
    },

    # ── EPS scoring thresholds ───────────────────────────────────
    # Tuning knobs for the EPS consistency & growth score (0-100).
    "eps": {
        "consistency_threshold": 0.65,  # Fraction of years EPS must grow to count as "consistent".  Range: 0.0 – 1.0
        "cagr_multiplier": 2.5,         # Points awarded per 1% EPS CAGR (growth component).       Range: 0.5 – 5.0
        "cagr_cap": 50,                 # Max points from CAGR (caps high-growth outliers).         Range: 10 – 100
    },

    # ── ROE scoring thresholds ───────────────────────────────────
    # What counts as "high" ROE and acceptable leverage.
    "roe": {
        "high_threshold": 15,    # ROE% above this = strong moat signal.    Range: 10 – 30
        "debt_reasonable": 150,  # Debt/Equity below this = full credit.    Range: 50 – 200
        "debt_max": 200,         # Debt/Equity above this = no credit.      Range: 100 – 400
    },

    # ── FCF scoring thresholds ───────────────────────────────────
    # Free Cash Flow quality gates.
    "fcf": {
        "yield_high": 3.0,   # FCF Yield% above this = full yield points.   Range: 1.0 – 8.0
        "yield_mid": 2.0,    # FCF Yield% above this = partial credit.      Range: 0.5 – 5.0
        "streak_high": 4,    # Consecutive positive-FCF years for full pts.  Range: 3 – 10 (integer)
        "streak_mid": 3,     # Consecutive positive-FCF years for half pts.  Range: 2 – 6  (integer)
    },

    # ── Balance sheet thresholds ─────────────────────────────────
    # Liquidity, debt coverage, and acquisition risk limits.
    "balance": {
        "current_ratio_high": 2.0,  # Current ratio ≥ this = full liquidity pts.  Range: 1.5 – 4.0
        "current_ratio_mid": 1.5,   # Current ratio ≥ this = partial credit.      Range: 1.0 – 3.0
        "cash_debt_high": 1.0,      # Cash/Debt ≥ this = can pay off all debt.     Range: 0.5 – 3.0
        "cash_debt_mid": 0.5,       # Cash/Debt ≥ this = partial credit.           Range: 0.1 – 1.5
        "goodwill_low": 10,         # Goodwill% of assets below this = excellent.  Range: 5 – 20
        "goodwill_mid": 20,         # Goodwill% of assets below this = acceptable. Range: 10 – 40
    },

    # ── Dividend thresholds ──────────────────────────────────────
    # What qualifies as a quality dividend payer.
    "dividend": {
        "yield_high": 2.0,   # Dividend yield% ≥ this = full yield pts.    Range: 1.0 – 5.0
        "yield_mid": 1.0,    # Dividend yield% ≥ this = partial credit.    Range: 0.3 – 3.0
        "payout_good": 60,   # Payout ratio% ≤ this = sustainable.         Range: 30 – 70
        "payout_ok": 80,     # Payout ratio% ≤ this = acceptable.          Range: 50 – 90
    },

    # ── Display settings ─────────────────────────────────────────
    "display": {
        "top_n": 20,       # Max stocks to show in ranked output.     Range: 5 – 100
        "max_peers": 5,    # Peers to include in comparison table.    Range: 3 – 10
    },

    # ── Cache settings ───────────────────────────────────────────
    "cache": {
        "expire_hours": 4,  # Hours before cached API responses expire.  Range: 1 – 24
    },

    # ── Alert thresholds ─────────────────────────────────────────
    # Controls what triggers price target & score-drop alerts.
    "alerts": {
        "margin_of_safety_min": 0,     # MoS% above this triggers an undervalued alert.  Range: -20 – 30
        "score_drop_threshold": 10,    # Fundamental score drop ≥ this triggers an alert.    Range: 5 – 30
    },

    # ── Simulation / auto-trading settings ───────────────────────
    # Controls the paper-trading simulator and backtester.
    "simulation": {
        "starting_cash": 100000,       # Virtual starting capital ($).                   Range: 10000 – 10000000
        "max_position_pct": 0.10,      # Max portfolio weight per stock (fraction).       Range: 0.03 – 0.25
        "max_positions": 20,           # Max simultaneous holdings.                       Range: 5 – 50
        "commission": 0.0,             # Per-trade commission ($).                        Range: 0.0 – 20.0
        "stop_loss_pct": 0.20,         # Sell if position drops this much.                Range: 0.05 – 0.50 (0 = disabled)
        "take_profit_pct": 0.0,        # Sell if position gains this much.                Range: 0.0 – 2.0  (0 = disabled)
        "benchmarks": ["SPY", "QQQ", "VT"],  # Benchmark symbols for comparison.
    },
}


def _deep_merge(base, override):
    """Recursively merge override into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path=None):
    """Load config from YAML file, merged with defaults.

    If file doesn't exist, returns defaults (no file created automatically).
    """
    cfg = DEFAULTS.copy()
    filepath = path or CONFIG_PATH

    if os.path.exists(filepath):
        try:
            import yaml
            with open(filepath, "r") as f:
                user_cfg = yaml.safe_load(f) or {}
            cfg = _deep_merge(DEFAULTS, user_cfg)
        except ImportError:
            print("  Warning: PyYAML not installed. Using default config.")
            print("  Install with: pip install pyyaml")
        except Exception as e:
            print(f"  Warning: Could not parse {filepath}: {e}")
            print("  Using default config.")

    return cfg


def save_default_config(path=None):
    """Write the default config.yaml file."""
    filepath = path or CONFIG_PATH

    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is required. Install with: pip install pyyaml")
        return False

    with open(filepath, "w") as f:
        f.write("# Stock Screener — Configuration\n")
        f.write("# Edit values below to customize scoring and analysis.\n")
        f.write("# Delete this file to reset to defaults.\n\n")
        yaml.dump(DEFAULTS, f, default_flow_style=False, sort_keys=False)

    print(f"  Default config written to {filepath}")
    return True


def get_weights(cfg=None):
    """Get scoring weights, normalized to sum to 1.0."""
    if cfg is None:
        cfg = load_config()
    w = cfg.get("weights", DEFAULTS["weights"])
    total = sum(w.values())
    if abs(total - 1.0) > 0.01:
        # Normalize
        w = {k: v / total for k, v in w.items()}
    return w


def get_dcf_params(cfg=None):
    """Get DCF model parameters."""
    if cfg is None:
        cfg = load_config()
    return cfg.get("dcf", DEFAULTS["dcf"])


# Module-level config instance (loaded once on first access)
_config = None


def config():
    """Get the global config (lazy-loaded)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


# ═══════════════════════════════════════════════════════════════════════
#  API request caching (merged from cache.py)
# ═══════════════════════════════════════════════════════════════════════

CACHE_DIR = os.path.join(_PROJECT_ROOT, ".cache")
CACHE_PATH = os.path.join(CACHE_DIR, "yfinance_cache")

_cache_enabled = False


def enable_cache(expire_hours=4):
    """Install requests-cache as a transparent session cache.

    All yfinance HTTP requests will be cached for `expire_hours` hours.
    Safe to call multiple times — only installs once.
    """
    global _cache_enabled
    if _cache_enabled:
        return

    try:
        import requests_cache
    except ImportError:
        print("  [cache] requests-cache not installed — caching disabled")
        print("  Install with: pip install requests-cache")
        return

    os.makedirs(CACHE_DIR, exist_ok=True)

    requests_cache.install_cache(
        CACHE_PATH,
        backend="sqlite",
        expire_after=expire_hours * 3600,
        allowable_methods=("GET", "POST"),
        stale_if_error=True,
    )
    _cache_enabled = True


def clear_cache():
    """Remove all cached responses."""
    try:
        import requests_cache
        requests_cache.clear()
        print("  Cache cleared.")
    except ImportError:
        pass

    for ext in (".sqlite", ".sqlite-journal"):
        path = CACHE_PATH + ext
        if os.path.exists(path):
            os.remove(path)
            print(f"  Removed {path}")


def cache_stats():
    """Print cache statistics."""
    for ext in (".sqlite",):
        path = CACHE_PATH + ext
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  Cache: {path} ({size_mb:.1f} MB)")
            return
    print("  No cache file found.")
