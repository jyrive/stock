"""Stock discovery/screening — dispatch façade.

All stock screening flows through this module.  The actual provider
implementation lives in ``datasources.screeners.finviz``.
"""

from datasources.screeners.finviz import PRESETS, screen  # noqa: F401
