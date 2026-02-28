# How to Use This Tool

A practical guide for finding quality stocks and tracking your picks against the index.

---

## Quick Start (10 minutes)

```bash
# 1. Find candidates — scans Finviz for Buffett-style stocks
python stock.py discover

# 2. Add the best ones to your watchlist
python stock.py watchlist add ACN CPRT MNST KLAC LULU

# 3. Get verdicts — combines fundamentals + technicals + macro
python stock.py verdict watchlist

# 4. Deep-dive the top picks — a due-diligence checklist
python stock.py deepdive ACN
```

---

## What to Run and When

The tool is designed for **long-term investing**, not day trading. You don't need to check it often.

| Frequency | Command | What it does | Time |
|-----------|---------|-------------|------|
| **Weekly** (Saturday) | `python stock.py weekly` | Full review: macro, portfolio alerts, watchlist verdicts, new discoveries, score changes | ~2 min |
| **Monthly** | `python stock.py monthly` | Everything above + full analysis of all stocks + discover new candidates + CSV export | ~5 min |
| **When adding stocks** | `python stock.py discover` | Scan Finviz for new ideas | ~1 min |
| **Before buying** | `python stock.py verdict TICKER` | Final triangulated buy/wait/avoid signal | ~15 sec |
| **On demand** | `python stock.py alerts` | Check for score drops or bargains | ~5 sec |

### Suggested Routine

**Saturday morning** (5 minutes):

```bash
python stock.py weekly
```

This single command gives you everything:
- Macro environment (how aggressive to be)
- Portfolio health + alerts (anything wrong with holdings?)
- Watchlist verdicts (any buy signals?)
- New discoveries (stocks you haven't seen before)
- Score movers (what changed this week?)

**Once a month** (10 minutes):

```bash
python stock.py monthly
```

Deeper review: full per-stock breakdowns, fresh discovery scan, comparison tables.

**That's it.** Buffett checks his stocks infrequently — you should too.

---

## The Decision Framework

The tool answers three questions:

| Question | Score | Command |
|----------|-------|---------|
| **WHAT** to buy? | Buffett Score (0–100) | `analyze`, `watchlist` |
| **WHEN** to buy? | Tech Score (0–100) | `technical`, `verdict` |
| **HOW MUCH** to buy? | Macro Score (0–100) | `macro` |

The `verdict` command **combines all three** into a single recommendation:

| Verdict | Action |
|---------|--------|
| **STRONG BUY** | All three scores align — high conviction entry |
| **BUY** | Good fundamentals + favorable technicals |
| **ACCUMULATE** | Good stock, decent timing — add small position |
| **NEUTRAL** | Mixed signals — no rush |
| **WATCH** | Interesting but wait for better entry |
| **HOLD** | If you own it, keep; don't add |
| **AVOID** | Poor fundamentals or terrible timing |

---

## Step-by-Step: Finding Stocks That Beat the Index

### Step 1: Discover Candidates

```bash
python stock.py discover
```

Scans 5 Finviz presets (buffett, mega, growth_value, high_roe, fcf_machines). Stocks matching multiple presets get more ★ stars = higher conviction.

### Step 2: Research the Best Ones

```bash
# Add top picks to watchlist
python stock.py watchlist add ACN CPRT MNST

# Get full analysis
python stock.py watchlist

# Check entry timing
python stock.py verdict watchlist
```

**Look for:**
- Buffett Score > 60
- Positive Margin of Safety (stock is undervalued)
- Verdict = BUY or STRONG BUY

### Step 3: Due Diligence

Before "buying", run the deep-dive checklist:

```bash
python stock.py deepdive ACN
```

This guides you through the qualitative checks the numbers can't cover: do you understand the business? What's the moat? Is management good?

### Step 4: Paper Trade

Move your best picks to the portfolio:

```bash
python stock.py portfolio buy ACN     # moves from watchlist → portfolio
python stock.py portfolio buy CPRT
```

Track them weekly with `python stock.py weekly`.

### Step 5: Monitor

```bash
python stock.py weekly        # every Saturday
python stock.py alerts        # anytime — checks for score drops or bargains
```

**When to sell** (move back to watchlist):
```bash
python stock.py portfolio sell ACN    # if thesis breaks
```

Sell triggers to watch for:
- Buffett Score drops below 40
- Verdict changes to AVOID
- `alerts` shows significant score drop
- Your deep-dive thesis no longer holds

---

## Key Numbers to Remember

| Metric | Good | Great | Red Flag |
|--------|------|-------|----------|
| Buffett Score | > 55 | > 70 | < 35 |
| Margin of Safety | > 0% | > 20% | < -50% |
| ROE | > 15% | > 25% | < 10% |
| Debt/Equity | < 100 | < 50 | > 200 |
| EPS CAGR | > 5% | > 15% | Negative |
| FCF Yield | > 3% | > 5% | Negative |
| Tech Score | > 50 | > 70 | < 20 (wait) |
| Macro Score | > 50 | > 70 | < 30 (be cautious) |

---

## Tips

- **Don't over-trade.** Buffett holds stocks for years. Check weekly, act monthly.
- **Conviction matters.** Stocks with ★★★+ from `discover` match multiple quality filters.
- **Margin of Safety is key.** A great company at a bad price is a bad investment.
- **Use `deepdive` before every buy.** Numbers are necessary but not sufficient.
- **Compare against SPY.** Run `python stock.py compare portfolio SPY` periodically to see if you're beating the index.
- **Score history helps.** `python stock.py history AAPL` shows how a stock's quality changes over time. Rising scores = improving business.
