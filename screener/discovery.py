"""Discover new stock candidates from online screeners (Finviz).

Scans Finviz for stocks matching Buffett-style filters and reports
candidates not already in the local ticker list.
"""

import os

from finvizfinance.screener.overview import Overview

from .data import load_tickers, DEFAULT_TICKER_FILE


# Predefined Buffett-style filter presets
PRESETS = {
    "buffett": {
        "description": "Classic Buffett: high ROE, profitable, large-cap, low debt",
        "filters": {
            "Market Cap.": "Large ($10bln to $200bln)",
            "Return on Equity": "Over +15%",
            "EPS growthpast 5 years": "Positive (>0%)",
            "Current Ratio": "Over 1",
            "Operating Margin": "Over 15%",
        },
    },
    "buffett_mega": {
        "description": "Buffett mega-caps: >$200B, high ROE, strong margins",
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


def get_existing_tickers(ticker_file=None):
    """Load existing tickers from file, return as a set."""
    path = ticker_file or DEFAULT_TICKER_FILE
    if not os.path.exists(path):
        return set()
    try:
        return set(load_tickers(path))
    except SystemExit:
        return set()


def scan_finviz(preset_name="buffett", custom_filters=None):
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


def discover_candidates(preset_name="buffett", ticker_file=None, show_all=False):
    """Discover new candidates not already in the ticker list.

    Returns (new_candidates, existing_matches, all_results).
    """
    existing = get_existing_tickers(ticker_file)
    results = scan_finviz(preset_name)

    new_candidates = []
    existing_matches = []

    for row in results:
        ticker = row.get("Ticker", "")
        if ticker in existing:
            existing_matches.append(row)
        else:
            new_candidates.append(row)

    if show_all:
        return new_candidates, existing_matches, results
    return new_candidates, existing_matches, results


def print_discovery_results(new_candidates, existing_matches, preset_name):
    """Pretty-print discovery results."""
    preset = PRESETS.get(preset_name, {})
    desc = preset.get("description", preset_name)

    print("=" * 80)
    print("STOCK DISCOVERY SCANNER")
    print("=" * 80)
    print(f"\nPreset: {preset_name} — {desc}")
    print(f"Total matches from Finviz: {len(new_candidates) + len(existing_matches)}")
    print(f"Already in tickers.txt:    {len(existing_matches)}")
    print(f"NEW candidates:            {len(new_candidates)}")

    if existing_matches:
        print(f"\n{'─' * 60}")
        print(f"  Already tracked ({len(existing_matches)}):")
        print(f"{'─' * 60}")
        for row in existing_matches:
            ticker = row.get("Ticker", "?")
            company = row.get("Company", "?")
            sector = row.get("Sector", "?")
            pe = row.get("P/E", "-")
            price = row.get("Price", "-")
            print(f"  ✓ {ticker:<8} {company:<35} {sector:<20} P/E: {pe}  ${price}")

    if new_candidates:
        print(f"\n{'─' * 60}")
        print(f"  NEW candidates to investigate ({len(new_candidates)}):")
        print(f"{'─' * 60}")
        for i, row in enumerate(new_candidates, 1):
            ticker = row.get("Ticker", "?")
            company = row.get("Company", "?")
            sector = row.get("Sector", "?")
            industry = row.get("Industry", "?")
            pe = row.get("P/E", "-")
            price = row.get("Price", "-")
            mcap = row.get("Market Cap", "-")
            print(f"  {i:>3}. {ticker:<8} {company:<35} {sector}")
            print(f"       Industry: {industry}")
            print(f"       P/E: {pe}  |  Price: ${price}  |  Market Cap: {mcap}")
            print()

        # Print just the tickers for easy copy-paste
        print(f"{'─' * 60}")
        print("  Quick copy — run screener on new candidates:")
        tickers_str = " ".join(row.get("Ticker", "") for row in new_candidates)
        print(f"  python buffett_screener.py {tickers_str}")
    else:
        print("\n  No new candidates found. Try a different preset.")

    print()
    print(f"Available presets: {', '.join(PRESETS.keys())}")
    print(f"Usage: python discover.py [preset]")
