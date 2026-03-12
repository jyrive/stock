"""Market data schema — the single source of truth for field definitions.

This module defines WHAT data exists in the domain.  It is independent
of how data is stored (SQLite, Postgres) or where it's fetched from
(yfinance, Polygon, CSV).

Three consumers read this module:
    1. utils/db.py           — generates DDL from field lists
    2. providers/yfinance.py — maps yfinance keys → our field names
    3. utils/snapshot_db.py  — builds queries using field names

When adding a new field:
    1. Add it here
    2. Add a migration in utils/db.py
    3. Map it in the provider that supplies it
"""


# ═══════════════════════════════════════════════════════════════════════
#  Fundamental snapshot fields
# ═══════════════════════════════════════════════════════════════════════
#
#  Each entry: (field_name, sql_type, required, description)
#
#  These are the point-in-time fundamental metrics that get stored
#  once per (symbol, snapshot_date).  The 'info_json' blob is stored
#  separately and does not appear here — it's a raw backup.

SNAPSHOT_FIELDS = [
    ("market_cap",       "REAL",  True,  "Market capitalisation (billions USD)"),
    ("current_price",    "REAL",  True,  "Share price at snapshot time"),
    ("trailing_pe",      "REAL",  False, "Trailing P/E ratio"),
    ("forward_pe",       "REAL",  False, "Forward P/E ratio"),
    ("price_to_book",    "REAL",  False, "Price / book value"),
    ("price_to_sales",   "REAL",  False, "Price / trailing 12M revenue"),
    ("roe_pct",          "REAL",  False, "Return on equity (%)"),
    ("debt_to_equity",   "REAL",  False, "Total debt / equity ratio"),
    ("current_ratio",    "REAL",  False, "Current assets / current liabilities"),
    ("profit_margin",    "REAL",  False, "Net profit margin (%)"),
    ("revenue_growth",   "REAL",  False, "Year-over-year revenue growth (%)"),
    ("earnings_growth",  "REAL",  False, "Year-over-year earnings growth (%)"),
    ("fcf_yield",        "REAL",  False, "Free-cash-flow yield (%)"),
    ("dividend_yield",   "REAL",  False, "Dividend yield (%)"),
    ("payout_ratio",     "REAL",  False, "Dividend payout ratio (%)"),
    ("beta",             "REAL",  False, "Beta vs market"),
]


# ═══════════════════════════════════════════════════════════════════════
#  Metadata fields  (shared by snapshots and scorer data dicts)
# ═══════════════════════════════════════════════════════════════════════

METADATA_FIELDS = [
    ("symbol",   "TEXT", True,  "Ticker symbol"),
    ("name",     "TEXT", True,  "Company name"),
    ("sector",   "TEXT", False, "GICS sector"),
    ("industry", "TEXT", False, "GICS industry"),
]


# ═══════════════════════════════════════════════════════════════════════
#  Financial statement line items
# ═══════════════════════════════════════════════════════════════════════
#
#  The row labels that scorers read from income_stmt, balance_sheet,
#  and cash_flow DataFrames.  Providers must map their source labels
#  to these names.

INCOME_STMT_ROWS = [
    "Total Revenue",
    "Net Income",
    "Basic EPS",
    "Diluted EPS",
]

BALANCE_SHEET_ROWS = [
    "Stockholders Equity",
    "Total Debt",
    "Current Assets",
    "Current Liabilities",
    "Goodwill",
    "Total Assets",
    "Retained Earnings",
]

CASHFLOW_ROWS = [
    "Free Cash Flow",
    "Cash Dividends Paid",
    "Operating Cash Flow",
]

STATEMENT_YEARS = 4  # how many annual periods scorers expect


# ═══════════════════════════════════════════════════════════════════════
#  Price / macro cache columns
# ═══════════════════════════════════════════════════════════════════════

PRICE_COLUMNS = [
    ("open",      "REAL",    False, "Opening price"),
    ("high",      "REAL",    False, "High price"),
    ("low",       "REAL",    False, "Low price"),
    ("close",     "REAL",    True,  "Closing price"),
    ("volume",    "REAL",    False, "Volume"),
    ("dividends", "REAL",    False, "Dividends paid"),
]

PRICE_PERIOD_DEFAULT = "1y"


# ═══════════════════════════════════════════════════════════════════════
#  Refresh policy — per-category staleness thresholds
# ═══════════════════════════════════════════════════════════════════════
#
# Each category has max_age_hours controlling when auto-mode re-fetches.
# Financial statements change quarterly, metadata almost never, so they
# don't need daily re-fetching.  Prices and valuation metrics do.

REFRESH_POLICY = {
    "snapshot":    {"max_age_hours": 24,    "description": "Valuation metrics from ticker.info"},
    "statements":  {"max_age_hours": 90*24, "description": "Quarterly financials (income/BS/CF)"},
    "prices":      {"max_age_hours": 18,    "description": "Daily OHLCV price data"},
    "dividends":   {"max_age_hours": 30*24, "description": "Dividend history"},
    "metadata":    {"max_age_hours": 30*24, "description": "Company name, sector, industry"},
}


def max_age(category):
    """Return max_age_hours for a data category.

    >>> max_age("snapshot")
    24
    """
    return REFRESH_POLICY[category]["max_age_hours"]


# Backward-compat aliases — old code uses these constants directly
MAX_SNAPSHOT_AGE_HOURS = REFRESH_POLICY["snapshot"]["max_age_hours"]
MAX_PRICE_AGE_HOURS = REFRESH_POLICY["prices"]["max_age_hours"]
MAX_STATEMENT_AGE_DAYS = REFRESH_POLICY["statements"]["max_age_hours"] // 24


# ═══════════════════════════════════════════════════════════════════════
#  Helpers — used by db.py, snapshot_db.py, providers
# ═══════════════════════════════════════════════════════════════════════

def sql_columns(field_list):
    """Generate SQL column definitions from a field list.

    >>> sql_columns([("market_cap", "REAL", True, "..."), ...])
    "market_cap REAL NOT NULL, ..."
    """
    parts = []
    for name, sql_type, required, _desc in field_list:
        col = f"{name} {sql_type}"
        if required:
            col += " NOT NULL"
        parts.append(col)
    return ",\n            ".join(parts)


def field_names(field_list):
    """Return just the column names from a field list."""
    return [f[0] for f in field_list]


def required_fields():
    """Return names of all required snapshot + metadata fields."""
    return [f[0] for f in SNAPSHOT_FIELDS + METADATA_FIELDS if f[2]]


def validate(data):
    """Check that a data dict has all required fields.

    Returns (ok: bool, missing: list[str]).
    """
    missing = [
        f[0]
        for f in SNAPSHOT_FIELDS + METADATA_FIELDS
        if f[2] and data.get(f[0]) is None
    ]
    return (len(missing) == 0, missing)
