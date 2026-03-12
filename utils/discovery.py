"""Discover new stock candidates from online screeners.

Scans for stocks matching quality filters and reports
candidates not already in portfolio or watchlist.
"""

from datasources.screener import PRESETS, screen as scan_finviz

from .lists import portfolio_list, watchlist_list


def get_existing_tickers():
    """Return combined set of portfolio + watchlist tickers."""
    return set(portfolio_list() + watchlist_list())


def discover_candidates(preset_name="quality", show_all=False):
    """Discover new candidates not already in portfolio/watchlist.

    Returns (new_candidates, existing_matches, all_results).
    """
    existing = get_existing_tickers()
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
    print(f"Already tracked:           {len(existing_matches)}")
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
        print(f"  python stock.py analyze {tickers_str}")
    else:
        print("\n  No new candidates found. Try a different preset.")

    print()
    print(f"Available presets: {', '.join(PRESETS.keys())}")
    print(f"Usage: python stock.py screen [preset]")
