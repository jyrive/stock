"""Verdict output — print functions for triangulation verdicts."""

from verdict.engine import _zone, _macro_multiplier


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
        mi, mlabel = _zone(macro_score)
        mult = _macro_multiplier(macro_score)
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
