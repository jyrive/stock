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

### Scoring Explained

The **Buffett Score** (0–100) is a weighted sum of four sub-scores:

$$\text{Buffett Score} = \text{EPS} \times 0.25 + \text{ROE} \times 0.25 + \text{FCF} \times 0.30 + \text{DCF} \times 0.20$$

#### EPS Score (0–100) — Earnings Per Share Growth

Measures whether the company grows earnings consistently year over year.

| Component | How it's calculated | Points |
|-----------|-------------------|--------|
| **Consistency** | % of years where EPS grew vs. prior year (need ≥65% to pass) | Up to 50 |
| **CAGR** | Compound Annual Growth Rate of EPS over all available years | Up to 50 (2.5 pts per 1% CAGR, capped at 20%+) |

- **EPS CAGR** — the annualized growth rate. Example: CAGR of 12% means EPS grew ~12% per year on average.
- **Consistent ✅/❌** — ✅ if EPS increased in at least 65% of year-over-year periods.

#### ROE Score (0–100) — Return on Equity

Measures how efficiently the company generates profit from shareholders' equity, adjusted for debt levels.

| Component | How it's calculated | Points |
|-----------|-------------------|--------|
| **Current ROE level** | ROE >30%: 50 pts, >20%: 40, >15%: 30, >10%: 15 | Up to 50 |
| **Debt/Equity** | D/E <150: 25 pts (reasonable), <200: 10 pts | Up to 25 |
| **Consistency bonus** | ROE >15% in all historical years: 25 pts, >70% of years: 15 pts | Up to 25 |

- **ROE%** — Net Income ÷ Shareholders' Equity × 100. Buffett looks for >15% sustained.
- **D/E** — Debt-to-Equity ratio. Lower is better; <150 is considered reasonable.

#### FCF Score (0–100) — Free Cash Flow

Measures the actual cash a company generates after capital expenditures.

| Component | How it's calculated | Points |
|-----------|-------------------|--------|
| **Positive FCF** | Current year FCF > 0 | 30 |
| **Positive streak** | ≥4 consecutive years positive: 25 pts, ≥3 years: 15 pts | Up to 25 |
| **Growing** | Most recent FCF > earliest FCF (over 3+ years) | 25 |
| **FCF Yield** | FCF ÷ Market Cap × 100. >3%: 20 pts, >2%: 10 pts | Up to 20 |

- **FCF (in $B)** — Free Cash Flow = Operating Cash Flow − Capital Expenditures.
- **FCF Yield** — how much free cash the company generates relative to its market price. Higher = cheaper.
- **Growing ✅/❌** — ✅ if FCF has grown from the earliest to the most recent year.

#### DCF / Valuation (0 or 25) — Discounted Cash Flow

A binary check: is the stock undervalued based on a conservative DCF model?

| Metric | Meaning |
|--------|---------|
| **Intrinsic Value** | Estimated fair price per share based on projected future FCF discounted to today |
| **MoS% (Margin of Safety)** | $(Intrinsic - Price) ÷ Intrinsic × 100$. Positive = undervalued. |
| **Upside%** | $(Intrinsic ÷ Price - 1) × 100$. How much the stock could rise to reach fair value. |
| **Undervalued ✅/❌** | ✅ if intrinsic value > current price × 1.15 (i.e., >15% margin of safety) |

If undervalued → 25 points (× 0.20 weight = 5 pts to final score). Otherwise 0.

### Summary Table Columns

The summary table and history viewer use these abbreviations:

| Column | Full Name | What It Tells You |
|--------|-----------|-------------------|
| **Score** | Buffett Score | Overall weighted score (0–100). Higher = more Buffett-like. |
| **ROE%** | Return on Equity | Profitability per dollar of equity. >15% is good, >30% is excellent. |
| **EPS CAGR** | EPS Compound Annual Growth Rate | Annualized earnings growth. >10% is strong. |
| **FCF Yld** | Free Cash Flow Yield | Cash generation relative to market cap. >3% is attractive. |
| **MoS%** | Margin of Safety | How cheap/expensive vs. DCF intrinsic value. Positive = bargain. |
| **Underval** | Undervalued | ✅ if MoS >15%, meaning meaningful discount to intrinsic value. |
| **EPS** | EPS Sub-Score | Component score (0–100) for earnings growth quality. |
| **ROE** | ROE Sub-Score | Component score (0–100) for return on equity + debt. |
| **FCF** | FCF Sub-Score | Component score (0–100) for free cash flow strength. |

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

### 3. Browse Score History

Every screening run saves scores to a local SQLite database (`scores.db`) with today's date. Re-running on the same day overwrites previous results.

```bash
python history.py                    # latest scores + biggest movers
python history.py AAPL               # score history for a ticker
python history.py AAPL MSFT GOOGL    # compare multiple tickers
python history.py --dates            # list all scan dates
python history.py --date 2026-02-27  # show all scores from a specific date
python history.py --movers           # biggest score changes over time
```

Use this to spot stocks that **stand out at a specific moment** — a sudden score jump or drop tells you something changed, and you can investigate why.

### 4. Typical Workflow

```
 ┌─────────────────────────────────────────────────┐
 │  1. python discover.py high_roe                 │ ← find new candidates
 │  2. Copy the suggested command from output      │
 │  3. python buffett_screener.py ACN LULU MNST    │ ← deep-score them
 │  4. Add winners to tickers.txt                  │ ← track going forward
 │  5. python buffett_screener.py                  │ ← re-rank full list
 │  6. python history.py --movers                  │ ← spot changes over time
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
| **scores.db** | SQLite database with historical scores (date-based, same-day overwrites). Query with `python history.py`. |

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
history.py                 # Score history viewer — track changes over time
tickers.txt                # Editable ticker list (one per line, # comments)
screener/
├── __init__.py            # Package exports
├── data.py                # Ticker loading + yfinance data fetching
├── db.py                  # SQLite score storage and queries
├── discovery.py           # Finviz screener integration
├── analysis.py            # Re-exports from analysis sub-modules
├── eps.py                 # EPS consistency & growth analysis
├── roe.py                 # Return on equity & debt analysis
├── fcf.py                 # Free cash flow strength analysis
├── dcf.py                 # DCF intrinsic value calculation
└── output.py              # Terminal display formatting
```

## Requirements

- Python 3.10+
- [yfinance](https://github.com/ranaroussi/yfinance) — financial data from Yahoo Finance
- [finvizfinance](https://github.com/lit26/finvizfinance) — Finviz screener API
- pandas, numpy

## Disclaimer

This is a screening tool for research purposes only. It is not financial advice. Always do your own due diligence before investing.
