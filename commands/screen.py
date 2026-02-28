#!/usr/bin/env python3
"""
Stock Screener

Scans online screeners (Finviz) for stocks matching Buffett-style criteria
and shows candidates NOT already in your tickers.txt.

Usage:
    python stock.py screen               # default "buffett" preset
    python stock.py screen high_roe      # use a specific preset
    python stock.py screen --list        # show available presets

Presets:
    buffett       Classic Buffett: high ROE, profitable, large-cap, low debt
    buffett_mega  Buffett mega-caps: >$200B, high ROE, strong margins
    growth_value  Growth at reasonable price: mid+ cap, growing, P/E < 25
    high_roe      High ROE screener: exceptional ROE (>30%) across cap sizes
    fcf_machines  FCF machines: profitable, high margins, low debt
"""

import sys
import warnings

from utils.discovery import (
    PRESETS,
    discover_candidates,
    print_discovery_results,
)

warnings.filterwarnings("ignore")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg in ("--list", "-l", "--help", "-h"):
            print("Available discovery presets:\n")
            for name, info in PRESETS.items():
                print(f"  {name:<16} {info['description']}")
            print(f"\nUsage: python stock.py screen [preset]")
            return

        preset = arg
    else:
        preset = "buffett"

    if preset not in PRESETS:
        print(f"Unknown preset: '{preset}'")
        print(f"Available: {', '.join(PRESETS.keys())}")
        print(f"Run: python stock.py screen --list")
        return

    print(f"Scanning Finviz with '{preset}' preset...\n")

    try:
        new_candidates, existing_matches, _ = discover_candidates(preset)
        print_discovery_results(new_candidates, existing_matches, preset)
    except Exception as e:
        print(f"Error scanning Finviz: {e}")
        print("Finviz may be rate-limiting. Try again in a minute.")


if __name__ == "__main__":
    main()
