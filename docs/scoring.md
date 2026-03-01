# Scoring Reference

## Fundamental Score (0–100)

Weighted sum of seven sub-scores:

| Criteria | Weight | What It Measures |
|----------|--------|------------------|
| **EPS Growth** | 15% | Consistent earnings growth over 4+ years |
| **ROE** | 15% | Return on equity >15% with reasonable debt |
| **Free Cash Flow** | 20% | Positive, growing FCF and FCF yield |
| **Balance Sheet** | 15% | Liquidity, debt coverage, retained earnings, goodwill |
| **Dividends** | 5% | Capital allocation quality — penalises unsustainable payouts, neutral for no dividend |
| **Valuation (DCF)** | 15% | Margin of safety based on discounted cash flow |
| **Revenue Growth** | 15% | Organic demand — confirms earnings growth is real |

> **Note:** The Technical Score (0–100) and Macro Score (0–100) are **separate** scores. Technical focuses on entry timing, Macro on environment/position sizing. Neither is part of the Fundamental Score — all three are combined by the `verdict` command.

---

## EPS Score (0–100)

| Component | How It's Calculated | Points |
|-----------|-------------------|--------|
| Consistency | % of years where EPS grew vs. prior year (need ≥65%) | Up to 50 |
| CAGR | Compound Annual Growth Rate (2.5 pts per 1%, capped at 20%) | Up to 50 |

---

## ROE Score (0–100)

| Component | How It's Calculated | Points |
|-----------|-------------------|--------|
| Current ROE | >30%: 50, >20%: 40, >15%: 30, >10%: 15 | Up to 50 |
| Debt/Equity | D/E <150: 25 pts, <200: 10 pts | Up to 25 |
| Consistency | ROE >15% all years: 25, >70% of years: 15 | Up to 25 |

---

## FCF Score (0–100)

| Component | How It's Calculated | Points |
|-----------|-------------------|--------|
| Positive FCF | Current year FCF > 0 | 30 |
| Positive streak | ≥4 consecutive years: 25, ≥3 years: 15 | Up to 25 |
| Growing | Most recent FCF > earliest FCF | 25 |
| FCF Yield | FCF ÷ Market Cap. >3%: 20, >2%: 10 | Up to 20 |

---

## DCF / Valuation (0 or 25)

Binary check: is the stock undervalued based on a conservative DCF model?

| Parameter | Value |
|-----------|-------|
| Years 1–5 FCF growth | 8% |
| Years 6–10 FCF growth | 3% |
| Terminal growth rate | 2.5% |
| Discount rate | 10% |

Undervalued = intrinsic value > current price × 1.15. If yes → 25 pts (× 0.15 = 3.75 pts to final score).

---

## Balance Sheet Health (0–100)

| Component | How It's Calculated | Points |
|-----------|---------------------|--------|
| Current Ratio | ≥2.0: 25, ≥1.5: 20, ≥1.0: 10 | Up to 25 |
| Cash / Debt | ≥1.0: 25, ≥0.5: 20, ≥0.25: 10 | Up to 25 |
| Retained Earnings | Growing ≥75% of years: 25, growing overall: 15 | Up to 25 |
| Goodwill % | <10%: 25, <20%: 15, <30%: 5 | Up to 25 |

---

## Dividend Score (0–100) — Growth-Friendly

Growth-friendly scoring: companies that pay **no dividend** are NOT penalised (neutral 50/100). The score primarily flags *unsustainable* payouts as a danger signal.

| Scenario | Score | Rationale |
|----------|-------|-----------|
| **No dividend** (reinvests in growth) | **50** | Neutral — not a penalty |
| Pays dividend, payout ≤40% | 80–100 | Very sustainable |
| Pays dividend, payout 40–60% | 70–95 | Sustainable |
| Pays dividend, payout 60–80% | 45–75 | Watch closely |
| Pays dividend, payout >80% | 0–40 | ⚠️ Danger signal! |

For dividend payers, the score combines: payout sustainability (40 pts), yield quality (25 pts), dividend growth (20 pts), and a base credit (15 pts).

---

## Revenue Growth (0–100) — Weighted 15%

Revenue growth is now part of the weighted Fundamental Score, rewarding companies with real organic demand growth.

| Component | How It's Calculated | Points |
|-----------|---------------------|--------|
| Consistency | Fraction of years with YoY revenue growth | Up to 40 |
| CAGR Magnitude | 2.5 pts per 1% revenue CAGR (capped) | Up to 40 |
| Overall Growth | Latest revenue > earliest | 20 |

---

## Technical Score (0–100) — Entry Timing

A separate score focused on *when* to buy. Higher = better entry opportunity.

| Component | Weight | Bullish Signal |
|-----------|--------|----------------|
| **RSI(14)** | 25 pts | < 30 oversold = 25, < 35 = 20, < 40 = 15, 40–60 neutral = 10 |
| **Price vs 200-MA** | 25 pts | Below MA = 25, near MA = 15, far above = 0 |
| **Bollinger Band %** | 20 pts | Near lower band (< 20%) = 20, mid-range = 10 |
| **52-week position** | 15 pts | Near low (< 20%) = 15, mid-range = 8, near high = 0 |
| **MACD** | 15 pts | Bullish crossover = 15, positive histogram = 10 |

The Technical Score is independent from the Fundamental Score.

---

## Macro Score (0–100) — Environment Favourability

A global macro-economic environment score for position sizing. Higher = more favourable.

| Component | Weight | Bullish Signal |
|-----------|--------|----------------|
| **VIX** | 25 pts | High VIX (> 25) = fear = opportunity |
| **S&P 500 vs 200-MA** | 25 pts | Below MA = cheaper market |
| **Yield Spread (10Y − 2Y)** | 20 pts | Normal/steep curve = healthy economy |
| **S&P 52-week position** | 15 pts | Near 52-week lows = opportunity |
| **10-Year Yield** | 15 pts | Lower rates = more equity-friendly |

Global breadth (how many of US / Europe / Asia / EM trade above their 200-MA)
provides additional context but is not scored numerically.

**Three-layer model:**
- Fundamental Score → **WHAT** to buy (fundamental quality)
- Technical Score → **WHEN** to buy (entry timing)
- Macro Score → **HOW MUCH** to buy (position sizing)

---

## Verdict — Triangulation

The `verdict` command converges all three scores. Each score is zoned (🟢 ≥ 70, 🟡 40–69, 🔴 < 40), pairwise convergence is checked (both ≥ 60), and a verdict is produced:

| Verdict | Meaning | Position |
|---------|---------|----------|
| **STRONG BUY** | 3 greens, 3 converge | 100–125% |
| **BUY** | 2 greens, 1+ converge | 75–100% |
| **ACCUMULATE** | 1 green, no reds | 50–75% |
| **NEUTRAL** | all yellow | 25–50% |
| **WATCH** | 2 greens + 1 red, or veto | 0–25% |
| **HOLD** | conflicting (green + yellow + red) | 0% |
| **AVOID** | 2+ reds | 0% |

Veto rule: any score < 25 caps verdict at WATCH. Macro ≥ 70 gives ×1.25 sizing multiplier; < 40 gives ×0.5.

---

## Table Columns

| Column | Full Name | Meaning |
|--------|-----------|---------|
| **#** | Rank | Position sorted by Score (highest first) |
| **Symbol** | Ticker | Stock ticker, e.g. AAPL |
| **Name** | Company Name | Full name (truncated to fit) |
| **Score** | Fundamental Score | Weighted score 0–100 |
| **EPS** | EPS Sub-Score | Earnings consistency + growth (0–100) |
| **ROE** | ROE Sub-Score | Return on equity + debt check (0–100) |
| **FCF** | FCF Sub-Score | Free cash flow strength (0–100) |
| **BAL** | Balance Sheet Score | Liquidity, debt coverage, retained earnings, goodwill (0–100) |
| **DIV** | Dividend Score | Capital allocation quality (0–100). 50 = no dividend (neutral) |
| **REV** | Revenue Score | Revenue growth strength (0–100). Weighted 15% |
| **ROE%** | Return on Equity | Net Income ÷ Equity × 100 |
| **D/E** | Debt-to-Equity | Total Debt ÷ Equity. <150 is reasonable |
| **CR** | Current Ratio | Current Assets ÷ Current Liabilities. >1.5 is healthy |
| **CAGR** | EPS Growth Rate | Compound Annual Growth Rate of EPS |
| **FCF$B** | FCF in Billions | Current year Free Cash Flow |
| **FYld** | FCF Yield | FCF ÷ Market Cap × 100. >3% is attractive |
| **GW%** | Goodwill % | Goodwill ÷ Total Assets × 100. <20% is healthy |
| **DY%** | Dividend Yield | Annual Dividend ÷ Price × 100 |
| **PO%** | Payout Ratio | Dividends ÷ Net Income × 100. <60% is sustainable |
| **RevCAGR** | Revenue CAGR | Compound annual growth rate of revenue |
| **RevG** | Revenue Growing | ✅ if latest revenue > earliest |
| **IV$** | Intrinsic Value | DCF-estimated fair share price |
| **MoS%** | Margin of Safety | (IV − Price) ÷ IV × 100. Positive = cheap |
| **UV** | Undervalued | ✅ if IV > Price × 1.15, otherwise ❌ |
| **Price** | Current Price | Market price at time of scan (Yahoo Finance) |
| **P/E** | Price-to-Earnings | Share price ÷ trailing EPS |
| **Tech** | Technical Score | Entry timing score 0–100 (higher = better entry) |
| **RSI** | RSI(14) | 14-day Relative Strength Index. <30 oversold, >70 overbought |
| **v200** | Price vs 200-MA | % distance from 200-day moving average. Negative = below MA |
