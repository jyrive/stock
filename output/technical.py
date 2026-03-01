"""Technical analysis output — print functions for TA results."""


def _entry_rating(tech_score, fundamental_score=None):
    """Generate a star rating + label for combined conviction.

    Returns (stars_str, label) like ("★★★★☆", "STRONG BUY SIGNAL").
    """
    if fundamental_score is not None and fundamental_score >= 55 and tech_score >= 70:
        return "★★★★★", "HIGHEST CONVICTION"
    if fundamental_score is not None and fundamental_score >= 55 and tech_score >= 50:
        return "★★★★☆", "STRONG BUY SIGNAL"
    if tech_score >= 70:
        return "★★★★☆", "STRONG ENTRY POINT"
    if tech_score >= 50:
        return "★★★☆☆", "GOOD ENTRY POINT"
    if tech_score >= 30:
        return "★★☆☆☆", "NEUTRAL"
    return "★☆☆☆☆", "WAIT FOR BETTER ENTRY"


def print_technical(ta, fundamental_score=None):
    """Print detailed technical analysis for a single ticker."""
    symbol = ta["symbol"]
    price = ta.get("current_price")
    tech_score = ta.get("tech_score", 0)

    print(f"\n{'─' * 60}")
    print(f"  TECHNICAL ANALYSIS — {symbol}")
    print(f"{'─' * 60}")

    if price is None:
        print("  Could not fetch price history.\n")
        return

    print(f"  Price: ${price}")
    print(f"  52-week: ${ta['week52_low']} — ${ta['week52_high']}"
          f"  (position: {ta['week52_position']:.0%})")

    print(f"\n  {'Indicator':<25}{'Value':>12}  {'Signal'}")
    print(f"  {'─' * 58}")

    # RSI
    rsi_str = f"{ta['rsi_14']:.1f}" if ta['rsi_14'] is not None else "-"
    print(f"  {'RSI (14)':<25}{rsi_str:>12}  {ta['rsi_signal']}")

    # Price vs 50 MA
    pct50 = ta.get("price_vs_sma50_pct")
    pct50_str = f"{pct50:+.1f}%" if pct50 is not None else "-"
    print(f"  {'Price vs 50-day MA':<25}{pct50_str:>12}  {ta['sma50_signal']}")

    # Price vs 200 MA
    pct200 = ta.get("price_vs_sma200_pct")
    pct200_str = f"{pct200:+.1f}%" if pct200 is not None else "-"
    print(f"  {'Price vs 200-day MA':<25}{pct200_str:>12}  {ta['sma200_signal']}")

    # Bollinger Band
    bb_pos = ta.get("bb_position")
    bb_pos_str = f"{bb_pos:.0%}" if bb_pos is not None else "-"
    print(f"  {'Bollinger Band':<25}{bb_pos_str:>12}  {ta['bb_signal']}")

    # MACD
    macd = ta.get("macd")
    if macd:
        macd_str = f"{macd['histogram']:+.3f}"
        crossover_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(macd["crossover"], "⚪")
        print(f"  {'MACD Histogram':<25}{macd_str:>12}  {crossover_icon} {macd['crossover'].title()} crossover")
    else:
        print(f"  {'MACD':<25}{'-':>12}  N/A (insufficient data)")

    # Tech score
    stars, label = _entry_rating(tech_score, fundamental_score)
    print(f"\n  Tech Score: {tech_score}/100")
    if fundamental_score is not None:
        print(f"  Fundamental Score: {fundamental_score}/100")
    print(f"  Entry Rating: {stars}  {label}")

    # Signals
    signals = ta.get("signals", [])
    if signals:
        print(f"\n  Signals:")
        for s in signals:
            print(f"    {s}")

    print()
