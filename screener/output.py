"""Output formatting: print results to terminal."""


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

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(
        f"{'#':<4} {'Symbol':<8} {'Name':<25} {'Score':<8} {'ROE%':<8} "
        f"{'EPS CAGR':<10} {'FCF Yield':<10} {'MoS%':<8} {'Underval':<8}"
    )
    print("-" * 95)
    for i, r in enumerate(top, 1):
        roe_val = f"{r['roe_analysis']['roe']}%" if r["roe_analysis"]["roe"] else "N/A"
        eps_cagr = (
            f"{r['eps_analysis']['eps_growth_rate']}%"
            if r["eps_analysis"]["eps_growth_rate"]
            else "N/A"
        )
        fcf_y = (
            f"{r['fcf_analysis']['fcf_yield']}%"
            if r["fcf_analysis"]["fcf_yield"]
            else "N/A"
        )
        mos = (
            f"{r['dcf_analysis']['margin_of_safety']}%"
            if r["dcf_analysis"]["margin_of_safety"]
            else "N/A"
        )
        uv = "✅" if r["dcf_analysis"].get("undervalued") else "❌"
        name = r["name"][:24]
        print(
            f"{i:<4} {r['symbol']:<8} {name:<25} {r['buffett_score']:<8} "
            f"{roe_val:<8} {eps_cagr:<10} {fcf_y:<10} {mos:<8} {uv:<8}"
        )


def save_results(results, filepath="buffett_results.json"):
    """Save all results to a JSON file."""
    save_data = []
    for r in results:
        save_data.append(
            {
                "symbol": r["symbol"],
                "name": r["name"],
                "sector": r["sector"],
                "buffett_score": r["buffett_score"],
                "market_cap_b": r["market_cap_b"],
                "current_price": r["current_price"],
                "roe": r["roe_analysis"]["roe"],
                "debt_to_equity": r["roe_analysis"]["debt_to_equity"],
                "eps_cagr": r["eps_analysis"]["eps_growth_rate"],
                "eps_consistent": r["eps_analysis"]["eps_consistent"],
                "fcf_current_b": r["fcf_analysis"]["fcf_current"],
                "fcf_yield": r["fcf_analysis"]["fcf_yield"],
                "intrinsic_value": r["dcf_analysis"]["intrinsic_value"],
                "margin_of_safety": r["dcf_analysis"]["margin_of_safety"],
                "undervalued": r["dcf_analysis"].get("undervalued", False),
            }
        )

    with open(filepath, "w") as f:
        json.dump(save_data, f, indent=2)

    print(f"\nFull results saved to {filepath}")
