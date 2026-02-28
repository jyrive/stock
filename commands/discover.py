"""discover command: scan ALL Finviz presets → find new investment ideas.

Runs every preset, deduplicates, removes stocks already in your
portfolio or watchlist, and presents the best new candidates.

Usage:
    python stock.py discover              # scan all presets
    python stock.py discover --analyze    # scan + auto-analyze top candidates
    python stock.py discover buffett      # scan one preset only
"""

import sys
import warnings

from utils.discovery import PRESETS, scan_finviz
from utils.lists import portfolio_list, watchlist_list, watchlist_add

warnings.filterwarnings("ignore")


def _collect_all_candidates(preset_name=None):
    """Scan Finviz presets and return deduplicated candidates.

    Returns:
        all_results: dict of ticker → {info dict + 'presets' list}
        excluded:    set of tickers already in portfolio/watchlist
    """
    # Determine which presets to scan
    presets_to_scan = (
        {preset_name: PRESETS[preset_name]}
        if preset_name and preset_name in PRESETS
        else PRESETS
    )

    # Known tickers to exclude
    owned = set(t.upper() for t in portfolio_list())
    watched = set(t.upper() for t in watchlist_list())
    excluded = owned | watched

    all_results = {}  # ticker → info dict
    errors = []

    for name, info in presets_to_scan.items():
        desc = info["description"]
        print(f"  Scanning: {name:<16} {desc}")
        try:
            rows = scan_finviz(name)
            for row in rows:
                ticker = row.get("Ticker", "")
                if not ticker:
                    continue
                if ticker in all_results:
                    all_results[ticker]["presets"].append(name)
                else:
                    all_results[ticker] = {
                        "ticker": ticker,
                        "company": row.get("Company", "?"),
                        "sector": row.get("Sector", "?"),
                        "industry": row.get("Industry", "?"),
                        "pe": row.get("P/E", "-"),
                        "price": row.get("Price", "-"),
                        "market_cap": row.get("Market Cap", "-"),
                        "presets": [name],
                    }
        except Exception as e:
            errors.append((name, str(e)))

    if errors:
        for name, err in errors:
            print(f"  ⚠️  {name} failed: {err}")

    return all_results, excluded


def main():
    args = sys.argv[1:]

    # Parse flags
    auto_analyze = "--analyze" in args
    args = [a for a in args if not a.startswith("--")]
    preset = args[0] if args else None

    if preset and preset not in PRESETS:
        print(f"Unknown preset: '{preset}'")
        print(f"Available: {', '.join(PRESETS.keys())}")
        return

    print()
    print("=" * 70)
    print("  DISCOVER — Finding new investment ideas")
    print("=" * 70)
    print()

    all_results, excluded = _collect_all_candidates(preset)
    total = len(all_results)

    # Split into new vs already-tracked
    new_candidates = {}
    already_tracked = {}
    for ticker, info in all_results.items():
        if ticker in excluded:
            already_tracked[ticker] = info
        else:
            new_candidates[ticker] = info

    # Sort new candidates: those matching MORE presets first (higher conviction)
    ranked = sorted(
        new_candidates.values(),
        key=lambda x: len(x["presets"]),
        reverse=True,
    )

    print()
    print(f"  Total matches across presets: {total}")
    print(f"  Already in portfolio/watchlist: {len(already_tracked)}")
    print(f"  NEW candidates: {len(ranked)}")

    if already_tracked:
        print(f"\n  {'─' * 60}")
        print(f"  Already tracked ({len(already_tracked)}):")
        for t, info in sorted(already_tracked.items()):
            tags = ", ".join(info["presets"])
            print(f"    ✓ {t:<8} {info['company']:<30} [{tags}]")

    if ranked:
        print(f"\n  {'─' * 60}")
        print(f"  NEW candidates ranked by conviction (# presets matched):")
        print(f"  {'─' * 60}")
        for i, info in enumerate(ranked, 1):
            presets_str = ", ".join(info["presets"])
            conv = len(info["presets"])
            stars = "★" * conv + "☆" * (len(PRESETS) - conv)
            print(f"\n  {i:>3}. {info['ticker']:<8} {info['company']}")
            print(f"       Sector: {info['sector']}  |  Industry: {info['industry']}")
            print(f"       P/E: {info['pe']}  |  Price: ${info['price']}  |  MCap: {info['market_cap']}")
            print(f"       Conviction: {stars}  [{presets_str}]")

        # Quick-add top candidates
        top_tickers = [r["ticker"] for r in ranked[:10]]
        print(f"\n  {'─' * 60}")
        print(f"  Quick actions:")
        print(f"    Add to watchlist:  python stock.py watchlist add {' '.join(top_tickers[:5])}")
        print(f"    Analyze first:     python stock.py analyze {' '.join(top_tickers[:5])}")

        if auto_analyze and ranked:
            # Auto-analyze top 10 (or fewer)
            analyze_tickers = [r["ticker"] for r in ranked[:10]]
            print(f"\n  {'─' * 60}")
            print(f"  Auto-analyzing top {len(analyze_tickers)} candidates...")
            print(f"  {'─' * 60}\n")
            sys.argv = ["analyze.py"] + analyze_tickers
            from commands.analyze import main as analyze_main
            analyze_main()
    else:
        print("\n  No new candidates found.  All Finviz matches are already tracked!")
        print("  Your portfolio + watchlist cover this well.")

    print()


if __name__ == "__main__":
    main()
