"""Backwards-compat shim — use verdict.engine and output.verdict directly."""
from verdict.engine import *  # noqa: F401,F403
from verdict.engine import compute_verdict
from output.verdict import print_verdict, verdict_one_liner, print_verdict_table
