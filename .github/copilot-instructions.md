# Copilot Instructions — Stock Screener

## Project Overview

This is a **Python CLI toolkit** for finding and analyzing stocks using fundamental investment principles. The single entry point is `stock.py`, which dispatches to command modules. It uses a **three-layer decision model** (Fundamental / Technical / Macro) converged by a verdict engine.

## Architecture

```
stock.py              → CLI entry point (lazy-imports command modules)
analysis/             → Domain logic (scoring & indicators)
  fundamental.py      → 7 fundamental scorers (EPS, ROE, FCF, Balance, Dividend, DCF, Revenue)
  technical.py        → 5 technical indicators (RSI, SMA, Bollinger, MACD, 52-week)
  macro.py            → 12 macro indicators (VIX, yields, indices, commodities, USD)
  verdict.py          → Triangulation engine (zone classify → converge → verdict)
commands/             → CLI command handlers (one file per command)
utils/                → Shared infrastructure (data fetching, DB, config, export, formatting)
simulation/           → Paper-trading engine & backtester
tests/                → pytest unit tests (mock data, no network)
docs/                 → Architecture, commands, scoring reference
```

### Key Design Principles

- **Domain packages are independent**: `analysis/` modules can be imported standalone. They depend only on `utils/config` and external libraries, never on `commands/` or each other (except verdict consuming scores).
- **Commands wire things together**: `commands/` modules import from `analysis/` and `utils/`, call scorers, format output, and save to DB.
- **Lazy imports**: `stock.py` uses `importlib.import_module()` for fast startup — only the invoked command is loaded.
- **No averaging in verdicts**: The verdict engine classifies each score into zones (Strong ≥70 / Neutral 40–69 / Weak <40), checks pairwise convergence, and applies a veto rule (<25 caps at WATCH).

## Data Sources

- **yfinance** — all financial data: prices, fundamentals, income/balance/cashflow statements, macro indicators.
- **finvizfinance** — stock discovery/screening only (transient, never stored).
- **SQLite** (`scores.db`) — persistent score history, simulation state.

## Scoring System

Each scorer produces a **0–100 sub-score**. The fundamental composite is a **weighted average** (weights defined in `utils/config.py` DEFAULTS, overridable via `config.yaml`):

| Scorer | Weight | Module |
|--------|--------|--------|
| EPS Growth | 15% | `analysis.fundamental.analyze_eps_growth()` |
| ROE | 15% | `analysis.fundamental.analyze_roe()` |
| Free Cash Flow | 20% | `analysis.fundamental.analyze_free_cash_flow()` |
| Balance Sheet | 15% | `analysis.fundamental.analyze_balance_sheet()` |
| Dividends | 5% | `analysis.fundamental.analyze_dividends()` |
| DCF Valuation | 15% | `analysis.fundamental.calculate_dcf_intrinsic_value()` |
| Revenue Growth | 15% | `analysis.fundamental.analyze_revenue_growth()` |

Technical Score and Macro Score are separate 0–100 scores, combined by the verdict engine.

## Coding Conventions

- **Python 3.10+**, no type annotations currently used.
- **No classes** — the codebase is functional: top-level functions, dict-based data passing.
- **Data dict pattern**: `get_financial_data(ticker)` returns a dict with keys `symbol`, `name`, `sector`, `industry`, `info`, `income_stmt`, `balance_sheet`, `cash_flow`, `market_cap`, `current_price`, `trailing_pe`. All scorers consume this dict.
- **Result dicts**: Each scorer returns a dict (e.g., `{"eps_score": 75, "eps_values": [...], ...}`). Keys are snake_case with the scorer name as prefix.
- **Score range**: Always 0–100 integer (or float rounded to 1 decimal for composites).
- **Config-driven**: Thresholds and weights live in `utils/config.py` DEFAULTS dict, overridable via `config.yaml`. Use `get_weights()`, `get_dcf_params()`, `load_config()`.
- **NumPy for math**: Use `numpy` for indicator calculations (RSI, SMA, etc.), not pandas.
- **Pandas for statements**: Financial statements are `pd.DataFrame` with row labels as index and date columns.
- **Error handling**: Scorers should return a default/zero-score dict on missing data, never raise. Wrap yfinance calls in try/except.
- **No global state**: Functions receive data as arguments and return results.

## File Conventions

- **portfolio.txt / watchlist.txt**: One ticker per line, `#` comments, blank lines ignored.
- **config.yaml**: Optional user config, deep-merged over DEFAULTS.
- **scores.db**: Auto-created SQLite, one row per (ticker, date). Re-running same day overwrites.

## Testing

- Tests are in `tests/` using **pytest**.
- All tests use **mock data** (`_make_data()` helper) — no network calls.
- Run: `python -m pytest tests/ -q`
- When adding a new scorer or modifying scoring logic, add or update tests in `tests/test_scoring.py`.
- Test files follow the pattern `test_<module>.py`.

## Adding a New Command

1. Create `commands/<name>.py` with a `main(args)` function.
2. Register it in `stock.py` `_CMD_MODULES` dict.
3. Optionally add a single-letter alias in `_ALIASES`.
4. Add help text to the `_help()` function.

## Adding a New Scorer

1. Add the scoring function to `analysis/fundamental.py` — accept `data` dict, return result dict with `<name>_score` key (0–100).
2. Add its weight to `utils/config.py` DEFAULTS `"weights"` dict (ensure all weights sum to 1.0).
3. Wire it into `commands/analyze.py` `screen_stock()` and `_compute_score()`.
4. Add tests in `tests/test_scoring.py` using mock data.

## Common Patterns

```python
# Fetching data for a ticker
from utils.lists import get_financial_data
data = get_financial_data("AAPL")

# Running all fundamental scorers
from analysis.fundamental import (
    analyze_eps_growth, analyze_roe, analyze_free_cash_flow,
    analyze_balance_sheet, analyze_dividends,
    calculate_dcf_intrinsic_value, analyze_revenue_growth,
)
eps = analyze_eps_growth(data)
# ... each returns a dict with a *_score key

# Technical analysis
from analysis.technical import analyze_technical
tech = analyze_technical("AAPL")  # takes ticker string, fetches prices internally

# Verdict
from analysis.verdict import compute_verdict
verdict = compute_verdict(fundamental_score, tech_score, macro_score)

# Database
from utils.scores_db import save_scores, connect_db
save_scores(result_dict)

# Config
from utils.config import get_weights, get_dcf_params, load_config
```

## Virtual Environment

Always use the project virtual environment for running commands:

```bash
source .venv/bin/activate          # activate before running anything
python stock.py analyze AAPL       # use `python` (not `python3` or system Python)
python -m pytest tests/ -q         # run tests inside venv
pip install -r requirements.txt    # install deps into venv
```

If `.venv` does not exist, create it first:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Dependencies

Core: `yfinance`, `numpy`, `pandas`, `finvizfinance`, `requests`, `requests-cache`, `matplotlib`, `pyyaml`, `scikit-learn`, `openpyxl`.

Testing: `pytest`.

## CLI Usage

```bash
python stock.py analyze AAPL MSFT       # fundamental analysis
python stock.py technical AAPL          # entry-timing signals
python stock.py macro                   # macro dashboard
python stock.py verdict AAPL            # triangulated verdict
python stock.py daily                   # quick morning workflow
```

Passing tickers without a command defaults to `analyze`. Single-letter aliases: `a`, `t`, `m`, `v`, `s`, `h`, `d`, `c`, `p`, `w`.
