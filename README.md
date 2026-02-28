# Buffett Stock Screener

A Python toolkit for finding and analyzing stocks using Warren Buffett's investment principles.

- **Screen** — scan Finviz for candidates matching Buffett-style filters
- **Analyze** — deep-score stocks on EPS growth, ROE, FCF, balance sheet, dividends, and DCF intrinsic value
- **Track** — store scores in SQLite and spot changes over time
- **Chart** — plot score trends from history as PNG charts
- **Deep Dive** — get a tailored manual due-diligence checklist for any stock
- **Cache** — transparent API response caching for faster re-runs

---

## Quick Start

```bash
git clone https://github.com/jyrive/stock.git
cd stock
python -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy finvizfinance requests-cache matplotlib
```

---

## Buffett's Method vs. This Tool

Warren Buffett's investment process has both quantitative (numbers) and qualitative (judgment) parts. This tool automates the quantitative side and flags where you still need to do your own thinking.

| # | Buffett's Step | This Tool | Status |
|---|---------------|-----------|--------|
| 1 | **Understand the business** — only invest in what you understand | Shows sector/industry labels. `deepdive.py` asks you to explain the business in one sentence. | ⚠️ Guided |
| 2 | **Durable competitive advantage (moat)** — brand, patents, switching costs, network effects | Sustained high ROE as quantitative proxy. `deepdive.py` walks you through identifying the moat source. | ⚠️ Guided |
| 3 | **Consistent earnings growth** — upward EPS over many years, not erratic | EPS consistency check (≥65% years growing) + CAGR scoring. | ✅ Covered |
| 4 | **High return on equity** — ROE >15% sustained over time | Current ROE level + historical consistency bonus + D/E penalty. | ✅ Covered |
| 5 | **Conservative debt** — can pay off debt from a few years of earnings | D/E ratio check (<150 = reasonable). Cash/Debt ratio scored in balance sheet module. | ✅ Covered |
| 6 | **Strong free cash flow** — business converts earnings into real cash | FCF streak, growth trend, and FCF yield scored. | ✅ Covered |
| 7 | **Owner earnings** — net income + depreciation − capex − working capital changes | FCF (operating cash flow − capex) is a close approximation. Does not compute Buffett's exact owner earnings formula. | ⚠️ Approx |
| 8 | **Intrinsic value & margin of safety** — buy only at a significant discount to fair value | 10-year DCF model with terminal value. Flags undervalued when IV > Price × 1.15. | ✅ Covered |
| 9 | **Management quality** — honest, shareholder-oriented, good capital allocators | `deepdive.py` provides a management checklist (CEO tenure, insider ownership, capital allocation, compensation). Research links included. | ⚠️ Guided |
| 10 | **Reasonable price** — don't overpay even for a great business | P/E displayed. FCF yield calculated. Finviz preset filters P/E < 25. | ✅ Covered |
| 11 | **Predictable earnings** — avoid cyclicals and turnarounds | EPS consistency ratio catches erratic earnings. Doesn't assess revenue stability or customer concentration. | ⚠️ Partial |
| 12 | **High profit margins** — pricing power and operational efficiency | Finviz presets filter operating margin >15–20%. Analyzer doesn't score margins independently. | ⚠️ Partial |
| 13 | **Dividends & shareholder returns** — cash returned via dividends and buybacks | Dividend yield, payout ratio, consecutive increases, and growth scoring. Buyback tracking not included. | ✅ Covered |
| 14 | **Balance sheet strength** — liquidity, retained earnings, acquisition discipline | Current ratio, cash/debt, retained earnings trend, goodwill % of assets. | ✅ Covered |
| 15 | **Industry positioning** — long-term tailwinds, avoid commoditized sectors | Sector/industry labels shown. No automated industry-quality scoring. | ⚠️ Partial |

**Bottom line:** the tool handles steps 3–6, 8, 10, 13, and 14 quantitatively. Steps 1, 2, 7, 9 are guided by `deepdive.py` (tells you exactly what to check and where). The rest are partially covered — the numbers are there, but interpreting them is up to you.

---

## Usage

### Unified CLI

All commands are available through `stock.py`:

```bash
python stock.py analyze AAPL MSFT    # deep fundamental analysis
python stock.py screen high_roe      # discover candidates via Finviz
python stock.py history --movers     # browse score history
python stock.py deepdive AAPL        # due-diligence checklist
python stock.py chart AAPL MSFT      # plot score trends as PNG
python stock.py cache stats          # show cache info
python stock.py cache clear          # clear cached API responses
```

Single-letter aliases work too: `a` (analyze), `s` (screen), `h` (history), `d` (deepdive), `c` (chart).

If you pass tickers without a command, it defaults to `analyze`:

```bash
python stock.py AAPL MSFT GOOGL      # same as: python stock.py analyze AAPL MSFT GOOGL
```

### 1. Screen — Find Candidates

Scan Finviz for stocks matching Buffett-style filters. Shows candidates **not already in your `tickers.txt`**:

```bash
python stock.py screen                # default "buffett" preset
python stock.py screen high_roe      # use a specific preset
python stock.py screen --list        # show available presets
```

#### Presets

| Preset | Market Cap | Key Filters |
|--------|-----------|-------------|
| `buffett` | Large+ | ROE >15%, EPS growth, margins >15% |
| `buffett_mega` | Mega (>$200B) | ROE >15%, margins >20% |
| `growth_value` | Mid+ | ROE >15%, EPS growth >10%, P/E <25 |
| `high_roe` | Mid+ | ROE >30% |
| `fcf_machines` | Mid+ | ROE >15%, margins >20%, current ratio >1.5 |

Output includes a ready-to-paste command to analyze the new candidates.

### 2. Analyze — Deep-Score Stocks

Run full fundamental analysis on specific tickers. Each stock gets scored on EPS, ROE, FCF, balance sheet, dividends, and DCF:

```bash
python stock.py analyze               # analyze tickers from tickers.txt
python stock.py analyze AAPL MSFT GOOGL  # analyze specific tickers
python stock.py analyze my_watchlist.txt  # analyze tickers from a custom file
```

API responses are cached for 4 hours to speed up repeated runs.

If no tickers are provided, you'll get an interactive prompt.

Results are saved to `scores.db` (SQLite) with today's date. Re-running on the same day overwrites previous results.

### 3. Track — Browse Score History

```bash
python stock.py history               # latest scores + biggest movers
python stock.py history AAPL         # score history for a ticker
python stock.py history AAPL MSFT GOOGL  # compare multiple tickers
python stock.py history --dates      # list all scan dates
python stock.py history --date 2026-02-27  # show scores from a specific date
python stock.py history --movers     # biggest score changes over time
python stock.py history --chart AAPL MSFT  # generate score trend chart (PNG)
```

Use this to spot stocks that **stand out at a specific moment** — a sudden score jump or drop tells you something changed, and you can investigate why.

Score trend charts are saved to `charts/` as PNG files.

### 4. Deep Dive — Manual Due-Diligence Checklist

```bash
python stock.py deepdive AAPL         # full checklist for one stock
```

Runs the analysis and prints a **tailored checklist** of what to research manually:

1. Do you understand this business?
2. Competitive advantage (moat) — what is the source?
3. Earnings quality — are they real and sustainable?
4. Balance sheet strength — with specific red flags highlighted
5. Free cash flow — where does the cash go?
6. Dividend quality — yield, payout sustainability, growth streak
7. Valuation — does the price offer margin of safety?
8. Management quality — who runs it and are they honest?
9. Risks to investigate — lawsuits, concentration, disruption
10. Decision checklist — 8 yes/no questions before buying
11. Research links — Yahoo Finance pages for the stock

Every section adapts to the stock's actual numbers (e.g. warns about high debt only if D/E is actually high).

### Typical Workflow

```
 ┌─────────────────────────────────────────────────┐
 │  1. python stock.py screen high_roe             │ ← find new candidates
 │  2. Copy the suggested command from output      │
 │  3. python stock.py analyze ACN LULU MNST       │ ← deep-score them
 │  4. Add winners to tickers.txt                  │ ← track going forward
 │  5. python stock.py analyze                     │ ← re-rank full list
 │  6. python stock.py history --movers            │ ← spot changes over time
 │  7. python stock.py chart LULU                  │ ← visualize score trend
 │  8. python stock.py deepdive LULU               │ ← manual due diligence
 └─────────────────────────────────────────────────┘
```

---

## Ticker Management

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

## Example Output

Each stock gets a detailed per-stock breakdown (with color-coded values in terminal):

```
──────────────────────────────────────────────────────────────────────
  #1  MSFT - Microsoft Corporation
──────────────────────────────────────────────────────────────────────
  Sector: Technology | Market Cap: $2985.7B | Price: $449.26
  Buffett Score: 65.8/100

  📈 EPS GROWTH (Score: 81/100)
     EPS History: 2022: $9.65 → 2023: $9.68 → 2024: $11.8 → 2025: $13.64
     CAGR: 12.23% | Consistent: ✅

  💰 ROE & DEBT (Score: 100/100)
     Current ROE: 34.39% | Debt/Equity: 31.54 | Reasonable: ✅

  💵 FREE CASH FLOW (Score: 90/100)
     Current FCF: $71.61B | FCF Yield: 2.4% | Growing: ✅

  🏦 BALANCE SHEET HEALTH (Score: 56/100)
     Current Ratio: 1.35 | Cash/Debt: 0.67 | Retained Earnings: Growing ✅
     Goodwill % of Assets: 14.0%

  💎 DIVIDENDS (Score: 75/100)
     Yield: 0.67% | Payout Ratio: 23.2%
     Consecutive Increases: 3 yrs | Growing: ✅

  🎯 INTRINSIC VALUE / DCF
     Intrinsic Value: $168.48 vs Price: $449.26
     Margin of Safety: -166.6% | Undervalued: ❌
```

Followed by a summary table:

```
#    Symbol  Name                         Score  EPS  ROE  FCF  BAL  DIV   ROE%    D/E    CR   CAGR  FCF$B  FYld   GW%   DY%  PO%       IV$    MoS%  UV     Price    P/E
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
1    MSFT    Microsoft Corporation         65.8   81  100   90   56   75   34.4%  31.5  1.35  12.2%   71.6  2.4%  14.0%  0.7%  23%   $168.48 -166.6%   ❌   $449.26   34.2
2    V       Visa Inc.                     65.0   90  100  100   35   75   53.6%  54.5  1.41  16.0%   21.6  3.5%  38.1%  0.8%  23%   $224.26  -41.2%   ❌   $316.70   29.8
3    AAPL    Apple Inc.                    48.1   46  100   70   38   50   71.5%    —   0.87  -0.4%  108.8  3.3%   0.0%  0.4%  16%   $342.10  -31.5%   ❌   $210.79   33.0
```


---

## Scoring Reference

### Buffett Score (0–100)

Weighted sum of six sub-scores:

| Criteria | Weight | What It Measures |
|----------|--------|------------------|
| **EPS Growth** | 15% | Consistent earnings growth over 4+ years |
| **ROE** | 15% | Return on equity >15% with reasonable debt |
| **Free Cash Flow** | 20% | Positive, growing FCF and FCF yield |
| **Balance Sheet** | 15% | Liquidity, debt coverage, retained earnings, goodwill |
| **Dividends** | 15% | Dividend yield, payout sustainability, growth streak |
| **Valuation (DCF)** | 20% | Margin of safety based on discounted cash flow |

### EPS Score (0–100)

| Component | How It's Calculated | Points |
|-----------|-------------------|--------|
| Consistency | % of years where EPS grew vs. prior year (need ≥65%) | Up to 50 |
| CAGR | Compound Annual Growth Rate (2.5 pts per 1%, capped at 20%) | Up to 50 |

### ROE Score (0–100)

| Component | How It's Calculated | Points |
|-----------|-------------------|--------|
| Current ROE | >30%: 50, >20%: 40, >15%: 30, >10%: 15 | Up to 50 |
| Debt/Equity | D/E <150: 25 pts, <200: 10 pts | Up to 25 |
| Consistency | ROE >15% all years: 25, >70% of years: 15 | Up to 25 |

### FCF Score (0–100)

| Component | How It's Calculated | Points |
|-----------|-------------------|--------|
| Positive FCF | Current year FCF > 0 | 30 |
| Positive streak | ≥4 consecutive years: 25, ≥3 years: 15 | Up to 25 |
| Growing | Most recent FCF > earliest FCF | 25 |
| FCF Yield | FCF ÷ Market Cap. >3%: 20, >2%: 10 | Up to 20 |

### DCF / Valuation (0 or 25)

Binary check: is the stock undervalued based on a conservative DCF model?

| Parameter | Value |
|-----------|-------|
| Years 1–5 FCF growth | 8% |
| Years 6–10 FCF growth | 3% |
| Terminal growth rate | 2.5% |
| Discount rate | 10% |

Undervalued = intrinsic value > current price × 1.15. If yes → 25 pts (× 0.20 = 5 pts to final score).

### Balance Sheet Health (0–100)

| Component | How It's Calculated | Points |
|-----------|---------------------|--------|
| Current Ratio | ≥2.0: 25, ≥1.5: 20, ≥1.0: 10 | Up to 25 |
| Cash / Debt | ≥1.0: 25, ≥0.5: 20, ≥0.25: 10 | Up to 25 |
| Retained Earnings | Growing ≥75% of years: 25, growing overall: 15 | Up to 25 |
| Goodwill % | <10%: 25, <20%: 15, <30%: 5 | Up to 25 |

### Dividend Score (0–100)

| Component | How It's Calculated | Points |
|-----------|---------------------|--------|
| Pays Dividend | Company pays a dividend | 25 |
| Payout Ratio | ≤60%: 25, ≤80%: 15 | Up to 25 |
| Dividend Yield | ≥2%: 25, ≥1%: 15, >0: 5 | Up to 25 |
| Dividend Growing | Consecutive annual increases | Up to 25 |

### Table Columns

| Column | Full Name | Meaning |
|--------|-----------|---------|
| **#** | Rank | Position sorted by Score (highest first) |
| **Symbol** | Ticker | Stock ticker, e.g. AAPL |
| **Name** | Company Name | Full name (truncated to fit) |
| **Score** | Buffett Score | Weighted score 0–100 |
| **EPS** | EPS Sub-Score | Earnings consistency + growth (0–100) |
| **ROE** | ROE Sub-Score | Return on equity + debt check (0–100) |
| **FCF** | FCF Sub-Score | Free cash flow strength (0–100) |
| **BAL** | Balance Sheet Score | Liquidity, debt coverage, retained earnings, goodwill (0–100) |
| **DIV** | Dividend Score | Dividend quality: yield, payout, growth (0–100) |
| **ROE%** | Return on Equity | Net Income ÷ Equity × 100 |
| **D/E** | Debt-to-Equity | Total Debt ÷ Equity. <150 is reasonable |
| **CR** | Current Ratio | Current Assets ÷ Current Liabilities. >1.5 is healthy |
| **CAGR** | EPS Growth Rate | Compound Annual Growth Rate of EPS |
| **FCF$B** | FCF in Billions | Current year Free Cash Flow |
| **FYld** | FCF Yield | FCF ÷ Market Cap × 100. >3% is attractive |
| **GW%** | Goodwill % | Goodwill ÷ Total Assets × 100. <20% is healthy |
| **DY%** | Dividend Yield | Annual Dividend ÷ Price × 100 |
| **PO%** | Payout Ratio | Dividends ÷ Net Income × 100. <60% is sustainable |
| **IV$** | Intrinsic Value | DCF-estimated fair share price |
| **MoS%** | Margin of Safety | (IV − Price) ÷ IV × 100. Positive = cheap |
| **UV** | Undervalued | ✅ if IV > Price × 1.15, otherwise ❌ |
| **Price** | Current Price | Market price at time of scan (Yahoo Finance) |
| **P/E** | Price-to-Earnings | Share price ÷ trailing EPS |

---

## Project Structure

```
stock.py                       # Unified CLI entry point
tickers.txt                    # Your tracked ticker list

commands/                      # CLI command handlers
├── analyze.py                 # Deep fundamental analysis
├── screen.py                  # Finviz candidate discovery
├── history.py                 # Score history browser
└── deepdive.py                # Due-diligence checklist

scoring/                       # Fundamental analysis modules
├── eps.py                     # EPS consistency & growth
├── roe.py                     # Return on equity & debt
├── fcf.py                     # Free cash flow strength
├── balance.py                 # Balance sheet health
├── dividend.py                # Dividend quality
└── dcf.py                     # DCF intrinsic value

utils/                         # Shared infrastructure
├── data.py                    # Ticker loading + Yahoo Finance
├── database.py                # SQLite score storage
├── discovery.py               # Finviz screener integration
├── formatting.py              # Table output formatting (color-coded)
├── colors.py                  # ANSI terminal color helpers
├── cache.py                   # API response caching
└── chart.py                   # Score trend chart generation (PNG)
```

## Requirements

- Python 3.10+
- [yfinance](https://github.com/ranaroussi/yfinance) — financial data from Yahoo Finance
- [finvizfinance](https://github.com/lit26/finvizfinance) — Finviz screener API
- [requests-cache](https://github.com/requests-cache/requests-cache) — transparent API response caching
- [matplotlib](https://matplotlib.org/) — score trend chart generation
- pandas, numpy

## Disclaimer

This is a screening tool for research purposes only. It is not financial advice. Always do your own due diligence before investing.
