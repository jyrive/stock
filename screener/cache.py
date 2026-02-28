"""yfinance request caching — speeds up repeated runs.

Uses requests-cache to transparently cache HTTP responses.
Cache lives in .cache/yfinance_cache.sqlite and expires after 4 hours.

Usage:
    from screener.cache import enable_cache
    enable_cache()  # Call once at startup
"""

import os

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache"
)
CACHE_PATH = os.path.join(CACHE_DIR, "yfinance_cache")

_enabled = False


def enable_cache(expire_hours=4):
    """Install requests-cache as a transparent session cache.

    All yfinance HTTP requests will be cached for `expire_hours` hours.
    Safe to call multiple times — only installs once.
    """
    global _enabled
    if _enabled:
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
    _enabled = True


def clear_cache():
    """Remove all cached responses."""
    try:
        import requests_cache
        requests_cache.clear()
        print("  Cache cleared.")
    except ImportError:
        pass

    # Also remove the file directly
    for ext in (".sqlite", ".sqlite-journal"):
        path = CACHE_PATH + ext
        if os.path.exists(path):
            os.remove(path)
            print(f"  Removed {path}")


def cache_stats():
    """Print cache statistics."""
    import os
    for ext in (".sqlite",):
        path = CACHE_PATH + ext
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  Cache: {path} ({size_mb:.1f} MB)")
            return
    print("  No cache file found.")
