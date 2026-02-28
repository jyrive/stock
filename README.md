# Buffett Stock Screener

A Python toolkit for finding and analyzing stocks using Warren Buffett's investment principles.

- **Screen** — scan Finviz for candidates matching Buffett-style filters
- **Analyze** — deep-score stocks on EPS growth, ROE, FCF, balance sheet, dividends, and DCF intrinsic value
- **Technical** — entry-timing signals using RSI, SMA, Bollinger Bands, MACD, and 52-week range
- **Macro** — global macro environment dashboard (VIX, yields, S&P/STOXX/Nikkei/EM, commodities, USD)
- **Verdict** — triangulated decision engine: converge Fundamental + Technical + Macro into actionable verdicts
- **Track** — store scores in SQLite and spot changes over time
- **Portfolio & Watchlist** — manage stocks you own vs. stocks you're watching
- **Deep Dive** — tailored manual due-diligence checklist with peer comparison
- **Discover** — scan all Finviz presets at once, ranked by conviction
- **Export** — save results to CSV or styled Excel spreadsheets
- **Config** — customize scoring weights, DCF assumptions, and thresholds via YAML
- **Tests** — 47 pytest tests covering scoring, config, database, export, alerts, and list management

---

## Quick Start

```bash
git clone https://github.com/jyrive/stock.git
cd stock
python -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy finvizfinance requests-cache matplotlib pyyaml
pip install pytest          # optional: run unit tests
pip install openpyxl        # optional: Excel export (.xlsx)
```

---

## Usage

```bash
python stock.py analyze AAPL MSFT       # deep fundamental analysis
python stock.py technical AAPL          # entry-timing signals
python stock.py macro                   # global macro dashboard
python stock.py verdict AAPL            # triangulated verdict
python stock.py screen high_roe         # discover candidates
python stock.py daily                   # quick morning workflow
python stock.py weekly                  # portfolio + watchlist review
python stock.py monthly                 # full review + discover
```

Single-letter aliases: `a` (analyze), `t` (technical), `m` (macro), `v` (verdict), `s` (screen), `h` (history), `d` (deepdive), `c` (chart), `p` (portfolio), `w` (watchlist).

Passing tickers without a command defaults to `analyze`:

```bash
python stock.py AAPL MSFT GOOGL
```

**Full command reference →** [docs/commands.md](docs/commands.md)

---

## Three-Layer Decision Model

| Layer | Score | Question |
|-------|-------|----------|
| Buffett Score | 0–100 | **WHAT** to buy (fundamental quality) |
| Technical Score | 0–100 | **WHEN** to buy (stock-level entry) |
| Macro Score | 0–100 | **HOW MUCH** to buy (position sizing) |

The `verdict` command converges all three into an actionable verdict (STRONG BUY → AVOID).

**Scoring formulas & table columns →** [docs/scoring.md](docs/scoring.md)

---

## Buffett's Method

The tool automates Buffett's quantitative steps (EPS, ROE, FCF, DCF, balance sheet, dividends) and guides you through the qualitative ones (moat, management, business understanding) via the `deepdive` command.

**Full mapping →** [docs/buffett-method.md](docs/buffett-method.md)

---

## Project Structure

```
stock.py              # Unified CLI entry point
fundamental/          # Fundamental scoring (7 modules)
technical/            # Technical analysis (RSI, SMA, BB, MACD)
macro/                # Global macro environment scoring
verdict/              # Triangulated verdict engine
output/               # Presentation / print functions
commands/             # CLI command handlers
utils/                # Shared infrastructure (data, DB, cache)
scoring/              # Backwards-compatibility shims
tests/                # 47 pytest tests
```

**Full structure & architecture →** [docs/project-structure.md](docs/project-structure.md)

---

## Requirements

| Package | Purpose | Required? |
|---------|---------|----------|
| [yfinance](https://github.com/ranaroussi/yfinance) | Financial data from Yahoo Finance | **Yes** |
| [finvizfinance](https://github.com/lit26/finvizfinance) | Finviz screener API | **Yes** |
| [requests-cache](https://github.com/requests-cache/requests-cache) | API response caching (4hr SQLite) | **Yes** |
| [matplotlib](https://matplotlib.org/) | Score trend chart generation (PNG) | **Yes** |
| pandas, numpy | Data manipulation | **Yes** |
| [pyyaml](https://pyyaml.org/) | Config file support (`config.yaml`) | **Yes** |
| [pytest](https://pytest.org/) | Run unit tests | Optional |
| [openpyxl](https://openpyxl.readthedocs.io/) | Styled Excel export (`.xlsx`) | Optional |

Python 3.10+ required.

```bash
pip install yfinance pandas numpy finvizfinance requests-cache matplotlib pyyaml pytest openpyxl
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

47 tests cover all scoring modules, config loading, database operations, export, alerts, and list management — all using mock data (no network calls).

---

## Documentation

| Document | Content |
|----------|---------|
| [docs/commands.md](docs/commands.md) | All CLI commands, workflows, ticker management, example output |
| [docs/scoring.md](docs/scoring.md) | Scoring formulas, weights, verdict logic, table column reference |
| [docs/buffett-method.md](docs/buffett-method.md) | How Buffett's 15-step process maps to this tool |
| [docs/project-structure.md](docs/project-structure.md) | Directory layout, architecture, package dependencies |

---

## Disclaimer

This is a screening tool for research purposes only. It is not financial advice. Always do your own due diligence before investing.
