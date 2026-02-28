"""Output formatting: print results to terminal with optional color."""

from .colors import (
    USE_COLOR, RESET, BOLD, DIM, GRAY,
    GREEN, YELLOW, RED, CYAN,
    good, warn, bad, highlight, dim,
    score_color, pct_color, uv_color, ratio_color,
)


# ── Shared column formatting ─────────────────────────────────────────

def _fmt(row):
    """Format a flat-dict row into display-ready strings."""
    def _ss(key):
        """Format a sub-score — show '-' for None."""
        v = row.get(key)
        return str(v) if v is not None else "-"

    return {
        "score": f"{row['buffett_score']:.1f}" if row.get("buffett_score") else "-",
        "eps": _ss("eps_score"),
        "roe": _ss("roe_score"),
        "fcf": _ss("fcf_score"),
        "bal": _ss("balance_score"),
        "div": _ss("dividend_score"),
        "roe_pct": f"{row['roe_pct']:.0f}%" if row.get("roe_pct") else "-",
        "de": f"{row['debt_to_equity']:.0f}" if row.get("debt_to_equity") is not None else "-",
        "cr": f"{row['current_ratio']:.1f}" if row.get("current_ratio") is not None else "-",
        "cagr": f"{row['eps_cagr']:.1f}%" if row.get("eps_cagr") else "-",
        "fcf_b": f"{row['fcf_current_b']:.1f}" if row.get("fcf_current_b") is not None else "-",
        "fcf_y": f"{row['fcf_yield']:.1f}%" if row.get("fcf_yield") else "-",
        "gw": f"{row['goodwill_pct']:.0f}%" if row.get("goodwill_pct") is not None else "-",
        "dy": f"{row['dividend_yield_pct']:.1f}%" if row.get("dividend_yield_pct") else "-",
        "po": f"{row['payout_ratio_pct']:.0f}%" if row.get("payout_ratio_pct") is not None else "-",
        "iv": f"${row['intrinsic_value']:.2f}" if row.get("intrinsic_value") else "-",
        "mos": f"{row['margin_of_safety']:.1f}%" if row.get("margin_of_safety") is not None else "-",
        "uv": "✅" if row.get("undervalued") else "❌",
        "price": f"${row['current_price']:.2f}" if row.get("current_price") else "-",
        "pe": f"{row['trailing_pe']:.1f}" if row.get("trailing_pe") else "-",
    }


def _color_fmt(row):
    """Format a flat-dict row with ANSI colors for terminal display."""
    if not USE_COLOR:
        return _fmt(row)

    score = row.get("buffett_score")
    eps_s = row.get("eps_score")
    roe_s = row.get("roe_score")
    fcf_s = row.get("fcf_score")
    bal_s = row.get("balance_score")
    div_s = row.get("dividend_score")
    mos = row.get("margin_of_safety")

    def _sub_score(val):
        if val is None: return dim("-")
        s = str(val)
        if val >= 70: return good(s)
        if val >= 40: return warn(s)
        return bad(s)

    return {
        "score": score_color(score) if score else dim("-"),
        "eps": _sub_score(eps_s),
        "roe": _sub_score(roe_s),
        "fcf": _sub_score(fcf_s),
        "bal": _sub_score(bal_s),
        "div": _sub_score(div_s),
        "roe_pct": pct_color(row.get("roe_pct"), high=15, mid=10) if row.get("roe_pct") else dim("-"),
        "de": ratio_color(row.get("debt_to_equity"), good_thresh=0, warn_thresh=0, fmt=".0f") if row.get("debt_to_equity") is not None else dim("-"),
        "cr": ratio_color(row.get("current_ratio"), good_thresh=1.5, warn_thresh=1.0) if row.get("current_ratio") is not None else dim("-"),
        "cagr": pct_color(row.get("eps_cagr"), high=10, mid=0) if row.get("eps_cagr") else dim("-"),
        "fcf_b": good(f"{row['fcf_current_b']:.1f}") if row.get("fcf_current_b") and row["fcf_current_b"] > 0 else bad(f"{row['fcf_current_b']:.1f}") if row.get("fcf_current_b") is not None else dim("-"),
        "fcf_y": pct_color(row.get("fcf_yield"), high=3, mid=1) if row.get("fcf_yield") else dim("-"),
        "gw": (good(f"{row['goodwill_pct']:.0f}%") if row["goodwill_pct"] < 10 else warn(f"{row['goodwill_pct']:.0f}%") if row["goodwill_pct"] < 30 else bad(f"{row['goodwill_pct']:.0f}%")) if row.get("goodwill_pct") is not None else dim("-"),
        "dy": pct_color(row.get("dividend_yield_pct"), high=2, mid=0.5) if row.get("dividend_yield_pct") else dim("-"),
        "po": (good(f"{row['payout_ratio_pct']:.0f}%") if row["payout_ratio_pct"] <= 60 else warn(f"{row['payout_ratio_pct']:.0f}%") if row["payout_ratio_pct"] <= 80 else bad(f"{row['payout_ratio_pct']:.0f}%")) if row.get("payout_ratio_pct") is not None else dim("-"),
        "iv": good(f"${row['intrinsic_value']:.2f}") if row.get("intrinsic_value") else dim("-"),
        "mos": (good(f"{mos:.1f}%") if mos > 15 else warn(f"{mos:.1f}%") if mos > 0 else bad(f"{mos:.1f}%")) if mos is not None else dim("-"),
        "uv": good("✅") if row.get("undervalued") else bad("❌"),
        "price": f"${row['current_price']:.2f}" if row.get("current_price") else dim("-"),
        "pe": (good(f"{row['trailing_pe']:.1f}") if row["trailing_pe"] < 15 else warn(f"{row['trailing_pe']:.1f}") if row["trailing_pe"] < 25 else bad(f"{row['trailing_pe']:.1f}")) if row.get("trailing_pe") else dim("-"),
    }


_DATA_HDR = (f"{'Score':>6}{'EPS':>5}{'ROE':>5}{'FCF':>5}{'BAL':>5}{'DIV':>5}"
             f"{'ROE%':>7}{'D/E':>7}{'CR':>6}{'CAGR':>7}{'FCF$B':>7}{'FYld':>6}{'GW%':>5}"
             f"{'DY%':>6}{'PO%':>5}"
             f"{'IV$':>10}{'MoS%':>8}{'UV':>4}{'Price':>10}{'P/E':>7}")


def _data_line(f):
    """Format data columns from a _fmt() dict."""
    return (f"{f['score']:>6}{f['eps']:>5}{f['roe']:>5}{f['fcf']:>5}{f['bal']:>5}{f['div']:>5}"
            f"{f['roe_pct']:>7}{f['de']:>7}{f['cr']:>6}{f['cagr']:>7}{f['fcf_b']:>7}{f['fcf_y']:>6}{f['gw']:>5}"
            f"{f['dy']:>6}{f['po']:>5}"
            f"{f['iv']:>10}{f['mos']:>8}{f['uv']:>4}{f['price']:>10}{f['pe']:>7}")


def _data_line_color(f):
    """Format data columns with ANSI colors — fixed-width padding accounts for escape codes."""
    def _pad(colored_str, width):
        """Right-align a potentially colored string to a visual width."""
        # Strip ANSI codes to get visible length
        import re
        visible = re.sub(r'\033\[[0-9;]*m', '', colored_str)
        pad_needed = width - len(visible)
        return " " * max(0, pad_needed) + colored_str

    return (_pad(f['score'], 6) + _pad(f['eps'], 5) + _pad(f['roe'], 5) +
            _pad(f['fcf'], 5) + _pad(f['bal'], 5) + _pad(f['div'], 5) +
            _pad(f['roe_pct'], 7) + _pad(f['de'], 7) + _pad(f['cr'], 6) +
            _pad(f['cagr'], 7) + _pad(f['fcf_b'], 7) + _pad(f['fcf_y'], 6) +
            _pad(f['gw'], 5) + _pad(f['dy'], 6) + _pad(f['po'], 5) +
            _pad(f['iv'], 10) + _pad(f['mos'], 8) + _pad(f['uv'], 4) +
            _pad(f['price'], 10) + _pad(f['pe'], 7))


def print_legend():
    """Print the shared column legend."""
    print(f"\n  EPS/ROE/FCF/BAL/DIV = sub-scores (0-100) | D/E = Debt-to-Equity | "
          f"CR = Current Ratio")
    print(f"  FCF$B = FCF in billions | FYld = FCF Yield | GW% = Goodwill % of Assets")
    print(f"  DY% = Dividend Yield | PO% = Payout Ratio")
    print(f"  IV$ = DCF Intrinsic Value | MoS% = Margin of Safety")
    print(f"  UV = Undervalued (IV > Price × 1.15) | CAGR = EPS growth rate")
    print()


def flatten_result(r):
    """Convert nested screener result to flat DB-style dict for shared table."""
    return {
        "symbol": r["symbol"],
        "name": r["name"],
        "sector": r.get("sector"),
        "industry": r.get("industry"),
        "market_cap_b": r.get("market_cap_b"),
        "current_price": r.get("current_price"),
        "trailing_pe": r.get("trailing_pe"),
        "buffett_score": r.get("buffett_score"),
        "eps_score": r["eps_analysis"]["eps_score"],
        "eps_cagr": r["eps_analysis"].get("eps_growth_rate"),
        "roe_score": r["roe_analysis"]["roe_score"],
        "roe_pct": r["roe_analysis"].get("roe"),
        "debt_to_equity": r["roe_analysis"].get("debt_to_equity"),
        "fcf_score": r["fcf_analysis"]["fcf_score"],
        "fcf_current_b": r["fcf_analysis"].get("fcf_current"),
        "fcf_yield": r["fcf_analysis"].get("fcf_yield"),
        "balance_score": r["balance_analysis"]["balance_score"],
        "current_ratio": r["balance_analysis"].get("current_ratio"),
        "goodwill_pct": r["balance_analysis"].get("goodwill_pct"),
        "dividend_score": r["dividend_analysis"]["dividend_score"],
        "dividend_yield_pct": r["dividend_analysis"].get("dividend_yield_pct"),
        "payout_ratio_pct": r["dividend_analysis"].get("payout_ratio_pct"),
        "consecutive_div_increases": r["dividend_analysis"].get("consecutive_increases"),
        "intrinsic_value": r["dcf_analysis"].get("intrinsic_value"),
        "margin_of_safety": r["dcf_analysis"].get("margin_of_safety"),
        "undervalued": r["dcf_analysis"].get("undervalued"),
    }


def print_summary_table(scores, title="Scores"):
    """Print a ranked table of scores. Used by both screener and history viewer."""
    if not scores:
        print("  No scores found.\n")
        return

    hdr = "=" * 80
    print(f"\n{hdr}")
    print(f"  {title}")
    print(hdr)

    print(f"  {'#':<5}{'Symbol':<8}{'Name':<28}{_DATA_HDR}")
    print(f"  {'─' * 145}")

    for i, s in enumerate(scores, 1):
        name = (s.get("name") or "?")[:26]
        if USE_COLOR:
            f = _color_fmt(s)
            print(f"  {i:<5}{s['symbol']:<8}{name:<28}{_data_line_color(f)}")
        else:
            f = _fmt(s)
            print(f"  {i:<5}{s['symbol']:<8}{name:<28}{_data_line(f)}")

    print_legend()


def print_results(results, top_n=20):
    """Print ranked results with detailed breakdowns."""
    top = results[:top_n]

    print("\n" + "=" * 80)
    print("TOP COMPANIES - BUFFETT CRITERIA RANKING")
    print("=" * 80)

    for i, r in enumerate(top, 1):
        print(f"\n{'─' * 70}")
        print(f"  #{i}  {r['symbol']} - {r['name']}")
        print(f"{'─' * 70}")
        print(f"  Sector: {r['sector']} | Industry: {r['industry']}")
        print(f"  Market Cap: ${r['market_cap_b']}B | Price: ${r['current_price']}")
        score_str = score_color(r['buffett_score']) if USE_COLOR else f"{r['buffett_score']}"
        print(f"  Buffett Score: {score_str}/100")

        # EPS
        eps = r["eps_analysis"]
        print(f"\n  📈 EPS GROWTH (Score: {eps['eps_score']}/100)")
        if eps["eps_values"]:
            eps_str = " → ".join([f"{y}: ${v}" for y, v in eps["eps_values"]])
            print(f"     EPS History: {eps_str}")
        print(
            f"     CAGR: {eps['eps_growth_rate']}% | "
            f"Consistent: {'✅' if eps['eps_consistent'] else '❌'}"
        )

        # ROE
        roe = r["roe_analysis"]
        print(f"\n  💰 ROE & DEBT (Score: {roe['roe_score']}/100)")
        print(
            f"     Current ROE: {roe['roe']}% | Target >15%: "
            f"{'✅' if roe['roe_high'] else '❌'}"
        )
        print(
            f"     Debt/Equity: {roe['debt_to_equity']} | Reasonable: "
            f"{'✅' if roe['debt_reasonable'] else '❌'}"
        )
        if roe["roe_values"]:
            roe_str = " → ".join([f"{y}: {v}%" for y, v in roe["roe_values"]])
            print(f"     ROE History: {roe_str}")

        # FCF
        fcf = r["fcf_analysis"]
        print(f"\n  💵 FREE CASH FLOW (Score: {fcf['fcf_score']}/100)")
        if fcf["fcf_values"]:
            fcf_str = " → ".join([f"{y}: ${v}B" for y, v in fcf["fcf_values"]])
            print(f"     FCF History: {fcf_str}")
        print(
            f"     Current FCF: ${fcf['fcf_current']}B | FCF Yield: {fcf['fcf_yield']}%"
        )
        print(
            f"     Positive Streak: {fcf['fcf_positive_streak']} yrs | "
            f"Growing: {'✅' if fcf['fcf_growing'] else '❌'}"
        )

        # Balance Sheet
        bal = r.get("balance_analysis", {})
        print(f"\n  🏦 BALANCE SHEET HEALTH (Score: {bal.get('balance_score', 0)}/100)")
        cr = bal.get("current_ratio")
        cd = bal.get("cash_to_debt")
        gw = bal.get("goodwill_pct")
        re_grow = bal.get("retained_earnings_growing")
        print(
            f"     Current Ratio: {cr if cr else 'N/A'}"
            f" {'✅' if cr and cr >= 1.5 else '⚠️' if cr and cr >= 1.0 else '❌' if cr else ''}"
            f" | Cash/Debt: {cd if cd else 'N/A'}"
            f" {'✅' if cd and cd >= 0.5 else '❌' if cd else ''}"
        )
        print(
            f"     Retained Earnings Growing: "
            f"{'✅' if re_grow else '❌' if re_grow is False else 'N/A'}"
            f" | Goodwill % of Assets: {f'{gw}%' if gw is not None else 'N/A'}"
            f" {'✅' if gw is not None and gw < 20 else '⚠️' if gw is not None and gw < 30 else '❌' if gw is not None else ''}"
        )

        # Dividends
        div = r.get("dividend_analysis", {})
        print(f"\n  💎 DIVIDENDS (Score: {div.get('dividend_score', 0)}/100)")
        if div.get("pays_dividend"):
            dy = div.get("dividend_yield_pct", 0)
            po = div.get("payout_ratio_pct")
            ci = div.get("consecutive_increases", 0)
            print(f"     Yield: {dy}% | Payout Ratio: {f'{po}%' if po is not None else 'N/A'}")
            print(f"     Consecutive Increases: {ci} yrs | Growing: {'✅' if div.get('dividend_growing') else '❌'}")
            if div.get("dividend_values"):
                dv_str = " → ".join([f"{y}: ${v}B" for y, v in div["dividend_values"]])
                print(f"     Dividend History: {dv_str}")
        else:
            print("     No dividend paid")

        # DCF
        dcf = r["dcf_analysis"]
        print(f"\n  🎯 INTRINSIC VALUE / DCF (Discount Rate: 10%)")
        if dcf["intrinsic_value"]:
            print(
                f"     Intrinsic Value: ${dcf['intrinsic_value']} vs "
                f"Price: ${dcf['current_price']}"
            )
            print(
                f"     Margin of Safety: {dcf['margin_of_safety']}% | "
                f"Upside: {dcf['upside_pct']}%"
            )
            print(
                f"     Undervalued (>15% margin): "
                f"{'✅' if dcf['undervalued'] else '❌'}"
            )
        else:
            print("     Could not calculate DCF")

        print()

    # Summary table — use the shared formatter
    flat = [flatten_result(r) for r in top]
    print_summary_table(flat, "SUMMARY TABLE")

