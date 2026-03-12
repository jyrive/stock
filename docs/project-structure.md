# Project Structure

```
stock.py                       # Unified CLI entry point
config.yaml                    # User config (created with `config init`)
scores.db                      # SQLite database (auto-created)

portfolio.txt                  # Stocks you OWN (auto-created)
watchlist.txt                  # Stocks you're WATCHING (auto-created)

commands/                      # CLI command handlers
├── analyze.py                 # Deep fundamental analysis + export
├── technical.py               # Technical entry-timing analysis
├── macro.py                   # Global macro environment dashboard
├── verdict.py                 # Triangulated verdict engine
├── screen.py                  # Finviz candidate discovery
├── history.py                 # Score history browser
├── deepdive.py                # Due-diligence checklist + peer comparison
├── alerts.py                  # Price target & score drop alerts
├── portfolio.py               # Portfolio management & analysis
├── watchlist.py               # Watchlist management & opportunities
├── discover.py                # Multi-preset discovery scanner
├── compare.py                 # Side-by-side comparison
└── workflow.py                # Daily/weekly/monthly workflow automation

fundamental/                   # Fundamental scoring (independent domain)
├── eps.py                     # EPS consistency & growth
├── roe.py                     # Return on equity & debt
├── fcf.py                     # Free cash flow strength
├── balance.py                 # Balance sheet health
├── dividend.py                # Dividend quality
├── dcf.py                     # DCF intrinsic value (config-driven)
└── revenue.py                 # Revenue growth tracking

technical/                     # Technical analysis (independent domain)
└── analysis.py                # RSI, SMA, EMA, Bollinger, MACD, 52-week

macro/                         # Global macro environment (independent domain)
└── analysis.py                # VIX, yields, spreads, indices, breadth

verdict/                       # Triangulated verdict (convergence layer)
└── engine.py                  # Zone classification, convergence, verdicts

output/                        # Presentation / print functions
├── technical.py               # Technical analysis display
├── macro.py                   # Macro dashboard display
└── verdict.py                 # Verdict table & one-liner display

scoring/                       # Backwards-compatibility shims
├── eps.py, roe.py, ...        # Re-export from fundamental/*
├── technical.py               # Re-export from technical/ + output/
├── macro.py                   # Re-export from macro/ + output/
└── verdict.py                 # Re-export from verdict/ + output/

utils/                         # Shared infrastructure
├── data.py                    # Ticker loading + Yahoo Finance
├── database.py                # SQLite score storage
├── discovery.py               # Finviz screener integration
├── formatting.py              # Table output formatting (color-coded)
├── colors.py                  # ANSI terminal color helpers
├── cache.py                   # API response caching
├── chart.py                   # Score trend chart generation (PNG)
├── config.py                  # YAML config loader with defaults
├── export.py                  # CSV / Excel export
├── peers.py                   # Same-sector peer comparison
└── lists.py                   # Portfolio/watchlist file management

tests/                         # Unit tests (pytest)
├── test_scoring.py            # All 7 scoring modules
├── test_config.py             # Config loading, merging, weights
├── test_database.py           # Save, retrieve, migration
├── test_export.py             # CSV/Excel output
├── test_alerts.py             # Alert scanning logic
└── test_lists.py              # Portfolio/watchlist CRUD + cross-list moves
```

## Architecture

The codebase is organized into independent domain packages:

| Package | Responsibility | Dependencies |
|---------|---------------|--------------|
| `fundamental/` | Score stocks on 7 fundamental criteria | `utils/data`, `utils/config` |
| `technical/` | Compute technical indicators & score | `numpy` |
| `macro/` | Fetch & score global macro indicators | `yfinance`, `numpy` |
| `verdict/` | Converge 3 scores into actionable verdict | None (pure logic) |
| `output/` | Format & print results to terminal | Domain packages (read-only) |
| `commands/` | CLI handlers — wire domains together | Domain + output + utils |
| `utils/` | Shared infrastructure (data, DB, cache) | External libraries |
| `scoring/` | Backwards-compat shims (re-exports) | Domain + output packages |

Each domain package can be imported and used independently:

```python
from fundamental import analyze_eps, analyze_roe
from technical.analysis import analyze_technical
from macro.analysis import analyze_macro
from verdict.engine import compute_verdict
```
