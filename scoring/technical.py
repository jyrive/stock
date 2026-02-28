"""Backwards-compat shim — use technical.analysis and output.technical directly."""
from technical.analysis import *  # noqa: F401,F403
from technical.analysis import analyze_technical, _compute_tech_score, _summarize_signals
from output.technical import print_technical, _entry_rating
