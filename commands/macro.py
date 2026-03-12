"""macro command: global macro-economic environment dashboard.

Usage:
    python stock.py macro              # full macro dashboard
    python stock.py macro --compact    # compact summary (~10 lines)
"""

import sys

from analysis.macro import analyze_macro, print_macro_full, print_macro_compact
from utils.config import enable_cache

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    compact = "--compact" in args or "-c" in args

    enable_cache()

    print("\n  Fetching global macro indicators...")

    macro = analyze_macro()

    if compact:
        print_macro_compact(macro)
    else:
        print_macro_full(macro)

if __name__ == "__main__":
    main()
