"""Triangulation verdict — converge Fundamental, Technical, and Macro scores.

Three independent
lenses must *converge* before acting.  We do NOT average;  we classify
each score into a zone, check pairwise convergence, and produce a single
verdict with a position-sizing recommendation.

Three-layer model:
    Fundamental  Score → WHAT  to buy  (fundamental quality)
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

def zone(score):
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
    return zone(score)[0]


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

def macro_multiplier(macro_score):
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
        icon, _ = zone(s)
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
    fund  : float | None   Fundamental Score 0–100
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

    mult = macro_multiplier(macro)

    return {
        "fund": fund,
        "tech": tech,
        "macro": macro,
        "fund_zone": zone(fund),
        "tech_zone": zone(tech),
        "macro_zone": zone(macro),
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

# ── Sell-signal logic (for auto-trading) ────────────────────────────

# Verdict hierarchy: higher value = worse signal for holding
_VERDICT_RANK = {
    "STRONG BUY": 0, "BUY": 1, "ACCUMULATE": 2, "NEUTRAL": 3,
    "WATCH": 4, "HOLD": 5, "AVOID": 6,
}


def should_sell(verdict_dict, previous_verdict=None):
    """Determine whether the auto-trader should sell a position.

    Returns (should_sell: bool, reason: str).

    Sell rules:
    1. AVOID verdict              → full sell
    2. HOLD + downgrade from BUY+ → full sell (deteriorating quality)
    3. WATCH with veto            → full sell (critical weakness)
    """
    verdict = verdict_dict["verdict"]

    if verdict == "AVOID":
        return True, "Verdict AVOID — multiple red flags"

    if verdict == "WATCH" and verdict_dict.get("veto"):
        return True, "Veto triggered — critically weak dimension"

    if verdict == "HOLD" and previous_verdict:
        prev_rank = _VERDICT_RANK.get(previous_verdict, 3)
        if prev_rank <= 2:  # Was ACCUMULATE or better
            return True, f"Downgrade from {previous_verdict} to HOLD"

    return False, ""


def should_buy(verdict_dict):
    """Determine whether the auto-trader should buy.

    Returns (should_buy: bool, action: str, reason: str).
    action is one of: "BUY" (new position) or "ADD" (add to existing).
    """
    verdict = verdict_dict["verdict"]

    if verdict == "STRONG BUY":
        return True, "BUY", "Strong conviction — all dimensions converge"
    if verdict == "BUY":
        return True, "BUY", "Two strong signals confirm"
    if verdict == "ACCUMULATE":
        return True, "BUY", "Positive setup — building position"

    return False, "", ""


# ── Display Functions ────────────────────────────────────────────

def print_verdict(v, symbol=None, name=None):
    """Print a full verdict card for one stock."""
    header = f"VERDICT: {symbol}" if symbol else "VERDICT"
    if name:
        header += f" — {name}"

    print(f"\n{'═' * 60}")
    print(f"  {header}")
    print(f"{'═' * 60}")

    # Scores + zones
    def _row(label, score, zone_tuple, role):
        icon, zlabel = zone_tuple
        s_str = f"{score:.0f}/100" if score is not None else "  -   "
        return f"  {label:<14}{s_str}  {icon} {zlabel:<8} │ {role}"

    print(_row("Fundamental", v["fund"], v["fund_zone"], "WHAT to buy"))
    print(_row("Technical",   v["tech"], v["tech_zone"], "WHEN to buy"))
    print(_row("Macro",       v["macro"], v["macro_zone"], "HOW MUCH to buy"))

    # Convergence
    pairs = v["convergence"]
    conv_parts = []
    for key, ok in pairs.items():
        conv_parts.append(f"{key} {'✓' if ok else '✗'}")
    print(f"\n  Convergence   {' '.join(conv_parts)}   ({v['conv_count']}/3)")

    # Verdict + position
    print(f"  Verdict       {v['verdict']}")
    if v["position_hi"] > 0:
        print(f"  Position      {v['position_lo']}–{v['position_hi']}% of normal size (macro ×{v['multiplier']:.2f})")
    else:
        print(f"  Position      0% — do not commit new capital")

    if v["veto"]:
        print(f"  ⚠️  VETO — one score < 25 caps verdict at WATCH")

    # Commentary
    print(f"\n  ► {v['commentary']}")
    print(f"{'═' * 60}")


def verdict_one_liner(v, symbol):
    """Return a single-line verdict string for daily workflow."""
    fi, _ = v["fund_zone"]
    ti, _ = v["tech_zone"]
    mi, _ = v["macro_zone"]
    lo, hi = v["position_lo"], v["position_hi"]
    pos = f"{lo}-{hi}%" if hi > 0 else "0%"
    return f"{symbol:<7} {fi}{ti}{mi} {v['verdict']:<14} {pos}"


def print_verdict_table(verdicts, title="PORTFOLIO VERDICT"):
    """Print a compact table for multiple verdicts.

    Parameters
    ----------
    verdicts : list of (symbol, verdict_dict) tuples
    """
    # Show macro context once at the top
    if verdicts:
        macro_score = verdicts[0][1]["macro"]
        mi, mlabel = zone(macro_score)
        mult = macro_multiplier(macro_score)
        print(f"\n  Macro: {macro_score:.0f}/100 {mi} {mlabel} — sizing ×{mult:.2f}")

    print(f"\n  {'Symbol':<8}{'Fund':>6}{'Tech':>6}{'Macro':>6}  {'Zones':<6}{'Conv':>5}  {'Verdict':<14}{'Size'}")
    print(f"  {'─' * 68}")

    for symbol, v in verdicts:
        fi, _ = v["fund_zone"]
        ti, _ = v["tech_zone"]
        mi, _ = v["macro_zone"]
        zones = f"{fi}{ti}{mi}"
        conv = f"{v['conv_count']}/3"
        fs = f"{v['fund']:.0f}" if v["fund"] is not None else "-"
        ts = f"{v['tech']:.0f}" if v["tech"] is not None else "-"
        ms = f"{v['macro']:.0f}" if v["macro"] is not None else "-"
        lo, hi = v["position_lo"], v["position_hi"]
        pos = f"{lo}-{hi}%" if hi > 0 else "0%"
        print(f"  {symbol:<8}{fs:>6}{ts:>6}{ms:>6}  {zones:<6}{conv:>5}  {v['verdict']:<14}{pos}")
