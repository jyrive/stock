# Buffett's Method vs. This Tool

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
