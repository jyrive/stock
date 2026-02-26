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

## Project Structure

```
buffett_screener.py        # CLI entry point — score & rank stocks
discover.py                # Discovery scanner — find new candidates online
tickers.txt                # Editable ticker list
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

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy finvizfinance
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

## Discovering New Candidates

Scan Finviz for stocks matching Buffett-style filters that aren't already in your `tickers.txt`:

```bash
python discover.py                  # default "buffett" preset
python discover.py high_roe          # ROE > 30%, mid-cap+
python discover.py growth_value      # growing + P/E < 25
python discover.py fcf_machines      # high margins, low debt
python discover.py buffett_mega      # mega-caps only (>$200B)
python discover.py --list            # show all presets
```

The output shows which matches you already track and lists new candidates with a ready-to-copy command to run the full screener on them.

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
