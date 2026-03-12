"""Data source abstraction layer.

Architecture:
    schema.py        — single source of truth for field definitions
    provider.py      — dispatch (auto / live / cache)
    market.py        — backward-compatible façade (re-exports from providers/)
    screener.py      — stock discovery (finviz)
    providers/       — remote API adapters
        yfinance.py  — yfinance implementation

To add a new market-data provider:
    1. Create datasources/providers/<name>.py with the same function signatures.
    2. Map the provider's field names to schema field names (see FIELD_MAP).
    3. Wire it in provider.py.
"""
