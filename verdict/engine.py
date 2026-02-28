"""Triangulation verdict — converge Fundamental, Technical, and Macro scores.

Inspired by Pietari Laurila's triangulation approach: three independent
lenses must *converge* before acting.  We do NOT average;  we classify
each score into a zone, check pairwise convergence, and produce a single
verdict with a position-sizing recommendation.

Three-layer model:
    Buffett  Score → WHAT  to buy  (fundamental quality)
    Technical Score → WHEN  to buy  (entry timing)
    Macro    Score → HOW MUCH      (position sizing)

Zone thresholds:
    🟢 Strong   ≥ 70
    🟡 Neutral  40–69
    🔴 Weak     < 40

Convergence: a pair converges when both scores ≥ 60.

Veto rule: any single score < 25 caps the verdict at WATCH.
"""


# ── Zone classification ─────────────────────────────────────────

def _zone(score):
    """Classify a numeric score into a coloured zone.

    Returns (icon, label).
    """
    if score is None:
        return "⚪", "N/A"
    if score >= 70:
        return "🟢", "Strong"
    if score >= 40:
        return "🟡", "Neutral"
    return "🔴", "Weak"


def _zone_icon(score):
    """Return only the icon for compact views."""
    return _zone(score)[0]


# ── Convergence ─────────────────────────────────────────────────

def _pair_converges(a, b, threshold=60):
    """Return True when both scores are at or above *threshold*."""
    if a is None or b is None:
        return False
    return a >= threshold and b >= threshold


def _convergence(fund, tech, macro):
    """Compute pairwise convergence.

    Returns (count, details_dict).
    """
    pairs = {
        "F+T": _pair_converges(fund, tech),
        "F+M": _pair_converges(fund, macro),
        "T+M": _pair_converges(tech, macro),
    }
    count = sum(pairs.values())
    return count, pairs


# ── Macro sizing multiplier ─────────────────────────────────────

def _macro_multiplier(macro_score):
    """Position-sizing multiplier driven by macro environment.

    ≥ 70  → ×1.25  (overweight)
    40–69 → ×1.0   (normal)
    < 40  → ×0.5   (underweight)
    """
    if macro_score is None:
        return 1.0
    if macro_score >= 70:
        return 1.25
    if macro_score >= 40:
        return 1.0
    return 0.5


# ── Verdict engine ──────────────────────────────────────────────

_VERDICTS = [
    # (min_greens, max_reds, min_conv, label, low_pct, high_pct)
    (3, 0, 3, "STRONG BUY",  100, 125),
    (2, 0, 1, "BUY",          75, 100),
    (1, 0, 0, "ACCUMULATE",   50,  75),
    (0, 0, 0, "NEUTRAL",      25,  50),
]


def _count_zones(fund, tech, macro):
    """Count greens, yellows, and reds among the three scores."""
    greens = reds = 0
    for s in (fund, tech, macro):
        icon, _ = _zone(s)
        if icon == "🟢":
            greens += 1
        elif icon == "🔴":
            reds += 1
    return greens, reds


def _raw_verdict(fund, tech, macro, conv_count):
    """Determine verdict before veto rule."""
    greens, reds = _count_zones(fund, tech, macro)

    if reds >= 2:
        return "AVOID", 0, 0

    if reds == 1:
        if greens >= 2:
            return "WATCH", 0, 25
        return "HOLD", 0, 0

    for min_g, max_r, min_c, label, lo, hi in _VERDICTS:
        if greens >= min_g and reds <= max_r and conv_count >= min_c:
            return label, lo, hi

    return "NEUTRAL", 25, 50


def compute_verdict(fund, tech, macro):
    """Main entry point — return full verdict dict.

    Parameters
    ----------
    fund  : float | None   Buffett Score 0–100
    tech  : float | None   Technical Score 0–100
    macro : float | None   Macro Score 0–100

    Returns
    -------
    dict with keys: fund, tech, macro, zones, convergence, conv_count,
                    verdict, position_lo, position_hi, multiplier, veto,
                    commentary
    """
    conv_count, pairs = _convergence(fund, tech, macro)
    verdict, pos_lo, pos_hi = _raw_verdict(fund, tech, macro, conv_count)

    veto = False
    for s in (fund, tech, macro):
        if s is not None and s < 25:
            veto = True
            break
    if veto and verdict not in ("HOLD", "AVOID"):
        verdict = "WATCH"
        pos_lo, pos_hi = 0, 25

    mult = _macro_multiplier(macro)

    return {
        "fund": fund,
        "tech": tech,
        "macro": macro,
        "fund_zone": _zone(fund),
        "tech_zone": _zone(tech),
        "macro_zone": _zone(macro),
        "convergence": pairs,
        "conv_count": conv_count,
        "verdict": verdict,
        "position_lo": pos_lo,
        "position_hi": pos_hi,
        "multiplier": mult,
        "veto": veto,
        "commentary": _commentary(fund, tech, macro, verdict, pairs),
    }


# ── Commentary ──────────────────────────────────────────────────

def _commentary(fund, tech, macro, verdict, pairs):
    """Generate a one-sentence actionable commentary."""
    if verdict == "STRONG BUY":
        return "All three dimensions converge — full conviction, size up."
    if verdict == "BUY":
        return "Two strong signals confirm — buy with normal sizing."
    if verdict == "ACCUMULATE":
        weak = []
        if (tech or 0) < 60:
            weak.append("technical improvement")
        if (macro or 0) < 60:
            weak.append("macro improvement")
        if weak:
            return f"Decent setup, consider a half-position now, add on {' or '.join(weak)}."
        return "Positive setup — start building a position."
    if verdict == "NEUTRAL":
        return "Mixed signals — no urgency. Wait for clearer convergence."
    if verdict == "WATCH":
        if any(s is not None and s < 25 for s in (fund, tech, macro)):
            return "Veto triggered — one dimension is critically weak. Monitor only."
        return "One significant headwind — monitor but don't commit capital."
    if verdict == "HOLD":
        return "Conflicting signals — hold existing, don't add."
    if verdict == "AVOID":
        return "Multiple red flags — stay away or consider trimming."
    return ""
