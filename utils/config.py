"""Configuration: load settings from config.yaml with sensible defaults.

Power users can tune DCF assumptions, scoring weights, and thresholds
without editing any Python code.
"""

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.yaml")

# ── Defaults ─────────────────────────────────────────────────────────

DEFAULTS = {
    # Scoring weights (must sum to 1.0)
    "weights": {
        "eps": 0.15,
        "roe": 0.15,
        "fcf": 0.20,
        "balance": 0.15,
        "dividend": 0.15,
        "dcf": 0.20,
    },

    # DCF model assumptions
    "dcf": {
        "growth_rate_high": 0.08,   # Years 1-5
        "growth_rate_low": 0.03,    # Years 6-10
        "terminal_growth": 0.025,   # Terminal growth rate
        "discount_rate": 0.10,      # Required return
        "margin_required": 0.15,    # 15% margin of safety
    },

    # EPS scoring thresholds
    "eps": {
        "consistency_threshold": 0.65,
        "cagr_multiplier": 2.5,
        "cagr_cap": 50,
    },

    # ROE scoring thresholds
    "roe": {
        "high_threshold": 15,
        "debt_reasonable": 150,
        "debt_max": 200,
    },

    # FCF scoring thresholds
    "fcf": {
        "yield_high": 3.0,
        "yield_mid": 2.0,
        "streak_high": 4,
        "streak_mid": 3,
    },

    # Balance sheet thresholds
    "balance": {
        "current_ratio_high": 2.0,
        "current_ratio_mid": 1.5,
        "cash_debt_high": 1.0,
        "cash_debt_mid": 0.5,
        "goodwill_low": 10,
        "goodwill_mid": 20,
    },

    # Dividend thresholds
    "dividend": {
        "yield_high": 2.0,
        "yield_mid": 1.0,
        "payout_good": 60,
        "payout_ok": 80,
    },

    # Display settings
    "display": {
        "top_n": 20,
        "max_peers": 5,
    },

    # Cache settings
    "cache": {
        "expire_hours": 4,
    },

    # Alert thresholds (for price target alerts)
    "alerts": {
        "margin_of_safety_min": 0,     # MoS% above this = alert
        "score_drop_threshold": 10,    # Score drop > this = alert
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
        f.write("# Buffett Stock Screener — Configuration\n")
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
