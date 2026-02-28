"""Price target alerts: flag stocks that crossed valuation thresholds.

Scans scores.db for:
1. Newly undervalued stocks (margin of safety turned positive)
2. Stocks whose Buffett score dropped significantly
3. Custom threshold alerts from config.yaml
"""

import sys
from datetime import date, timedelta

from utils.database import get_latest_scores, get_ticker_history
from utils.config import config
from utils.colors import USE_COLOR, good, warn, bad, dim, BOLD, RESET


def _fmt_mos(mos):
    """Format margin of safety with color."""
    if mos is None:
        return dim("-") if USE_COLOR else "-"
    s = f"{mos:.1f}%"
    if mos >= 15:
        return good(s) if USE_COLOR else s
    if mos >= 0:
        return warn(s) if USE_COLOR else s
    return bad(s) if USE_COLOR else s


def _fmt_score(score):
    """Format Buffett score with color."""
    if score is None:
        return dim("-") if USE_COLOR else "-"
    s = f"{score:.0f}"
    if score >= 60:
        return good(s) if USE_COLOR else s
    if score >= 40:
        return warn(s) if USE_COLOR else s
    return bad(s) if USE_COLOR else s


def scan_alerts(db_path=None):
    """Scan database for price target alerts.

    Returns dict with:
        undervalued: stocks where margin_of_safety > threshold
        score_drops: stocks whose score dropped significantly
        bargains: stocks that are both high-scoring AND undervalued
    """
    cfg = config()
    alerts_cfg = cfg.get("alerts", {})
    mos_min = alerts_cfg.get("margin_of_safety_min", 0)
    score_drop_thresh = alerts_cfg.get("score_drop_threshold", 10)

    latest = get_latest_scores(db_path)

    undervalued = []
    score_drops = []
    bargains = []

    for row in latest:
        symbol = row["symbol"]
        mos = row.get("margin_of_safety")
        score = row.get("buffett_score")
        price = row.get("current_price")
        iv = row.get("intrinsic_value")

        # 1. Undervalued stocks
        if mos is not None and mos > mos_min:
            undervalued.append({
                "symbol": symbol,
                "name": row.get("name", ""),
                "sector": row.get("sector", ""),
                "price": price,
                "intrinsic_value": iv,
                "margin_of_safety": mos,
                "buffett_score": score,
                "scan_date": row.get("scan_date"),
            })

        # 2. Check for score drops
        history = get_ticker_history(symbol, db_path)
        if len(history) >= 2:
            prev_score = history[-2].get("buffett_score")
            curr_score = history[-1].get("buffett_score")
            if prev_score is not None and curr_score is not None:
                drop = prev_score - curr_score
                if drop >= score_drop_thresh:
                    score_drops.append({
                        "symbol": symbol,
                        "name": row.get("name", ""),
                        "prev_score": prev_score,
                        "curr_score": curr_score,
                        "drop": round(drop, 1),
                        "prev_date": history[-2].get("scan_date"),
                        "curr_date": history[-1].get("scan_date"),
                    })

        # 3. Bargains: high score AND undervalued
        if score is not None and score >= 55 and mos is not None and mos > 10:
            bargains.append({
                "symbol": symbol,
                "name": row.get("name", ""),
                "sector": row.get("sector", ""),
                "price": price,
                "intrinsic_value": iv,
                "margin_of_safety": mos,
                "buffett_score": score,
            })

    # Sort
    undervalued.sort(key=lambda x: x.get("margin_of_safety", 0), reverse=True)
    score_drops.sort(key=lambda x: x.get("drop", 0), reverse=True)
    bargains.sort(key=lambda x: x.get("buffett_score", 0), reverse=True)

    return {
        "undervalued": undervalued,
        "score_drops": score_drops,
        "bargains": bargains,
    }


def print_alerts(alerts):
    """Print alert results to terminal."""

    bargains = alerts["bargains"]
    undervalued = alerts["undervalued"]
    score_drops = alerts["score_drops"]

    print(f"\n{'═' * 72}")
    print(f"  PRICE TARGET ALERTS")
    print(f"{'═' * 72}")

    # ── Bargains ─────────────────────────────────────────────
    if bargains:
        print(f"\n  🎯 BARGAIN ALERTS — High score + undervalued ({len(bargains)} stocks)")
        print(f"  {'─' * 68}")
        print(f"  {'Symbol':<8}{'Name':<26}{'Score':>7}{'Price':>9}{'IV':>9}{'MoS%':>8}")
        print(f"  {'─' * 68}")
        for b in bargains:
            score_str = _fmt_score(b["buffett_score"])
            mos_str = _fmt_mos(b["margin_of_safety"])
            price = f"${b['price']:.2f}" if b["price"] else "-"
            iv = f"${b['intrinsic_value']:.2f}" if b["intrinsic_value"] else "-"
            name = (b["name"] or "")[:24]

            if USE_COLOR:
                import re
                # Calculate visible widths for alignment
                score_vis = len(re.sub(r'\033\[[0-9;]*m', '', score_str))
                mos_vis = len(re.sub(r'\033\[[0-9;]*m', '', mos_str))
                print(f"  {b['symbol']:<8}{name:<26}"
                      f"{' ' * (7 - score_vis)}{score_str}"
                      f"{price:>9}{iv:>9}"
                      f"{' ' * (8 - mos_vis)}{mos_str}")
            else:
                print(f"  {b['symbol']:<8}{name:<26}{b['buffett_score']:>7.0f}"
                      f"{price:>9}{iv:>9}{b['margin_of_safety']:>7.1f}%")
    else:
        print(f"\n  No bargain alerts (score ≥55 and MoS >10%)")

    # ── Undervalued ──────────────────────────────────────────
    if undervalued:
        print(f"\n  💰 UNDERVALUED — Trading below intrinsic value ({len(undervalued)} stocks)")
        print(f"  {'─' * 68}")
        print(f"  {'Symbol':<8}{'Name':<26}{'Price':>9}{'IV':>9}{'MoS%':>8}{'Score':>7}")
        print(f"  {'─' * 68}")
        for u in undervalued[:15]:  # Limit display
            price = f"${u['price']:.2f}" if u["price"] else "-"
            iv = f"${u['intrinsic_value']:.2f}" if u["intrinsic_value"] else "-"
            name = (u["name"] or "")[:24]
            print(f"  {u['symbol']:<8}{name:<26}{price:>9}{iv:>9}"
                  f"{u['margin_of_safety']:>7.1f}%{u['buffett_score']:>7.0f}")
        if len(undervalued) > 15:
            print(f"  ... and {len(undervalued) - 15} more")
    else:
        print(f"\n  No undervalued stocks found (MoS > {config().get('alerts', {}).get('margin_of_safety_min', 0)}%)")

    # ── Score drops ──────────────────────────────────────────
    if score_drops:
        print(f"\n  📉 SCORE DROPS — Significant declines ({len(score_drops)} stocks)")
        print(f"  {'─' * 68}")
        print(f"  {'Symbol':<8}{'Name':<26}{'Prev':>7}{'Curr':>7}{'Drop':>7}{'Dates'}")
        print(f"  {'─' * 68}")
        for sd in score_drops[:10]:
            name = (sd["name"] or "")[:24]
            drop_str = f"-{sd['drop']:.0f}"
            if USE_COLOR:
                drop_str = bad(drop_str)
            dates = f"{sd['prev_date']} → {sd['curr_date']}"
            print(f"  {sd['symbol']:<8}{name:<26}{sd['prev_score']:>7.0f}"
                  f"{sd['curr_score']:>7.0f}  {drop_str}  {dates}")
    else:
        print(f"\n  No significant score drops detected")

    total = len(bargains) + len(undervalued) + len(score_drops)
    print(f"\n  Total alerts: {total}")
    print()


def main():
    """Entry point for the alerts command."""
    alerts = scan_alerts()
    print_alerts(alerts)


if __name__ == "__main__":
    main()
