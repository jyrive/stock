"""Output formatting: print results to terminal."""


# ── Shared column formatting ─────────────────────────────────────────

def _fmt(row):
    """Format a flat-dict row into display-ready strings."""
    return {
        "score": f"{row['buffett_score']:.1f}" if row.get("buffett_score") else "-",
        "eps": str(row.get("eps_score", "-")),
        "roe": str(row.get("roe_score", "-")),
        "fcf": str(row.get("fcf_score", "-")),
        "bal": str(row.get("balance_score", "-")),
        "roe_pct": f"{row['roe_pct']:.0f}%" if row.get("roe_pct") else "-",
        "de": f"{row['debt_to_equity']:.0f}" if row.get("debt_to_equity") is not None else "-",
        "cr": f"{row['current_ratio']:.1f}" if row.get("current_ratio") is not None else "-",
        "cagr": f"{row['eps_cagr']:.1f}%" if row.get("eps_cagr") else "-",
        "fcf_b": f"{row['fcf_current_b']:.1f}" if row.get("fcf_current_b") is not None else "-",
        "fcf_y": f"{row['fcf_yield']:.1f}%" if row.get("fcf_yield") else "-",
        "gw": f"{row['goodwill_pct']:.0f}%" if row.get("goodwill_pct") is not None else "-",
        "iv": f"${row['intrinsic_value']:.2f}" if row.get("intrinsic_value") else "-",
        "mos": f"{row['margin_of_safety']:.1f}%" if row.get("margin_of_safety") is not None else "-",
        "uv": "✅" if row.get("undervalued") else "❌",
        "price": f"${row['current_price']:.2f}" if row.get("current_price") else "-",
        "pe": f"{row['trailing_pe']:.1f}" if row.get("trailing_pe") else "-",
    }


_DATA_HDR = (f"{'Score':>6}{'EPS':>5}{'ROE':>5}{'FCF':>5}{'BAL':>5}"
             f"{'ROE%':>7}{'D/E':>7}{'CR':>6}{'CAGR':>7}{'FCF$B':>7}{'FYld':>6}{'GW%':>5}"
             f"{'IV$':>10}{'MoS%':>8}{'UV':>4}{'Price':>10}{'P/E':>7}")


def _data_line(f):
    """Format data columns from a _fmt() dict."""
    return (f"{f['score']:>6}{f['eps']:>5}{f['roe']:>5}{f['fcf']:>5}{f['bal']:>5}"
            f"{f['roe_pct']:>7}{f['de']:>7}{f['cr']:>6}{f['cagr']:>7}{f['fcf_b']:>7}{f['fcf_y']:>6}{f['gw']:>5}"
            f"{f['iv']:>10}{f['mos']:>8}{f['uv']:>4}{f['price']:>10}{f['pe']:>7}")


def print_legend():
    """Print the shared column legend."""
    print(f"\n  EPS/ROE/FCF/BAL = sub-scores (0-100) | D/E = Debt-to-Equity | "
          f"CR = Current Ratio")
    print(f"  FCF$B = FCF in billions | FYld = FCF Yield | GW% = Goodwill % of Assets")
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
    print(f"  {'─' * 130}")

    for i, s in enumerate(scores, 1):
        name = (s.get("name") or "?")[:26]
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
        print(f"  Buffett Score: {r['buffett_score']}/100")

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

