# System Architecture

How the stock analysis tool works — data sources, scoring pipeline, storage, and machine learning.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Commands                             │
│  screen / discover │ analyze │ verdict │ study │ collect    │
└────────┬───────────┴────┬────┴────┬────┴───┬──┴─────┬──────┘
         │                │         │        │        │
    ┌────▼────┐    ┌──────▼──────┐  │  ┌─────▼────┐   │
    │ Finviz  │    │  7 Fundmntl │  │  │ ML Study │   │
    │ Screener│    │  Scorers    │  │  │ (sklearn)│   │
    └─────────┘    └──────┬──────┘  │  └─────▲────┘   │
                          │         │        │        │
         ┌────────────────┤    ┌────▼────┐   │   ┌────▼────┐
         │                │    │ Verdict │   │   │ Collect │
    ┌────▼────┐    ┌──────▼──┐│ Engine  │   │   │ Pipeline│
    │Technical│    │  DCF    ││ F+T+M   │   │   └────┬────┘
    │ Analysis│    │Valuation│└─────────┘   │        │
    └────┬────┘    └─────────┘              │        │
         │                            ┌─────▼────────▼──┐
    ┌────▼────┐                       │    SQLite DB     │
    │  Macro  │                       │   scores.db      │
    │ Analysis│                       │  (5 tables)      │
    └─────────┘                       └──────────────────┘
```

---

## 1. Data Sources

### Finviz (finvizfinance library)

**Role:** Stock discovery and screening only. Data is transient — never stored.

**What's fetched:** Overview screener results (Ticker, Company, Sector, Industry, Market Cap, P/E, Price).

**5 filter presets:**

| Preset | Key Filters |
|--------|-------------|
| `quality` | Large-cap, ROE >15%, EPS growth >0%, current ratio >1, operating margin >15% |
| `quality_mega` | Mega-cap (>$200B), ROE >15%, operating margin >20% |
| `growth_value` | Mid+, ROE >15%, EPS growth >10%, P/E <25 |
| `high_roe` | Mid+, ROE >30%, EPS growth >0% |
| `fcf_machines` | Mid+, ROE >15%, operating margin >20%, current ratio >1.5 |

**Commands:** `screen` (single preset), `discover` (all presets, ranks by conviction = presets matched).

### yfinance

**Role:** All financial data — prices, fundamentals, macro indicators.

**Per ticker** (`get_financial_data()`):
- `ticker.info` — ~150 keys: marketCap, currentPrice, trailingPE, returnOnEquity, debtToEquity, freeCashflow, dividendYield, etc.
- `ticker.income_stmt` — 4 years of annual income statements
- `ticker.balance_sheet` — 4 years of annual balance sheets
- `ticker.cash_flow` — 4 years of annual cash flow statements

**For technicals:** `ticker.history(period="1y")` — 1 year daily OHLCV

**For macro:** 1 year of daily closes for 12 indicators (see Section 4)

---

## 2. Fundamental Scoring (7 Scorers → 0–100 Composite)

Each scorer consumes the raw yfinance data and produces a 0–100 sub-score. The fundamental composite is a weighted average.

### What's Fetched vs Calculated

| Scorer | Raw Data (from yfinance) | Calculated |
|--------|--------------------------|------------|
| **EPS** | `Net Income`, `Diluted Avg Shares` from income stmt | EPS per year, CAGR, consistency ratio → `eps_score` |
| **Revenue** | `Total Revenue` from income stmt | Revenue per year (in $B), CAGR, growth trend → `revenue_score` |
| **ROE** | `returnOnEquity`, `debtToEquity` from info; `Net Income / Stockholders Equity` from statements | ROE %, historical consistency, debt reasonableness → `roe_score` |
| **FCF** | `Free Cash Flow` (or `Operating CF + CapEx`) from cash flow stmt; `freeCashflow` from info | FCF per year ($B), yield, positive streak, growth → `fcf_score` |
| **Balance** | `Current Assets/Liabilities`, `Cash`, `Total Debt`, `Retained Earnings`, `Goodwill`, `Total Assets` from balance sheet | Current ratio, cash/debt, RE trend, goodwill % → `balance_score` |
| **Dividend** | `dividendRate`, `payoutRatio` from info; `Cash Dividends Paid` from cash flow | Yield, payout sustainability, consecutive increases → `dividend_score` |
| **DCF** | `sharesOutstanding` from info, FCF from FCF scorer | Intrinsic value, margin of safety, undervalued flag (not a sub-score) |

### Scoring Details

| Scorer | Points Breakdown |
|--------|-----------------|
| EPS | 50 pts consistency + 50 pts CAGR magnitude |
| Revenue | 40 pts consistency + 40 pts CAGR + 20 pts growth bonus |
| ROE | 50 pts ROE level + 25 pts low debt + 25 pts historical |
| FCF | 30 pts positive + 25 pts streak + 25 pts growing + 20 pts yield |
| Balance | 25 pts each: current ratio, cash/debt, retained earnings, low goodwill |
| Dividend | Growth-friendly: no dividend = 50 (neutral). With dividend: sustainability + yield + growth + FCF coverage |

---

## 3. Technical Analysis (5 Indicators → 0–100)

**Data:** 1 year daily close prices from yfinance.

All indicators are **calculated**, not fetched.

| Indicator | Method | Weight | Entry Signal |
|-----------|--------|--------|--------------|
| RSI(14) | Exponential avg of gains/losses | 25 pts | <30 = oversold |
| Price vs SMA(200) | Simple 200-day moving average | 25 pts | Below = opportunity |
| Bollinger(20,2) | 20-day mean ± 2 std dev | 20 pts | At lower band |
| 52-week position | (price − low) / (high − low) | 15 pts | Near low |
| MACD(12,26,9) | Fast/slow EMA diff + signal | 15 pts | Bullish crossover |

Higher tech score = better buying opportunity (contrarian: weakness = opportunity).

---

## 4. Macro Analysis (12 Indicators → 0–100)

**Data:** 1 year daily closes from yfinance for these tickers:

| Ticker | Label | Category |
|--------|-------|----------|
| `^GSPC` | S&P 500 | US equity |
| `^STOXX` | STOXX 600 | Europe |
| `^N225` | Nikkei 225 | Asia |
| `EEM` | MSCI EM ETF | Emerging |
| `^VIX` | VIX | Volatility |
| `^TNX` | 10Y Treasury | Rates |
| `2YY=F` | 2Y Treasury | Rates |
| `DX-Y.NYB` | USD Index | Currency |
| `EURUSD=X` | EUR/USD | Currency |
| `GC=F` | Gold | Commodities |
| `CL=F` | Oil (WTI) | Commodities |
| `HG=F` | Copper | Commodities |

**Derived (calculated):** Each indicator's SMA(200), SMA(50), % vs 200-MA, 52-week position, YTD change. Also: global breadth (indices above/below 200-MA), 2Y-10Y yield spread.

| Component | Weight | Entry Signal |
|-----------|--------|--------------|
| VIX level | 25 pts | High fear = opportunity |
| S&P 500 vs 200-MA | 25 pts | Below = opportunity |
| Yield spread | 20 pts | Normal curve = healthy |
| S&P 52-week position | 15 pts | Near lows |
| 10Y yield level | 15 pts | Lower = favorable |

Higher macro score = more favorable environment for buying.

---

## 5. Verdict Engine

Combines the three layers with distinct roles:

| Layer | Role | Weight |
|-------|------|--------|
| **Fundamental** | WHAT to buy | 70% (configurable) |
| **Technical** | WHEN to buy | 20% |
| **Macro** | HOW MUCH (position sizing) | 10% |

### Zone Classification

Each score is classified: ≥70 = 🟢 Strong, 40–69 = 🟡 Neutral, <40 = 🔴 Weak

**Convergence:** Two scores converge when both ≥ 60. Three pairs checked: F+T, F+M, T+M.

### Verdict Rules

| Condition | Verdict | Position Range |
|-----------|---------|----------------|
| 3 greens, 3 convergences | STRONG BUY | 100–125% |
| 2 greens, ≥1 convergence | BUY | 75–100% |
| 1 green, 0 reds | ACCUMULATE | 50–75% |
| 0 greens, 0 reds | NEUTRAL | 25–50% |
| 1 red + 2 greens | WATCH | 0–25% |
| 1 red | HOLD | 0% |
| 2+ reds | AVOID | 0% |

**Veto:** Any score <25 caps verdict at WATCH.

**Macro multiplier:** ≥70 → ×1.25, 40–69 → ×1.0, <40 → ×0.5

---

## 6. What's Stored in the Database

All tables live in `scores.db` (SQLite).

### Table 1: `scores` — Analysis Results

**Primary key:** `(symbol, scan_date)` — one row per ticker per day.

Written by: `analyze`, `verdict`, `portfolio` commands.

| Column | Source | Fetched/Calculated |
|--------|--------|--------------------|
| `symbol`, `scan_date` | — | identity |
| `name`, `sector`, `industry` | yfinance info | fetched |
| `market_cap_b`, `current_price`, `trailing_pe` | yfinance info | fetched |
| `eps_score`, `eps_cagr`, `eps_consistent` | EPS scorer | calculated |
| `roe_score`, `roe_pct`, `debt_to_equity` | ROE scorer | calculated (ROE score) / fetched (raw values) |
| `fcf_score`, `fcf_current_b`, `fcf_yield`, `fcf_growing` | FCF scorer | calculated |
| `balance_score`, `current_ratio`, `cash_to_debt`, `retained_earnings_growing`, `goodwill_pct` | Balance scorer | calculated |
| `dividend_score`, `dividend_yield_pct`, `payout_ratio_pct`, `consecutive_div_increases` | Dividend scorer | calculated |
| `intrinsic_value`, `margin_of_safety`, `undervalued` | DCF | calculated |
| `revenue_cagr`, `revenue_growing`, `revenue_score` | Revenue scorer | calculated |
| `tech_score`, `rsi_14`, `price_vs_sma200_pct` | Technical analysis | calculated |
| `fundamental_score` | Weighted composite | calculated |

**Note:** Macro score is NOT stored here — computed live each time.

### Table 2: `fundamental_snapshots` — Point-in-Time Fundamentals

**Primary key:** `(symbol, snapshot_date)`. Auto-populated on every analyze run.

Stores 16 key metrics from yfinance info at the time of analysis + full `info_json` blob: `market_cap`, `trailing_pe`, `forward_pe`, `price_to_book`, `price_to_sales`, `roe_pct`, `debt_to_equity`, `current_ratio`, `profit_margin`, `revenue_growth`, `earnings_growth`, `fcf_yield`, `dividend_yield`, `payout_ratio`, `beta`, `current_price`.

### Table 3: `quarterly_financials` — Financial Statements

**Primary key:** `(symbol, period_end, statement_type)`.

Stores quarterly income, balance sheet, and cash flow statements as JSON. Populated on analyze (auto-snapshot) or via `collect --backfill`.

### Table 4: `price_cache` — Daily OHLCV

**Primary key:** `(symbol, trade_date)`. Append-only.

Columns: `open`, `high`, `low`, `close`, `volume`, `dividends`.

### Table 5: `macro_cache` — Macro Daily Closes

**Primary key:** `(indicator, trade_date)`. Append-only.

Stores daily close prices for all 12 macro indicators.

---

## 7. Machine Learning

### Collect → Store → Study

```
  Regular Usage              Passive Collection         Active Collection
┌──────────────┐          ┌──────────────────┐       ┌───────────────────┐
│ analyze AAPL │───auto──▶│ fundamental_     │       │ collect AAPL MSFT │
│ verdict AAPL │ snapshot │ snapshots        │       │   --backfill      │
│ portfolio    │          │ quarterly_       │       │                   │
└──────────────┘          │ financials       │       │ collect --macro   │
                          └────────┬─────────┘       └─────────┬─────────┘
                                   │                           │
                                   ▼                           ▼
                          ┌──────────────────────────────────────┐
                          │          scores.db (all 5 tables)    │
                          └──────────────────┬───────────────────┘
                                             │
                                             ▼
                                    ┌────────────────┐
                                    │  study --quick  │
                                    │  study --full   │
                                    └────────┬───────┘
                                             │
                                    Random Forest model
                                    Feature importance
                                    Optimal layer weights
```

### How Study Works

1. **Universe:** 60 liquid US stocks across 6 sectors (or 15 in `--quick` mode)
2. **Evaluation points:** Every ~21 trading days (monthly), needs 252 days look-back and 126 days forward
3. **Features per evaluation point (35 total):**
   - 16 fundamental features — from datastore snapshots (point-in-time) or current yfinance (with look-ahead bias noted)
   - 9 technical features — RSI, SMA positions, Bollinger, MACD, volatility, momentum (no bias)
   - 10 macro features — VIX, yields, spreads, indices vs 200-MA, breadth (no bias)
4. **Target:** Forward returns at 1-month, 3-month, 6-month horizons
5. **Model:** RandomForestRegressor ranks which features best predict returns
6. **Output:** Feature importance by layer (Fund/Tech/Macro %), optimal weight recommendation

### Data Quality

- **Technical & macro features:** No look-ahead bias — computed from historical prices
- **Fundamental features:** Uses point-in-time snapshots when available; falls back to current data (acknowledged bias)
- **Over time:** As more snapshots accumulate from regular analyze runs + weekly collects, the look-ahead bias shrinks to zero

### Latest Results (30-ticker study)

| Layer | Feature Importance | Current Weight | Suggested Weight |
|-------|-------------------|----------------|------------------|
| Fundamental | 41.5% | 70% | 60% |
| Macro | 29.9% | 10% | 10% |
| Technical | 28.6% | 20% | 30% |

---

## 8. Command Summary

| Command | What It Does | Stores Data? |
|---------|-------------|--------------|
| `screen <preset>` | Finviz screener | No |
| `discover` | All presets, ranked by conviction | No |
| `analyze <TICKER>` | Full fundamental scoring + tech | Yes: scores + snapshots |
| `verdict <TICKER>` | Analyze + macro + verdict | Yes: scores + snapshots |
| `portfolio` | Analyze all portfolio tickers | Yes: scores + snapshots |
| `watchlist` | Show watchlist with scores | Yes: scores + snapshots |
| `compare T1 T2...` | Side-by-side comparison | Yes: scores + snapshots |
| `technical <TICKER>` | Technical analysis only | No |
| `macro` | Macro environment only | No |
| `history <TICKER>` | Historical scores from DB | No (reads only) |
| `collect [TICKERS]` | Populate datastore tables | Yes: all 4 datastore tables |
| `study` | ML feature importance analysis | Yes: caches prices/macro |
| `backtest <TICKER>` | Long-term investor simulation | No |
| `alerts` | Check alert conditions | No |
