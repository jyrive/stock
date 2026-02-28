"""Backwards-compat shim — use macro.analysis and output.macro directly."""
from macro.analysis import *  # noqa: F401,F403
from macro.analysis import analyze_macro
from output.macro import macro_one_liner, print_macro_compact, print_macro_full
