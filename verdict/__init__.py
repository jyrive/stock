"""Verdict — triangulated convergence of Fundamental + Technical + Macro.

Pure logic: no I/O, no imports. Takes three scores and produces
a verdict with position-sizing recommendation.
"""

from .engine import compute_verdict

__all__ = ["compute_verdict"]
