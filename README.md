# Buffett Stock Screener

A Python-based stock screener that evaluates companies against Warren Buffett's core investment criteria.

## What It Does

Screens stocks on five Buffett fundamentals and assigns a weighted score (0–100):

| Criteria | Weight | What It Measures |
|----------|--------|-----------------|
| **EPS Growth** | 25% | Consistent earnings growth over 4+ years, CAGR |
| **ROE** | 25% | Return on equity >15% with reasonable debt |
| **Free Cash Flow** | 30% | Positive, growing FCF and FCF yield |
| **Valuation (DCF)** | 20% | Margin of safety vs. discounted cash flow intrinsic value |

Each stock gets a detailed breakdown plus a summary ranking.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy
```

## Usage

**Screen all tickers from `tickers.txt`:**
```bash
python buffett_screener.py
```

**Screen specific tickers from the command line:**
```bash
python buffett_screener.py AAPL MSFT GOOGL
```

**Use a different ticker file:**
```bash
python buffett_screener.py my_picks.txt
```

## Editing the Ticker List

Edit `tickers.txt` — one ticker per line. Use `#` for comments and blank lines to organize:

```
# Tech
AAPL
MSFT

# Financials
JPM
BRK-B
```

Comma-separated tickers on a single line also work: `AAPL, MSFT, GOOGL`

## Output

- Terminal: ranked results with per-stock breakdowns (EPS history, ROE trend, FCF, DCF valuation)
- `buffett_results.json`: full results in JSON for further analysis

## DCF Assumptions

Conservative Buffett-style defaults:
- Years 1–5 growth: 8%
- Years 6–10 growth: 3%
- Terminal growth: 2.5%
- Discount rate: 10%

## Disclaimer

This is a screening tool for research purposes only. It is not financial advice. Always do your own due diligence before investing.
