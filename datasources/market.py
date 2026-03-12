"""Market data provider — façade re-exporting from the active provider.

All external market data fetching flows through this module.
The actual implementation lives in ``datasources.providers.yfinance``
(or whichever provider is configured).

This module exists for backward compatibility — callers can import
from ``datasources.market`` without knowing which provider is active.
New code should prefer ``datasources.provider`` for cache-aware access.
"""

# Re-export everything from the active provider backend
from datasources.providers.yfinance import (  # noqa: F401
    FIELD_MAP,
    get_info,
    get_fundamentals,
    get_quarterly_financials,
    get_price_history,
    get_current_price,
    get_current_prices,
    get_macro_history,
    get_dividends,
    _ticker,
)
