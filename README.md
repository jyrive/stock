# Buffett Stock Screener

A Python tool that screens stocks against Warren Buffett's investment criteria and discovers new candidates from online screeners.

## Quick Start

```bash
git clone https://github.com/jyrive/stock.git
cd stock
python -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy finvizfinance
```

## How It Works

The screener evaluates every stock on four Buffett fundamentals and assigns a weighted score (0–100):

| Criteria | Weight | What It Measures |
|----------|--------|-----------------|
| **EPS Growth** | 25% | Consistent earnings growth over 4+ years (CAGR) |
| **ROE** | 25% | Return on equity >15% with reasonable debt-to-equity |
| **Free Cash Flow** | 30% | Positive, growing FCF and FCF yield |
| **Valuation (DCF)** | 20% | Margin of safety based on discounted cash flow |

Each stock gets a detailed breakdown (EPS history, ROE trend, FCF streak, DCF intrinsic value) plus a summary ranking table.

---

## Usage

### 1. Screen Stocks

Run the screener against your tracked tickers in `tickers.txt`:

```bash
python buffett_screener.py
```

Screen specific tickers directly (no file needed):

```bash
python buffett_screener.py AAPL MSFT GOOGL V BRK-B
```

Use a custom ticker file:

```bash
python buffett_screener.py my_watchlist.txt
```

If no tickers are found (empty file, no CLI args), you'll get an interactive prompt to type them in.

### 2. Discover New Candidates

Find stocks from Finviz that match Buffett-style filters but **aren't already in your `tickers.txt`**:

```bash
python discover.py
```

This scans Finviz, compares the results against your existing list, and shows:
- Which matches you already track
- **New candidates** you haven't seen yet
- A ready-to-paste command to run the full screener on the new ones

#### Discovery Presets

```bash
python discover.py buffett          # Default: large-cap, ROE >15%, EPS growth, margins >15%
python discover.py buffett_mega     # Mega-caps >$200B, ROE >15%, margins >20%
python discover.py growth_value     # Mid+ cap, ROE >15%, EPS growth >10%, P/E <25
python discover.py high_roe         # Mid+ cap, ROE >30%
python discover.py fcf_machines     # Mid+ cap, ROE >15%, margins >20%, current ratio >1.5
python discover.py --list           # Show all presets with descriptions
```

### 3. Typical Workflow

```
 ┌─────────────────────────────────────────────────┐
 │  1. python discover.py high_roe                 │ ← find new candidates
 │  2. Copy the suggested command from output      │
 │  3. python buffett_screener.py ACN LULU MNST    │ ← deep-score them
 │  4. Add winners to tickers.txt                  │ ← track going forward
 │  5. python buffett_screener.py                  │ ← re-rank full list
 └─────────────────────────────────────────────────┘
```

---

## Managing Your Ticker List

Edit `tickers.txt` — one ticker per line. Use `#` for comments and blank lines to organize by sector:

```
# Technology
AAPL
MSFT
GOOGL

# Financials
JPM
BRK-B
V
```

Comma-separated tickers on a single line also work: `AAPL, MSFT, GOOGL`

---

## Output

| Output | Description |
|--------|-------------|
| **Terminal** | Ranked results with per-stock breakdowns (EPS history, ROE trend, FCF, DCF valuation) and a summary table |
| **buffett_results.json** | Full results in JSON for further analysis or integration |

### Example Output

```
──────────────────────────────────────────────────────────────────────
  #1  MSFT - Microsoft Corporation
──────────────────────────────────────────────────────────────────────
  Sector: Technology | Market Cap: $2985.7B | Price: $401.72
  Buffett Score: 72.2/100

  📈 EPS GROWTH (Score: 81/100)
     EPS History: 2022: $9.65 → 2023: $9.68 → 2024: $11.8 → 2025: $13.64
     CAGR: 12.23% | Consistent: ✅

  💰 ROE & DEBT (Score: 100/100)
     Current ROE: 34.39% | Debt/Equity: 31.54 | Reasonable: ✅

  💵 FREE CASH FLOW (Score: 90/100)
     Current FCF: $71.61B | FCF Yield: 2.4% | Growing: ✅

  🎯 INTRINSIC VALUE / DCF
     Intrinsic Value: $168.48 vs Price: $401.72
     Margin of Safety: -138.44% | Undervalued: ❌
```

---

## DCF Model Assumptions

Conservative Buffett-style defaults hardcoded in [screener/dcf.py](screener/dcf.py):

| Parameter | Value |
|-----------|-------|
| Years 1–5 FCF growth | 8% |
| Years 6–10 FCF growth | 3% |
| Terminal growth rate | 2.5% |
| Discount rate (required return) | 10% |

---

## Project Structure

```
buffett_screener.py        # CLI entry point — score & rank stocks
discover.py                # Discovery scanner — find new candidates online
tickers.txt                # Editable ticker list (one per line, # comments)
screener/
├── __init__.py            # Package exports
├── data.py                # Ticker loading + yfinance data fetching
├── discovery.py           # Finviz screener integration
├── analysis.py            # Re-exports from analysis sub-modules
├── eps.py                 # EPS consistency & growth analysis
├── roe.py                 # Return on equity & debt analysis
├── fcf.py                 # Free cash flow strength analysis
├── dcf.py                 # DCF intrinsic value calculation
└── output.py              # Terminal display + JSON export
```

## Requirements

- Python 3.10+
- [yfinance](https://github.com/ranaroussi/yfinance) — financial data from Yahoo Finance
- [finvizfinance](https://github.com/lit26/finvizfinance) — Finviz screener API
- pandas, numpy

## Disclaimer

This is a screening tool for research purposes only. It is not financial advice. Always do your own due diligence before investing.
