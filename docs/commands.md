# CLI Commands

All commands are available through `stock.py`:

```bash
python stock.py analyze AAPL MSFT    # deep fundamental analysis
python stock.py technical AAPL       # entry-timing signals (RSI, SMA, BB, MACD)
python stock.py macro                # global macro environment dashboard
python stock.py verdict AAPL         # triangulated verdict (Fund+Tech+Macro)
python stock.py screen high_roe      # discover candidates via Finviz
python stock.py history --movers     # browse score history
python stock.py deepdive AAPL        # due-diligence checklist
python stock.py chart AAPL MSFT      # plot score trends as PNG
python stock.py cache stats          # show cache info
python stock.py cache clear          # clear cached API responses
python stock.py config show          # show current config
python stock.py config init          # create config.yaml with defaults
python stock.py alerts               # price target & score drop alerts
python stock.py portfolio            # analyze stocks you OWN
python stock.py watchlist            # analyze stocks you're WATCHING
python stock.py discover             # scan all presets for new ideas
python stock.py compare portfolio watchlist  # side-by-side comparison
```

Single-letter aliases work too: `a` (analyze), `t` (technical), `m` (macro), `v` (verdict), `s` (screen), `h` (history), `d` (deepdive), `c` (chart), `p` (portfolio), `w` (watchlist).

If you pass tickers without a command, it defaults to `analyze`:

```bash
python stock.py AAPL MSFT GOOGL      # same as: python stock.py analyze AAPL MSFT GOOGL
```

---

## 1. Screen — Find Candidates

Scan Finviz for stocks matching quality filters. Shows candidates **not already in your `tickers.txt`**:

```bash
python stock.py screen                # default "quality" preset
python stock.py screen high_roe      # use a specific preset
python stock.py screen --list        # show available presets
```

### Presets

| Preset | Market Cap | Key Filters |
|--------|-----------|-------------|
| `quality` | Large+ | ROE >15%, EPS growth, margins >15% |
| `quality_mega` | Mega (>$200B) | ROE >15%, margins >20% |
| `growth_value` | Mid+ | ROE >15%, EPS growth >10%, P/E <25 |
| `high_roe` | Mid+ | ROE >30% |
| `fcf_machines` | Mid+ | ROE >15%, margins >20%, current ratio >1.5 |

Output includes a ready-to-paste command to analyze the new candidates.

---

## 2. Technical — Entry Timing Signals

Spot buying opportunities with technical indicators. The **Tech Score** (0–100) tells you *when* to buy — pair it with the Fundamental Score to know *what* to buy:

```bash
python stock.py technical AAPL          # single stock — detailed breakdown
python stock.py technical AAPL MSFT V   # multiple stocks — summary table
python stock.py technical portfolio     # all portfolio stocks
python stock.py technical watchlist     # all watchlist stocks
```

Indicators analyzed:

| Indicator | What It Measures | Bullish When |
|-----------|-----------------|---------------|
| **RSI(14)** | Momentum — overbought/oversold | < 30 (oversold) |
| **SMA(50/200)** | Trend direction | Price below moving averages |
| **Bollinger Bands** | Volatility & mean reversion | Near lower band |
| **MACD(12,26,9)** | Trend momentum & crossovers | Bullish crossover |
| **52-week position** | Price range context | Near 52-week low |

The **Entry Rating** combines Tech Score + Fundamental Score:

| Rating | Meaning |
|--------|--------|
| ★★★★★ HIGHEST CONVICTION | High Fundamental + high Tech — strong buy signal |
| ★★★★☆ GOOD ENTRY | Good fundamentals + favorable technical setup |
| ★★★☆☆ FAIR | Mixed signals — proceed with caution |
| ★★☆☆☆ NEUTRAL | No strong entry signal |
| ★☆☆☆☆ WAIT | Technically unfavorable — wait for better entry |

Technical data is also included in the `analyze` summary table (Tech, RSI, v200 columns) and saved to `scores.db`.

---

## 3. Macro — Global Environment Dashboard

Assess the macro-economic environment to calibrate your position sizing. The **Macro Score** (0–100) tells you *how much* to buy:

```bash
python stock.py macro              # full dashboard with all indicators
python stock.py macro --compact    # compact summary (~10 lines)
```

Indicators tracked:

| Category | Indicator | What It Tells You |
|----------|----------|-------------------|
| **US Market** | S&P 500 vs 200-MA | Market trend direction |
| **Europe** | STOXX 600 vs 200-MA | European market health |
| **Asia** | Nikkei 225 vs 200-MA | Asian market health |
| **Emerging** | MSCI EM ETF vs 200-MA | Emerging market health |
| **Volatility** | VIX (Fear Index) | High VIX = fear = opportunity |
| **Rates** | 10Y & 2Y Treasury, 2-10 spread | Rate environment, recession signal |
| **Currency** | USD Index, EUR/USD | Dollar strength |
| **Commodities** | Gold, Oil (WTI), Copper | Inflation, demand, risk-off gauge |

**Three-layer decision model:**

| Layer | Score | Question |
|-------|-------|----------|
| Fundamental Score | 0–100 | **WHAT** to buy (fundamental quality) |
| Technical Score | 0–100 | **WHEN** to buy (stock-level entry) |
| Macro Score | 0–100 | **HOW MUCH** to buy (position sizing) |

Macro score interpretation:

| Score | Stance | Position Sizing |
|-------|--------|----------------|
| ≥ 70 | Aggressive | Full positions on quality stocks |
| 50–69 | Constructive | Normal position sizes |
| 35–49 | Cautious | Half positions, average in gradually |
| < 35 | Defensive | Minimal new positions, build cash |

Macro analysis is automatically included in all workflow commands (daily one-liner, weekly compact, monthly full dashboard).

---

## 4. Verdict — Triangulated Decision Engine

Converge all three scores into a single actionable verdict — the engine uses a triangulation approach. Instead of averaging, the engine classifies each score into a zone and checks whether independent signals *agree*:

```bash
python stock.py verdict AAPL              # single stock (full card)
python stock.py verdict AAPL MSFT GOOGL   # side-by-side table
python stock.py verdict --portfolio       # all portfolio stocks
python stock.py verdict --watchlist       # all watchlist stocks
python stock.py verdict --all             # portfolio + watchlist
python stock.py v AAPL                    # alias
```

**Zone classification:**

| Zone | Score | Signal |
|------|-------|--------|
| 🟢 Strong | ≥ 70 | Favourable |
| 🟡 Neutral | 40–69 | Mixed |
| 🔴 Weak | < 40 | Unfavourable |

**Verdict matrix:**

| Zone Pattern | Verdict | Position % |
|---|---|---|
| 🟢🟢🟢 | **STRONG BUY** | 100–125% |
| 🟢🟢🟡 | **BUY** | 75–100% |
| 🟢🟡🟡 | **ACCUMULATE** | 50–75% |
| 🟡🟡🟡 | **NEUTRAL** | 25–50% |
| 🟢🟢🔴 | **WATCH** — 1 veto | 0–25% |
| 🟢🟡🔴 | **HOLD** — conflicting | 0% |
| 2+ 🔴 | **AVOID** | 0% |

**Veto rule:** if any single score < 25, the verdict is capped at WATCH regardless of the others.

**Macro multiplier:** Macro ≥ 70 → ×1.25 overweight, 40–69 → ×1.0, < 40 → ×0.5 underweight.

Verdicts are integrated into all three workflow commands (daily one-liner, weekly compact table, monthly full verdicts).

---

## 5. Analyze — Deep-Score Stocks

Run full fundamental analysis on specific tickers. Each stock gets scored on EPS, ROE, FCF, balance sheet, dividends, and DCF:

```bash
python stock.py analyze               # analyze tickers from tickers.txt
python stock.py analyze AAPL MSFT GOOGL  # analyze specific tickers
python stock.py analyze my_watchlist.txt  # analyze tickers from a custom file
python stock.py analyze AAPL --csv       # analyze and export results to CSV
python stock.py analyze AAPL --xlsx      # analyze and export to styled Excel
```

API responses are cached for 4 hours to speed up repeated runs.

If no tickers are provided, you'll get an interactive prompt.

Results are saved to `scores.db` (SQLite) with today's date. Re-running on the same day overwrites previous results.

---

## 6. Track — Browse Score History

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

---

## 7. Deep Dive — Manual Due-Diligence Checklist

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

At the end of the deep dive, a **peer comparison table** is automatically displayed showing 5 same-sector companies side-by-side with key metrics (ROE, P/E, D/E, current ratio, FCF yield, dividend yield, profit margin, revenue growth).

---

## 8. Alerts — Price Target & Score Drop Alerts

Scan your `scores.db` for actionable signals:

```bash
python stock.py alerts
```

Three alert types are generated:

| Alert | What It Flags |
|-------|---------------|
| **Bargains** | Stocks with Fundamental Score ≥55 AND margin of safety >10% |
| **Undervalued** | All stocks where margin of safety is positive (price < intrinsic value) |
| **Score Drops** | Stocks whose Fundamental Score dropped ≥10 points between scans |

Thresholds are configurable in `config.yaml` (see Configuration section below).

> **Tip:** Run `python stock.py analyze` first to populate scores, then `python stock.py alerts` to see what stands out.

---

## 9. Export — Save Results to CSV or Excel

After running `analyze`, export results to a spreadsheet:

```bash
python stock.py analyze AAPL MSFT --csv       # saves scores_YYYY-MM-DD.csv
python stock.py analyze AAPL MSFT --xlsx      # saves scores_YYYY-MM-DD.xlsx (styled)
python stock.py analyze AAPL MSFT --excel     # same as --xlsx
```

The export includes 35 columns covering all sub-scores, key metrics, revenue CAGR, DCF valuation, technical indicators, and more.

**CSV** works out of the box. **Excel** requires `openpyxl` (`pip install openpyxl`). If `openpyxl` is not installed, it falls back to CSV automatically.

The Excel output includes:
- Bold header row with colored background
- Auto-sized column widths
- Frozen top row for easy scrolling

---

## 10. Config — Customize Scoring & Thresholds

All scoring weights, DCF assumptions, and thresholds are configurable:

```bash
python stock.py config init     # create config.yaml with all defaults
python stock.py config show     # display current settings as JSON
python stock.py config path     # show config file location
```

**Step-by-step to customize:**

1. Generate the default config file:
   ```bash
   python stock.py config init
   ```

2. Open `config.yaml` in your editor. It contains all tuneable parameters with comments:
   ```yaml
   # Scoring weights (must sum to 1.0)
   weights:
     eps: 0.15
     roe: 0.15
     fcf: 0.20
     balance: 0.15
     dividend: 0.05       # growth-friendly: low weight
     dcf: 0.15
     revenue: 0.15        # rewards organic growth

   # DCF model assumptions
   dcf:
     growth_rate_high: 0.08    # FCF growth years 1-5 (range: 0.0 – 0.25)
     growth_rate_low: 0.03     # FCF growth years 6-10 (range: 0.0 – 0.15)
     terminal_growth: 0.025    # Perpetual growth (must be < discount_rate)
     discount_rate: 0.10       # Required return / WACC (range: 0.06 – 0.15)
     margin_required: 0.15     # MoS to flag "undervalued" (range: 0.0 – 0.50)

   # Alert thresholds
   alerts:
     margin_of_safety_min: 0   # MoS% above this triggers alert
     score_drop_threshold: 10  # Score drop >= this triggers alert
   ```

3. Edit the values you want to change. For example, to be more conservative:
   ```yaml
   dcf:
     discount_rate: 0.12       # higher required return
     margin_required: 0.25     # need 25% margin of safety
   ```

4. Run your analysis — it automatically picks up the config:
   ```bash
   python stock.py analyze AAPL
   ```

5. To reset to defaults, simply delete `config.yaml`:
   ```bash
   rm config.yaml
   ```

If `config.yaml` doesn't exist, all defaults are used. Partial configs work too — only override the values you want to change.

---

## 11. Revenue Growth — Organic Demand Tracking

Revenue growth is automatically tracked alongside EPS in both `analyze` and `deepdive` commands. This helps identify whether earnings growth comes from real demand or just share buybacks / cost-cutting.

In the **analyze** output, each stock shows:
- Revenue history (4 years, in billions)
- Revenue CAGR (compound annual growth rate)
- Whether revenue is growing overall

In the **deep dive**, the Earnings Quality section compares EPS CAGR vs. Revenue CAGR. If EPS is growing much faster than revenue, a warning flags potential buyback-driven growth.

> Revenue is informational — it is NOT part of the weighted fundamental score.

---

## 12. Portfolio — Manage & Analyze Stocks You Own

Track stocks you own and get alerts specific to your holdings:

```bash
python stock.py portfolio              # analyze all portfolio stocks + alerts
python stock.py portfolio list         # show current portfolio tickers
python stock.py portfolio add AAPL V   # add tickers to portfolio
python stock.py portfolio remove MSFT  # remove a ticker
python stock.py portfolio buy AAPL     # move from watchlist → portfolio
python stock.py portfolio sell MSFT    # move from portfolio → watchlist
python stock.py portfolio export       # analyze + export to CSV
```

> **Recommended frequency:** every 2–3 days (these are stocks you own).

---

## 13. Watchlist — Track Stocks You're Watching

Watch stocks you're interested in and spot buying opportunities:

```bash
python stock.py watchlist              # analyze watchlist + show buying opportunities
python stock.py watchlist list         # show current watchlist
python stock.py watchlist add MSFT V   # add tickers to watchlist
python stock.py watchlist remove META  # remove a ticker
python stock.py watchlist export       # analyze + export to CSV
```

The watchlist command highlights **buying opportunities** — stocks that are undervalued according to DCF.

> **Recommended frequency:** weekly (looking for entry points).

---

## 14. Discover — Find New Investment Ideas

Scan all Finviz presets at once, deduplicate, and rank by conviction (number of presets matched):

```bash
python stock.py discover               # scan all 5 presets
python stock.py discover --analyze     # also auto-analyze top 10 candidates
python stock.py discover quality       # scan only one preset
```

Stocks already in your portfolio or watchlist are excluded. Results are ranked by "conviction" — a stock matching 4 presets is a stronger signal than one matching 1.

> **Recommended frequency:** bi-weekly (finding new ideas).

---

## 15. Compare — Side-by-Side Comparison

Compare any two sets of stocks:

```bash
python stock.py compare portfolio watchlist       # portfolio vs watchlist
python stock.py compare AAPL,MSFT GOOGL,META      # two ticker groups
python stock.py compare portfolio other_picks.txt  # vs an external file
python stock.py compare AAPL,MSFT                  # compare against portfolio
```

Shows average scores, P/E, undervalued count, rankings side-by-side, and overlap analysis.

> **Recommended frequency:** on demand.

---

## Workflow Commands

Instead of running individual commands, use the built-in workflow commands that chain
the right operations together with compact output:

```bash
python stock.py daily       # Quick morning check (~30s)
python stock.py weekly      # Portfolio + watchlist review (~2min)
python stock.py monthly     # Full review + discover (~5min)
```

| Command | What it does | Output |
|---------|-------------|--------|
| `daily` | Macro one-liner + portfolio summary + verdicts + alerts | ~30 lines |
| `weekly` | Macro compact + portfolio + watchlist verdicts + buying opportunities + score movers | ~70 lines |
| `monthly` | Full macro dashboard + discover + full analysis + verdicts + compare + CSV export | Verbose |

**Tip:** Use `--summary` on any `analyze` command for compact output:
```bash
python stock.py analyze AAPL MSFT --summary   # summary table only, no per-stock detail
```

---

## Manual Workflow

For more control, run the individual steps:

```
 ┌──────────────────────────────────────────────────────┐
 │  1. python stock.py discover              │ ← find new candidates
 │  2. python stock.py watchlist add ACN LULU │ ← add interesting ones
 │  3. python stock.py watchlist              │ ← analyze & rank them
 │  4. python stock.py technical watchlist    │ ← check entry timing
 │  5. python stock.py deepdive LULU          │ ← manual due diligence
 │  6. python stock.py portfolio buy LULU     │ ← move to portfolio
 │  7. python stock.py portfolio              │ ← monitor your holdings
 │  8. python stock.py technical portfolio    │ ← check entry signals
 │  9. python stock.py compare portfolio watchlist │ ← compare lists
 │ 10. python stock.py history --movers       │ ← spot changes over time
 │ 11. python stock.py alerts                 │ ← check price signals
 │ 12. python stock.py portfolio export       │ ← export for sharing
 └──────────────────────────────────────────────────────┘

  Flow:  discover → watchlist → technical → research → buy → portfolio
```

---

## Ticker Management

The tool uses three ticker files, all in the project root:

| File | Purpose | Managed by |
|------|---------|------------|
| `tickers.txt` | Master list for `analyze` (default) | Edit manually |
| `portfolio.txt` | Stocks you **OWN** | `portfolio add/remove/buy/sell` |
| `watchlist.txt` | Stocks you're **WATCHING** | `watchlist add/remove` |

`portfolio.txt` and `watchlist.txt` are auto-created on first use. The `buy` command moves a stock from watchlist → portfolio; `sell` moves it the other way (keeps watching).

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
  Fundamental Score: 65.8/100

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
