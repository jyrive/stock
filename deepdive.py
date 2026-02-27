#!/usr/bin/env python3
"""
Deep Dive Guide — Manual Due-Diligence Checklist

Runs the Buffett analysis on a single stock and prints a tailored
checklist of what to research manually, based on the actual numbers.

Usage:
    python deepdive.py AAPL
    python deepdive.py MSFT
"""

import sys
import warnings

from screener import (
    get_financial_data,
    analyze_eps_growth,
    analyze_roe,
    analyze_free_cash_flow,
    analyze_balance_sheet,
    calculate_dcf_intrinsic_value,
)
from screener.db import save_scores

warnings.filterwarnings("ignore")

# ── Symbols ──────────────────────────────────────────────────────────
OK = "✅"
WARN = "⚠️"
FAIL = "❌"
ARROW = "→"
BULLET = "•"
LINE = "─" * 72


def _run_analysis(ticker):
    """Run full analysis on one ticker, return result dict."""
    print(f"\n  Fetching data for {ticker}...")
    data = get_financial_data(ticker)
    if data is None:
        print(f"\n  Could not fetch data for {ticker}. Check the ticker symbol.\n")
        sys.exit(1)

    eps = analyze_eps_growth(data)
    roe = analyze_roe(data)
    fcf = analyze_free_cash_flow(data)
    bal = analyze_balance_sheet(data)
    dcf = calculate_dcf_intrinsic_value(data, fcf)

    total_score = (
        eps["eps_score"] * 0.20
        + roe["roe_score"] * 0.20
        + fcf["fcf_score"] * 0.25
        + bal["balance_score"] * 0.15
        + (25 if dcf["undervalued"] else 0) * 0.20
    )

    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "sector": data["sector"],
        "industry": data["industry"],
        "market_cap_b": round(data["market_cap"] / 1e9, 1) if data["market_cap"] else None,
        "current_price": data["current_price"],
        "trailing_pe": data["trailing_pe"],
        "eps_analysis": eps,
        "roe_analysis": roe,
        "fcf_analysis": fcf,
        "balance_analysis": bal,
        "dcf_analysis": dcf,
        "buffett_score": round(total_score, 1),
    }


def _section(title):
    print(f"\n{LINE}")
    print(f"  {title}")
    print(LINE)


def _check(status, text):
    print(f"  {status}  {text}")


def _action(text):
    print(f"       {ARROW} {text}")


def _todo(text):
    print(f"     {BULLET} {text}")


def print_deep_dive(r):
    """Print the full deep-dive manual checklist."""
    sym = r["symbol"]
    name = r["name"]
    sector = r["sector"]
    industry = r["industry"]
    score = r["buffett_score"]
    price = r["current_price"]
    pe = r["trailing_pe"]
    mcap = r["market_cap_b"]

    eps = r["eps_analysis"]
    roe = r["roe_analysis"]
    fcf = r["fcf_analysis"]
    bal = r["balance_analysis"]
    dcf = r["dcf_analysis"]

    # ── Header ───────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print(f"  DEEP DIVE GUIDE: {sym} — {name}")
    print(f"  Sector: {sector} | Industry: {industry}")
    pe_str = f"{pe:.1f}" if pe else "N/A"
    print(f"  Price: ${price:.2f} | P/E: {pe_str} | "
          f"Market Cap: ${mcap}B | Buffett Score: {score}/100")
    print(f"{'=' * 72}")

    # ── 1. Do You Understand This Business? ──────────────────────
    _section("1. DO YOU UNDERSTAND THIS BUSINESS?")
    print()
    print(f"  This tool CANNOT answer this — only you can.")
    print()
    _todo(f"Can you explain how {name} makes money in one sentence?")
    _todo(f"Do you understand {industry} well enough to predict")
    _todo(f"  what this company looks like in 10 years?")
    _todo(f"If you can't answer YES to both, stop here. Move on.")

    # ── 2. Competitive Advantage (Moat) ──────────────────────────
    _section("2. COMPETITIVE ADVANTAGE (MOAT)")
    roe_val = roe.get("roe")
    de_val = roe.get("debt_to_equity")

    if roe_val and roe_val > 20:
        _check(OK, f"ROE is {roe_val:.1f}% — high returns suggest a moat exists")
    elif roe_val and roe_val > 15:
        _check(WARN, f"ROE is {roe_val:.1f}% — decent but not exceptional")
    else:
        _check(FAIL, f"ROE is {roe_val:.1f}% — low returns, likely no moat" if roe_val else "ROE not available")

    print()
    print(f"  The numbers hint at a moat, but you MUST identify the SOURCE:")
    print()
    _todo(f"What stops a competitor from taking {name}'s customers?")
    _todo("Identify which moat type applies:")
    print(f"       - Brand power (e.g. Coca-Cola, Apple)")
    print(f"       - Switching costs (e.g. Salesforce, Oracle)")
    print(f"       - Network effects (e.g. Visa, Meta)")
    print(f"       - Cost advantage (e.g. Costco, Geico)")
    print(f"       - Patents/regulation (e.g. pharma, utilities)")
    _todo("If you cannot name a specific moat source, be cautious.")

    # ── 3. Earnings Quality ──────────────────────────────────────
    _section("3. EARNINGS QUALITY")
    eps_score = eps["eps_score"]
    eps_cagr = eps.get("eps_growth_rate")
    eps_consistent = eps.get("eps_consistent")
    eps_values = eps.get("eps_values", [])

    if eps_score >= 70:
        _check(OK, f"EPS Score: {eps_score}/100 — strong earnings growth")
    elif eps_score >= 40:
        _check(WARN, f"EPS Score: {eps_score}/100 — moderate earnings")
    else:
        _check(FAIL, f"EPS Score: {eps_score}/100 — weak or erratic earnings")

    if eps_values:
        eps_str = ", ".join([f"{y}: ${v}" for y, v in eps_values])
        print(f"  EPS history: {eps_str}")
    if eps_cagr:
        print(f"  EPS CAGR: {eps_cagr:.1f}%")

    print()
    if not eps_consistent:
        _todo(f"EPS is NOT consistently growing. Find out WHY:")
        _todo(f"  Was it a one-time event (restructuring, write-off)?")
        _todo(f"  Or is this business fundamentally cyclical?")
        _todo(f"  Buffett avoids cyclical, unpredictable businesses.")
    else:
        _todo(f"Earnings look consistent. Now verify the QUALITY:")

    _todo(f"Read the latest 10-K filing (SEC.gov {ARROW} search '{sym}')")
    _todo(f"Check: is revenue also growing, or just EPS from buybacks?")
    _todo(f"Look for non-recurring items that inflate/deflate earnings")

    # ── 4. Balance Sheet Strength ────────────────────────────────
    _section("4. BALANCE SHEET STRENGTH")
    bal_score = bal.get("balance_score", 0)
    cr = bal.get("current_ratio")
    cd = bal.get("cash_to_debt")
    re_growing = bal.get("retained_earnings_growing")
    gw = bal.get("goodwill_pct")
    re_values = bal.get("retained_earnings_values", [])

    if bal_score >= 70:
        _check(OK, f"Balance Sheet Score: {bal_score}/100 — fortress balance sheet")
    elif bal_score >= 40:
        _check(WARN, f"Balance Sheet Score: {bal_score}/100 — some concerns")
    else:
        _check(FAIL, f"Balance Sheet Score: {bal_score}/100 — serious weaknesses")

    print()

    # Current Ratio
    if cr is not None:
        if cr >= 1.5:
            _check(OK, f"Current Ratio: {cr:.2f} — can pay short-term bills")
        elif cr >= 1.0:
            _check(WARN, f"Current Ratio: {cr:.2f} — tight liquidity")
            _action("Check if this is normal for {industry}")
        else:
            _check(FAIL, f"Current Ratio: {cr:.2f} — liquidity risk")
            _action(f"Find out how {name} funds short-term obligations")
    else:
        _check(WARN, "Current Ratio: not available")

    # Cash / Debt
    if cd is not None:
        if cd >= 1.0:
            _check(OK, f"Cash/Debt: {cd:.2f} — can cover all debt with cash")
        elif cd >= 0.5:
            _check(WARN, f"Cash/Debt: {cd:.2f} — moderate debt cushion")
        else:
            _check(FAIL, f"Cash/Debt: {cd:.2f} — heavily leveraged")
            _action("Check when major debt matures (10-K debt schedule)")
            _action("Can the company refinance at reasonable rates?")
    else:
        _check(WARN, "Cash/Debt: not available")

    # Retained Earnings
    if re_growing is True:
        _check(OK, "Retained Earnings: growing — compounding reinvestment")
    elif re_growing is False:
        _check(FAIL, "Retained Earnings: declining")
        _action("Check if this is from buybacks (OK) or losses (bad)")
        if re_values:
            re_str = ", ".join([f"{y}: ${v}B" for y, v in re_values])
            print(f"       Trend: {re_str}")
    else:
        _check(WARN, "Retained Earnings: not available")

    # Goodwill
    if gw is not None:
        if gw < 10:
            _check(OK, f"Goodwill: {gw:.1f}% of assets — minimal acquisition risk")
        elif gw < 20:
            _check(WARN, f"Goodwill: {gw:.1f}% of assets — some acquisition exposure")
            _action("Check if past acquisitions are performing well")
        elif gw < 30:
            _check(WARN, f"Goodwill: {gw:.1f}% of assets — significant acquisition exposure")
            _action("Is there risk of a goodwill write-down?")
            _action("Read management's discussion of acquisition performance")
        else:
            _check(FAIL, f"Goodwill: {gw:.1f}% of assets — heavy acquisition risk")
            _action("HIGH PRIORITY: check for impairment risk")
            _action("Has management written down goodwill before?")
    else:
        _check(OK, "No significant goodwill on balance sheet")

    print()
    _todo("Manual checks you should do:")
    _todo(f"  Open the latest 10-K balance sheet for {sym}")
    _todo("  Look at inventory levels — growing faster than revenue = red flag")
    _todo("  Look at accounts receivable — growing faster than revenue = collection issues")
    _todo("  Check off-balance-sheet items (operating leases, guarantees)")

    # ── 5. Cash Flow ─────────────────────────────────────────────
    _section("5. FREE CASH FLOW")
    fcf_score = fcf["fcf_score"]
    fcf_current = fcf.get("fcf_current")
    fcf_yield = fcf.get("fcf_yield")
    fcf_growing = fcf.get("fcf_growing")
    fcf_values = fcf.get("fcf_values", [])

    if fcf_score >= 70:
        _check(OK, f"FCF Score: {fcf_score}/100 — strong cash generation")
    elif fcf_score >= 40:
        _check(WARN, f"FCF Score: {fcf_score}/100 — moderate cash flow")
    else:
        _check(FAIL, f"FCF Score: {fcf_score}/100 — weak cash flow")

    if fcf_values:
        fcf_str = ", ".join([f"{y}: ${v}B" for y, v in fcf_values])
        print(f"  FCF history: {fcf_str}")
    if fcf_current:
        print(f"  Current FCF: ${fcf_current}B | FCF Yield: {fcf_yield}%")

    print()
    if not fcf_growing:
        _todo("FCF is NOT growing. Investigate:")
        _todo("  Is capex increasing (investing for growth)? That may be OK.")
        _todo("  Or is the core business generating less cash? That's bad.")
    _todo(f"Check how {name} uses its cash (10-K / earnings call):")
    _todo("  Buybacks? Dividends? Acquisitions? Debt repayment?")
    _todo("  Buffett prefers companies that reinvest at high returns")

    # ── 6. Valuation ─────────────────────────────────────────────
    _section("6. VALUATION")
    iv = dcf.get("intrinsic_value")
    mos = dcf.get("margin_of_safety")
    uv = dcf.get("undervalued")

    if iv:
        if uv:
            _check(OK, f"DCF Intrinsic Value: ${iv:.2f} vs Price: ${price:.2f}")
            _check(OK, f"Margin of Safety: {mos:.1f}% — priced below fair value")
        else:
            _check(FAIL, f"DCF Intrinsic Value: ${iv:.2f} vs Price: ${price:.2f}")
            _check(FAIL, f"Margin of Safety: {mos:.1f}% — NO margin of safety")
    else:
        _check(WARN, "Could not calculate DCF intrinsic value")

    if pe:
        if pe < 15:
            _check(OK, f"P/E: {pe:.1f} — cheap relative to market")
        elif pe < 25:
            _check(WARN, f"P/E: {pe:.1f} — market-range valuation")
        else:
            _check(FAIL, f"P/E: {pe:.1f} — expensive")
    else:
        _check(WARN, "P/E: not available")

    print()
    _todo("Our DCF model uses conservative assumptions (8% growth, 10% discount).")
    _todo("  Do YOUR OWN valuation check:")
    _todo(f"  What growth rate is realistic for {name} over 10 years?")
    _todo(f"  At current price ${price:.2f}, what growth is the market pricing in?")
    _todo(f"  Would you be comfortable buying at this price if the market")
    _todo(f"  closed for 5 years and you couldn't sell?")
    if not uv:
        _todo(f"  Consider: what price WOULD give you margin of safety?")
        if iv:
            buy_price = iv * 0.85
            _todo(f"  For 15% margin: target buy price ≈ ${buy_price:.2f}")

    # ── 7. Management ────────────────────────────────────────────
    _section("7. MANAGEMENT QUALITY")
    print()
    print("  This tool has NO data on management. You MUST check this yourself.")
    print()
    _todo(f"Who is the CEO of {name}? How long have they been in charge?")
    _todo("Read the CEO's shareholder letters (annual reports)")
    _todo("Check insider ownership — do executives own significant stock?")
    _todo("  (Look up on OpenInsider.com or SEC Form 4 filings)")
    _todo("Look at capital allocation history:")
    _todo("  Did they make smart acquisitions or overpay?")
    _todo("  Are buybacks done at reasonable prices or at any price?")
    _todo("Are executive compensation packages aligned with shareholders?")
    _todo("Is there a founder/owner-operator still involved?")

    # ── 8. Risks ─────────────────────────────────────────────────
    _section("8. RISKS TO INVESTIGATE")
    print()
    print("  Every company has risks. You need to find them BEFORE buying.")
    print()
    _todo(f"Read the 'Risk Factors' section of {sym}'s 10-K filing")
    _todo(f"Search news for '{name} lawsuit' or '{name} regulatory'")
    _todo("Check for customer concentration — does one customer = big % of revenue?")
    _todo("Check for supplier concentration — single-source dependencies?")
    _todo(f"Is {industry} being disrupted by technology or regulation?")
    _todo("Is there geopolitical risk (e.g. China exposure, tariffs)?")

    # Tailored warnings based on data
    warnings_found = False
    if de_val and de_val > 150:
        _check(FAIL, f"HIGH DEBT: D/E is {de_val:.0f} — investigate debt sustainability")
        warnings_found = True
    if cr and cr < 1.0:
        _check(FAIL, f"LIQUIDITY RISK: Current ratio {cr:.2f} is below 1.0")
        warnings_found = True
    if gw and gw >= 30:
        _check(FAIL, f"GOODWILL: {gw:.1f}% of assets — impairment write-down risk")
        warnings_found = True
    if not eps_consistent:
        _check(WARN, "ERRATIC EARNINGS: this business may be cyclical or unstable")
        warnings_found = True
    if pe and pe > 40:
        _check(WARN, f"EXPENSIVE: P/E of {pe:.1f} means market expects a lot of growth")
        warnings_found = True
    if not warnings_found:
        print(f"  No major red flags detected in the numbers — but read the 10-K!")

    # ── 9. Summary Verdict ───────────────────────────────────────
    _section("9. YOUR DECISION CHECKLIST")
    print()
    print("  Before buying, you should be able to answer YES to ALL of these:")
    print()

    checks = [
        "I understand how this company makes money",
        "I can identify a specific competitive advantage (moat)",
        "I have read the latest 10-K annual report",
        "I understand and accept the key risks",
        "I believe management is honest and competent",
        "The price offers a margin of safety",
        "I would be happy holding this stock for 10+ years",
        "If the stock dropped 50% tomorrow, I would buy MORE, not sell",
    ]

    for i, check in enumerate(checks, 1):
        print(f"  [ ]  {i}. {check}")

    print()
    print(f"  If you can't check ALL boxes, this is not a Buffett-style buy.")
    print()

    # ── 10. Where to Research ────────────────────────────────────
    _section("10. WHERE TO DO THIS RESEARCH")
    print()

    sym_lower = sym.lower()
    _todo(f"SEC filings: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={sym}&type=10-K")
    _todo(f"Earnings calls: https://seekingalpha.com/symbol/{sym}/earnings/transcripts")
    _todo(f"Insider trading: https://openinsider.com/screener?s={sym}")
    _todo(f"Analyst estimates: https://finance.yahoo.com/quote/{sym}/analysis")
    _todo(f"News: https://finance.yahoo.com/quote/{sym}/news")
    _todo(f"Industry data: search '{industry} market size trends'")
    print()

    print(f"  {'─' * 60}")
    print(f"  Bing Finance — {sym}")
    print(f"  {'─' * 60}")
    bing_base = f"https://www.bing.com/entitydetails?q={sym_lower}&wt=FinanceGenericL3TabModule&ocid=ansMSNMoney11"
    _todo(f"Overview:         {bing_base}&l3=L3_Overview")
    _todo(f"Financials:       {bing_base}&l3=L3_Financials")
    _todo(f"Income Statement: {bing_base}&l3=L3_IncomeStatement")
    _todo(f"Balance Sheet:    {bing_base}&l3=L3_BalanceSheet")
    _todo(f"Cash Flow:        {bing_base}&l3=L3_CashFlow")
    _todo(f"Analysis:         {bing_base}&l3=L3_Analysis")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python deepdive.py TICKER")
        print()
        print("Example: python deepdive.py AAPL")
        print()
        print("Runs full analysis and prints a detailed checklist of what")
        print("you need to research manually before buying.")
        sys.exit(1)

    ticker = sys.argv[1].upper().strip()

    result = _run_analysis(ticker)

    print_deep_dive(result)

    # Save to DB too
    saved = save_scores([result])
    print(f"  Score saved to scores.db ({saved} stock, Buffett Score: {result['buffett_score']})")
    print()


if __name__ == "__main__":
    main()
