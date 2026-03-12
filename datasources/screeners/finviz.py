"""Finviz stock screener provider.

All finvizfinance access is isolated here.  Other modules import
from ``datasources.screener`` (the dispatch façade), never directly.
"""

from finvizfinance.screener.overview import Overview


# ═══════════════════════════════════════════════════════════════════════
#  Preset filter definitions
# ═══════════════════════════════════════════════════════════════════════

PRESETS = {
    "quality": {
        "description": "Classic quality: high ROE, profitable, large-cap, low debt",
        "filters": {
            "Market Cap.": "Large ($10bln to $200bln)",
            "Return on Equity": "Over +15%",
            "EPS growthpast 5 years": "Positive (>0%)",
            "Current Ratio": "Over 1",
            "Operating Margin": "Over 15%",
        },
    },
    "quality_mega": {
        "description": "Quality mega-caps: >$200B, high ROE, strong margins",
        "filters": {
            "Market Cap.": "Mega ($200bln and more)",
            "Return on Equity": "Over +15%",
            "EPS growthpast 5 years": "Positive (>0%)",
            "Operating Margin": "Over 20%",
        },
    },
    "growth_value": {
        "description": "Growth at reasonable price: mid+ cap, growing, not expensive",
        "filters": {
            "Market Cap.": "+Mid (over $2bln)",
            "Return on Equity": "Over +15%",
            "EPS growthpast 5 years": "Over 10%",
            "P/E": "Under 25",
            "EPS growthnext 5 years": "Over 10%",
        },
    },
    "high_roe": {
        "description": "High ROE screener: exceptional ROE across all cap sizes",
        "filters": {
            "Market Cap.": "+Mid (over $2bln)",
            "Return on Equity": "Over +30%",
            "EPS growthpast 5 years": "Positive (>0%)",
        },
    },
    "fcf_machines": {
        "description": "Free cash flow machines: profitable, positive FCF, low debt",
        "filters": {
            "Market Cap.": "+Mid (over $2bln)",
            "Return on Equity": "Over +15%",
            "Operating Margin": "Over 20%",
            "Current Ratio": "Over 1.5",
            "EPS growthpast 5 years": "Positive (>0%)",
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  Screening
# ═══════════════════════════════════════════════════════════════════════

def screen(preset_name="quality", custom_filters=None):
    """Query Finviz screener and return a list of ticker dicts.

    Returns list of dicts with keys: Ticker, Company, Sector, Industry,
    Market Cap, P/E, Price, etc.
    """
    foverview = Overview()

    if custom_filters:
        filters = custom_filters
    elif preset_name in PRESETS:
        filters = PRESETS[preset_name]["filters"]
    else:
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available: {', '.join(PRESETS)}"
        )

    foverview.set_filter(filters_dict=filters)
    df = foverview.screener_view()

    if df is None or df.empty:
        return []

    return df.to_dict("records")
