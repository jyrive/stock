# Buffett Stock Screener

A Python toolkit for finding and analyzing stocks using Warren Buffett's investment principles.

- **Screen** — scan Finviz for candidates matching Buffett-style filters
- **Analyze** — deep-score stocks on EPS growth, ROE, FCF, and DCF intrinsic value
- **Track** — store scores in SQLite and spot changes over time

---

## Quick Start

```bash
git clone https://github.com/jyrive/stock.git
cd stock
python -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy finvizfinance
```

---

## Buffett's Method vs. This Tool

Warren Buffett's investment process has both quantitative (numbers) and qualitative (judgment) parts. This tool automates the quantitative side and flags where you still need to do your own thinking.

| # | Buffett's Step | This Tool | Status |
|---|---------------|-----------|--------|
| 1 | **Understand the business** — only invest in what you understand | Shows sector/industry labels. *You* decide if you understand it. | ❌ Manual |
| 2 | **Durable competitive advantage (moat)** — brand, patents, switching costs, network effects | Sustained high ROE + high margins in screener are quantitative proxies for a moat. Source and durability require your judgment. | ⚠️ Proxy |
| 3 | **Consistent earnings growth** — upward EPS over many years, not erratic | EPS consistency check (≥65% years growing) + CAGR scoring. | ✅ Covered |
| 4 | **High return on equity** — ROE >15% sustained over time | Current ROE level + historical consistency bonus + D/E penalty. | ✅ Covered |
| 5 | **Conservative debt** — can pay off debt from a few years of earnings | D/E ratio check (<150 = reasonable). Cash/Debt ratio scored in balance sheet module. | ✅ Covered |
| 6 | **Strong free cash flow** — business converts earnings into real cash | FCF streak, growth trend, and FCF yield scored. | ✅ Covered |
| 7 | **Owner earnings** — net income + depreciation − capex − working capital changes | FCF (operating cash flow − capex) is a close approximation. Does not compute Buffett's exact owner earnings formula. | ⚠️ Approx |
| 8 | **Intrinsic value & margin of safety** — buy only at a significant discount to fair value | 10-year DCF model with terminal value. Flags undervalued when IV > Price × 1.15. | ✅ Covered |
| 9 | **Management quality** — honest, shareholder-oriented, good capital allocators | Not assessed. No insider ownership, tenure, or capital allocation analysis. | ❌ Manual |
| 10 | **Reasonable price** — don't overpay even for a great business | P/E displayed. FCF yield calculated. Finviz preset filters P/E < 25. | ✅ Covered |
| 11 | **Predictable earnings** — avoid cyclicals and turnarounds | EPS consistency ratio catches erratic earnings. Doesn't assess revenue stability or customer concentration. | ⚠️ Partial |
| 12 | **High profit margins** — pricing power and operational efficiency | Finviz presets filter operating margin >15–20%. Analyzer doesn't score margins independently. | ⚠️ Partial |
| 13 | **Dividends & shareholder returns** — cash returned via dividends and buybacks | Not analyzed. No dividend yield, payout ratio, or buyback tracking. | ❌ Not covered |
| 14 | **Balance sheet strength** — liquidity, retained earnings, acquisition discipline | Current ratio, cash/debt, retained earnings trend, goodwill % of assets. | ✅ Covered |
| 15 | **Industry positioning** — long-term tailwinds, avoid commoditized sectors | Sector/industry labels shown. No automated industry-quality scoring. | ⚠️ Partial |

**Bottom line:** the tool handles steps 3–6, 8, 10, and 14 quantitatively. Steps 1, 2, 9, and 13 require your own research. The rest are partially covered — the numbers are there, but interpreting them is up to you.

---

## Usage

### 1. Screen — Find Candidates

Scan Finviz for stocks matching Buffett-style filters. Shows candidates **not already in your `tickers.txt`**:

```bash
python screen.py                     # default "buffett" preset
python screen.py high_roe            # use a specific preset
python screen.py --list              # show available presets
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

Run full fundamental analysis on specific tickers. Each stock gets scored on EPS, ROE, FCF, and DCF:

```bash
python analyze.py                    # analyze tickers from tickers.txt
python analyze.py AAPL MSFT GOOGL    # analyze specific tickers
python analyze.py my_watchlist.txt   # analyze tickers from a custom file
```

If no tickers are provided, you'll get an interactive prompt.

Results are saved to `scores.db` (SQLite) with today's date. Re-running on the same day overwrites previous results.

### 3. Track — Browse Score History

```bash
python history.py                    # latest scores + biggest movers
python history.py AAPL               # score history for a ticker
python history.py AAPL MSFT GOOGL    # compare multiple tickers
python history.py --dates            # list all scan dates
python history.py --date 2026-02-27  # show scores from a specific date
python history.py --movers           # biggest score changes over time
```

Use this to spot stocks that **stand out at a specific moment** — a sudden score jump or drop tells you something changed, and you can investigate why.

### 4. Deep Dive — Manual Due-Diligence Checklist

```bash
python deepdive.py AAPL              # full checklist for one stock
```

Runs the analysis and prints a **tailored checklist** of what to research manually:

1. Do you understand this business?
2. Competitive advantage (moat) — what is the source?
3. Earnings quality — are they real and sustainable?
4. Balance sheet strength — with specific red flags highlighted
5. Free cash flow — where does the cash go?
6. Valuation — does the price offer margin of safety?
7. Management quality — who runs it and are they honest?
8. Risks to investigate — lawsuits, concentration, disruption
9. Decision checklist — 8 yes/no questions before buying
10. Research links — SEC filings, insider trading, analyst estimates

Every section adapts to the stock's actual numbers (e.g. warns about high debt only if D/E is actually high).

### Typical Workflow

```
 ┌─────────────────────────────────────────────────┐
 │  1. python screen.py high_roe                   │ ← find new candidates
 │  2. Copy the suggested command from output      │
 │  3. python analyze.py ACN LULU MNST             │ ← deep-score them
 │  4. Add winners to tickers.txt                  │ ← track going forward
 │  5. python analyze.py                           │ ← re-rank full list
 │  6. python history.py --movers                  │ ← spot changes over time
 │  7. python deepdive.py LULU                     │ ← manual due diligence
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

Each stock gets a detailed per-stock breakdown:

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

Followed by a summary table (identical in `analyze.py` and `history.py`):

```
#    Symbol  Name                         Score  EPS  ROE  FCF   ROE%    D/E   CAGR  FCF$B  FYld       IV$    MoS%  UV     Price    P/E
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
1    ADBE    Adobe Inc.                    84.0   96  100  100    55%     57  18.2%    9.8  9.1%   $419.20   38.2%   ✅   $259.04   15.5
2    CMCSA   Comcast Corporation           80.0  100   80  100    21%    108  64.5%   19.2 17.1%    $93.62   67.0%   ✅    $30.85    5.7
3    V       Visa Inc.                     77.5   90  100  100    54%     55  16.0%   21.6  3.5%   $224.26  -41.2%   ❌   $316.70   29.8
```

---

## Scoring Reference

### Buffett Score (0–100)

Weighted sum of five sub-scores:

$$\text{Score} = \text{EPS} \times 0.20 + \text{ROE} \times 0.20 + \text{FCF} \times 0.25 + \text{BAL} \times 0.15 + \text{DCF} \times 0.20$$

| Criteria | Weight | What It Measures |
|----------|--------|------------------|
| **EPS Growth** | 20% | Consistent earnings growth over 4+ years |
| **ROE** | 20% | Return on equity >15% with reasonable debt |
| **Free Cash Flow** | 25% | Positive, growing FCF and FCF yield |
| **Balance Sheet** | 15% | Liquidity, debt coverage, retained earnings, goodwill |
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

| Component | How It’s Calculated | Points |
|-----------|---------------------|--------|
| Current Ratio | ≥2.0: 25, ≥1.5: 20, ≥1.0: 10 | Up to 25 |
| Cash / Debt | ≥1.0: 25, ≥0.5: 20, ≥0.25: 10 | Up to 25 |
| Retained Earnings | Growing ≥75% of years: 25, growing overall: 15 | Up to 25 |
| Goodwill % | <10%: 25, <20%: 15, <30%: 5 | Up to 25 |

### Table Columns

Both `analyze.py` and `history.py` print the same table:

```
#  Symbol  Name  Score  EPS  ROE  FCF  BAL  ROE%  D/E  CR  CAGR  FCF$B  FYld  GW%  IV$  MoS%  UV  Price  P/E
```

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
| **ROE%** | Return on Equity | Net Income ÷ Equity × 100 |
| **D/E** | Debt-to-Equity | Total Debt ÷ Equity. <150 is reasonable |
| **CR** | Current Ratio | Current Assets ÷ Current Liabilities. >1.5 is healthy |
| **CAGR** | EPS Growth Rate | Compound Annual Growth Rate of EPS |
| **FCF$B** | FCF in Billions | Current year Free Cash Flow |
| **FYld** | FCF Yield | FCF ÷ Market Cap × 100. >3% is attractive |
| **GW%** | Goodwill % | Goodwill ÷ Total Assets × 100. <20% is healthy |
| **IV$** | Intrinsic Value | DCF-estimated fair share price |
| **MoS%** | Margin of Safety | (IV − Price) ÷ IV × 100. Positive = cheap |
| **UV** | Undervalued | ✅ if IV > Price × 1.15, otherwise ❌ |
| **Price** | Current Price | Market price at time of scan (Yahoo Finance) |
| **P/E** | Price-to-Earnings | Share price ÷ trailing EPS |

The detailed per-stock breakdown (printed above the summary table) also shows **Cash/Debt** ratio and **Retained Earnings** trend, which are part of the BAL score but not separate columns in the summary table.

---

## Project Structure

```
screen.py                  # Step 1 — scan Finviz for candidates
analyze.py                 # Step 2 — deep fundamental analysis
history.py                 # Step 3 — browse score history
deepdive.py                # Step 4 — manual due-diligence checklist
tickers.txt                # Your tracked ticker list
screener/
├── __init__.py            # Package exports
├── data.py                # Ticker loading + yfinance data fetching
├── db.py                  # SQLite score storage and queries
├── discovery.py           # Finviz screener integration
├── analysis.py            # Re-exports from analysis sub-modules
├── eps.py                 # EPS consistency & growth analysis
├── roe.py                 # Return on equity & debt analysis
├── fcf.py                 # Free cash flow strength analysis
├── balance.py             # Balance sheet health analysis
├── dcf.py                 # DCF intrinsic value calculation
└── output.py              # Shared table formatting
```

## Requirements

- Python 3.10+
- [yfinance](https://github.com/ranaroussi/yfinance) — financial data from Yahoo Finance
- [finvizfinance](https://github.com/lit26/finvizfinance) — Finviz screener API
- pandas, numpy

## Disclaimer

This is a screening tool for research purposes only. It is not financial advice. Always do your own due diligence before investing.
