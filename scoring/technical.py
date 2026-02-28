"""Technical analysis: entry-timing indicators using price history.

Computes RSI, moving averages, Bollinger Bands, MACD, and 52-week range
to produce a Technical Score (0-100) — higher means better entry point
(the stock is oversold / near support / more attractive to buy NOW).

Philosophy: Buffett Score tells you WHAT to buy, Technical Score tells
you WHEN to buy.
"""

import numpy as np
import yfinance as yf


# ── Indicator Computations ──────────────────────────────────────────

def _rsi(closes, period=14):
    """Compute RSI (Relative Strength Index).

    Returns the most recent RSI value (0-100).
    Lower RSI = more oversold = better entry.
    """
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _sma(closes, period):
    """Simple Moving Average of the last `period` values."""
    if len(closes) < period:
        return None
    return float(np.mean(closes[-period:]))


def _ema(closes, period):
    """Exponential Moving Average."""
    if len(closes) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_val = np.mean(closes[:period])  # seed with SMA
    for price in closes[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val
    return float(ema_val)


def _bollinger_bands(closes, period=20, num_std=2):
    """Compute Bollinger Bands.

    Returns (lower, middle, upper) or (None, None, None).
    """
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    middle = float(np.mean(window))
    std = float(np.std(window, ddof=1))
    return (
        round(middle - num_std * std, 2),
        round(middle, 2),
        round(middle + num_std * std, 2),
    )


def _macd(closes, fast=12, slow=26, signal=9):
    """Compute MACD line, signal line, and histogram.

    Returns dict with macd_line, signal_line, histogram, crossover.
    """
    if len(closes) < slow + signal:
        return None

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None

    # Calculate full MACD line series for signal line
    # We need at least slow + signal periods
    macd_series = []
    for i in range(slow, len(closes) + 1):
        subset = closes[:i]
        ef = _ema(subset, fast)
        es = _ema(subset, slow)
        if ef is not None and es is not None:
            macd_series.append(ef - es)

    if len(macd_series) < signal:
        return None

    macd_line = macd_series[-1]

    # Signal line = EMA of MACD series
    macd_arr = np.array(macd_series)
    signal_line = _ema(macd_arr, signal)
    if signal_line is None:
        return None

    histogram = macd_line - signal_line

    # Bullish crossover: MACD crosses above signal
    # Check last 2 values
    crossover = "neutral"
    if len(macd_series) >= 2:
        prev_macd = macd_series[-2]
        prev_signal_arr = np.array(macd_series[:-1])
        prev_signal = _ema(prev_signal_arr, signal) if len(prev_signal_arr) >= signal else None
        if prev_signal is not None:
            if prev_macd <= prev_signal and macd_line > signal_line:
                crossover = "bullish"
            elif prev_macd >= prev_signal and macd_line < signal_line:
                crossover = "bearish"

    return {
        "macd_line": round(macd_line, 3),
        "signal_line": round(signal_line, 3),
        "histogram": round(histogram, 3),
        "crossover": crossover,
    }


def _week52_position(closes):
    """Compute where the current price sits in the 52-week range.

    Returns 0.0 (at 52-week low) to 1.0 (at 52-week high).
    """
    if len(closes) < 5:
        return None
    # Use up to ~252 trading days (1 year)
    window = closes[-252:] if len(closes) >= 252 else closes
    low = float(np.min(window))
    high = float(np.max(window))
    current = float(closes[-1])
    if high == low:
        return 0.5
    return round((current - low) / (high - low), 3)


# ── Signal Interpretation ───────────────────────────────────────────

def _rsi_signal(rsi_val):
    """Interpret RSI value."""
    if rsi_val is None:
        return "N/A", ""
    if rsi_val < 30:
        return "OVERSOLD", "🟢"
    if rsi_val < 40:
        return "Near oversold", "🟡"
    if rsi_val > 70:
        return "OVERBOUGHT", "🔴"
    if rsi_val > 60:
        return "Near overbought", "🟡"
    return "Neutral", "⚪"


def _ma_signal(price, ma_val, label):
    """Interpret price vs moving average."""
    if ma_val is None or price is None:
        return "N/A", "", None
    pct = round((price - ma_val) / ma_val * 100, 1)
    if pct < -10:
        return f"{pct}% below {label}", "🟢", pct
    if pct < -3:
        return f"{pct}% below {label}", "🟡", pct
    if pct > 10:
        return f"+{pct}% above {label}", "🔴", pct
    if pct > 3:
        return f"+{pct}% above {label}", "🟡", pct
    return f"{pct:+.1f}% vs {label}", "⚪", pct


def _bb_signal(price, lower, middle, upper):
    """Interpret Bollinger Band position."""
    if None in (price, lower, middle, upper):
        return "N/A", "", None
    band_width = upper - lower
    if band_width == 0:
        return "N/A", "", None
    position = (price - lower) / band_width  # 0 = at lower, 1 = at upper
    if position <= 0.1:
        return "At lower band", "🟢", round(position, 2)
    if position <= 0.3:
        return "Near lower band", "🟡", round(position, 2)
    if position >= 0.9:
        return "At upper band", "🔴", round(position, 2)
    if position >= 0.7:
        return "Near upper band", "🟡", round(position, 2)
    return "Mid-range", "⚪", round(position, 2)


# ── Main Analysis Function ─────────────────────────────────────────

def analyze_technical(ticker_symbol):
    """Run technical analysis on a ticker.

    Fetches 1 year of daily price history from yfinance and computes
    RSI, SMA(50/200), Bollinger Bands, MACD, and 52-week range position.

    Returns dict with all indicators, signals, and a tech_score (0-100).
    Higher score = better entry point (more oversold/attractive).
    """
    result = {
        "symbol": ticker_symbol,
        "tech_score": 0,
        "current_price": None,
        "rsi_14": None,
        "rsi_signal": "N/A",
        "sma_50": None,
        "sma_200": None,
        "price_vs_sma50_pct": None,
        "price_vs_sma200_pct": None,
        "sma50_signal": "N/A",
        "sma200_signal": "N/A",
        "bb_lower": None,
        "bb_middle": None,
        "bb_upper": None,
        "bb_position": None,
        "bb_signal": "N/A",
        "macd": None,
        "week52_position": None,
        "week52_high": None,
        "week52_low": None,
        "signals": [],
    }

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1y")

        if hist.empty or len(hist) < 30:
            return result

        closes = hist["Close"].values.astype(float)
        current_price = float(closes[-1])
        result["current_price"] = round(current_price, 2)

        # 52-week range
        result["week52_high"] = round(float(np.max(closes)), 2)
        result["week52_low"] = round(float(np.min(closes)), 2)

        # ── RSI ─────────────────────────────────
        rsi_val = _rsi(closes)
        result["rsi_14"] = rsi_val
        sig_text, sig_icon = _rsi_signal(rsi_val)
        result["rsi_signal"] = f"{sig_icon} {sig_text}"

        # ── Moving Averages ─────────────────────
        sma50 = _sma(closes, 50)
        sma200 = _sma(closes, 200)
        result["sma_50"] = round(sma50, 2) if sma50 else None
        result["sma_200"] = round(sma200, 2) if sma200 else None

        sig50_text, sig50_icon, pct50 = _ma_signal(current_price, sma50, "50-day MA")
        sig200_text, sig200_icon, pct200 = _ma_signal(current_price, sma200, "200-day MA")
        result["sma50_signal"] = f"{sig50_icon} {sig50_text}"
        result["sma200_signal"] = f"{sig200_icon} {sig200_text}"
        result["price_vs_sma50_pct"] = pct50
        result["price_vs_sma200_pct"] = pct200

        # ── Bollinger Bands ─────────────────────
        bb_lower, bb_middle, bb_upper = _bollinger_bands(closes)
        result["bb_lower"] = bb_lower
        result["bb_middle"] = bb_middle
        result["bb_upper"] = bb_upper
        bb_sig_text, bb_sig_icon, bb_pos = _bb_signal(current_price, bb_lower, bb_middle, bb_upper)
        result["bb_signal"] = f"{bb_sig_icon} {bb_sig_text}"
        result["bb_position"] = bb_pos

        # ── MACD ────────────────────────────────
        macd_result = _macd(closes)
        result["macd"] = macd_result

        # ── 52-week position ────────────────────
        w52_pos = _week52_position(closes)
        result["week52_position"] = w52_pos

        # ── Compute Technical Score ─────────────
        score = _compute_tech_score(result)
        result["tech_score"] = score

        # ── Generate signal summary ─────────────
        result["signals"] = _summarize_signals(result)

    except Exception as e:
        result["error"] = str(e)

    return result


def _compute_tech_score(ta):
    """Compute technical entry score 0-100 (higher = better entry).

    Weights:
        RSI (25):           Oversold = high score
        Price vs 200 MA (25): Below MA = high score
        Bollinger Band (20):  Near lower band = high score
        52-week range (15):   Near 52-week low = high score
        MACD (15):           Bullish crossover = high score
    """
    score = 0

    # RSI (0-25 points): oversold (RSI < 30) = 25, neutral (50) = 12.5, overbought (>70) = 0
    rsi = ta.get("rsi_14")
    if rsi is not None:
        if rsi <= 30:
            score += 25
        elif rsi <= 50:
            # Linear scale: 30 → 25, 50 → 12.5
            score += 25 - (rsi - 30) * (12.5 / 20)
        elif rsi <= 70:
            # 50 → 12.5, 70 → 0
            score += 12.5 - (rsi - 50) * (12.5 / 20)
        # >70 = 0

    # Price vs 200-day MA (0-25 points): >10% below = 25, at MA = 10, >10% above = 0
    pct200 = ta.get("price_vs_sma200_pct")
    if pct200 is not None:
        if pct200 <= -10:
            score += 25
        elif pct200 <= 0:
            # -10% → 25, 0% → 10
            score += 25 - (-pct200 - 10) * (-15 / 10)  # = 25 + (pct200) * 1.5
            score = max(0, min(score, score))  # clamp
            # Simpler: linear from -10 (25) to 0 (10)
            score -= (25 - (10 + (-pct200) * 1.5))  # recompute
        elif pct200 <= 10:
            score += 10 - pct200
        # >10% above = 0
        # Let me redo this more clearly
    # Redo Price vs 200-day MA scoring cleanly
    score_200 = 0
    if pct200 is not None:
        if pct200 <= -10:
            score_200 = 25
        elif pct200 <= 0:
            score_200 = 10 + (-pct200) * 1.5  # 0% → 10, -10% → 25
        elif pct200 <= 10:
            score_200 = max(0, 10 - pct200)  # 0% → 10, 10% → 0
        else:
            score_200 = 0
    # Replace the incorrect incremental with clean value
    # Reset score to just RSI portion and add clean 200MA portion
    rsi_portion = 0
    if rsi is not None:
        if rsi <= 30:
            rsi_portion = 25
        elif rsi <= 50:
            rsi_portion = 25 - (rsi - 30) * (12.5 / 20)
        elif rsi <= 70:
            rsi_portion = 12.5 - (rsi - 50) * (12.5 / 20)

    score = rsi_portion + score_200

    # Bollinger Band position (0-20 points): at lower band (0.0) = 20, middle (0.5) = 5, upper (1.0) = 0
    bb_pos = ta.get("bb_position")
    if bb_pos is not None:
        if bb_pos <= 0.1:
            score += 20
        elif bb_pos <= 0.5:
            score += 20 - (bb_pos - 0.1) * (15 / 0.4)  # 0.1 → 20, 0.5 → 5
        elif bb_pos <= 1.0:
            score += max(0, 5 - (bb_pos - 0.5) * (5 / 0.5))  # 0.5 → 5, 1.0 → 0

    # 52-week range (0-15 points): near low (0.0) = 15, middle (0.5) = 5, near high (1.0) = 0
    w52 = ta.get("week52_position")
    if w52 is not None:
        if w52 <= 0.2:
            score += 15
        elif w52 <= 0.5:
            score += 15 - (w52 - 0.2) * (10 / 0.3)  # 0.2 → 15, 0.5 → 5
        elif w52 <= 1.0:
            score += max(0, 5 - (w52 - 0.5) * (5 / 0.5))

    # MACD (0-15 points): bullish crossover = 15, neutral = 7, bearish = 0
    macd = ta.get("macd")
    if macd is not None:
        if macd["crossover"] == "bullish":
            score += 15
        elif macd["crossover"] == "neutral":
            # Positive histogram = slightly bullish
            if macd["histogram"] > 0:
                score += 10
            else:
                score += 5
        # bearish = 0

    return min(round(score), 100)


def _summarize_signals(ta):
    """Generate a list of actionable signal strings."""
    signals = []
    rsi = ta.get("rsi_14")
    if rsi is not None:
        if rsi < 30:
            signals.append("🟢 RSI oversold — potential bounce")
        elif rsi > 70:
            signals.append("🔴 RSI overbought — caution")

    pct200 = ta.get("price_vs_sma200_pct")
    if pct200 is not None and pct200 < -5:
        signals.append(f"🟢 Trading {abs(pct200):.1f}% below 200-day MA")

    bb_pos = ta.get("bb_position")
    if bb_pos is not None and bb_pos <= 0.15:
        signals.append("🟢 At lower Bollinger Band — stretched low")

    w52 = ta.get("week52_position")
    if w52 is not None and w52 <= 0.2:
        signals.append("🟢 Near 52-week low — deep discount")

    macd = ta.get("macd")
    if macd is not None and macd["crossover"] == "bullish":
        signals.append("🟢 MACD bullish crossover — momentum turning up")

    if not signals:
        if rsi is not None and 40 <= rsi <= 60:
            signals.append("⚪ No strong entry signals — neutral territory")

    return signals


def _entry_rating(tech_score, buffett_score=None):
    """Generate a star rating + label for combined conviction.

    Returns (stars_str, label) like ("★★★★☆", "STRONG BUY SIGNAL").
    """
    if buffett_score is not None and buffett_score >= 55 and tech_score >= 70:
        return "★★★★★", "HIGHEST CONVICTION"
    if buffett_score is not None and buffett_score >= 55 and tech_score >= 50:
        return "★★★★☆", "STRONG BUY SIGNAL"
    if tech_score >= 70:
        return "★★★★☆", "STRONG ENTRY POINT"
    if tech_score >= 50:
        return "★★★☆☆", "GOOD ENTRY POINT"
    if tech_score >= 30:
        return "★★☆☆☆", "NEUTRAL"
    return "★☆☆☆☆", "WAIT FOR BETTER ENTRY"


def print_technical(ta, buffett_score=None):
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
    stars, label = _entry_rating(tech_score, buffett_score)
    print(f"\n  Tech Score: {tech_score}/100")
    if buffett_score is not None:
        print(f"  Buffett Score: {buffett_score}/100")
    print(f"  Entry Rating: {stars}  {label}")

    # Signals
    signals = ta.get("signals", [])
    if signals:
        print(f"\n  Signals:")
        for s in signals:
            print(f"    {s}")

    print()
