#!/usr/bin/env python3
"""Generate a concise email report showing only changes and highlights.

Usage:
    python report.py weekly              # generate weekly report (stdout)
    python report.py weekly --email      # generate + send via SMTP

Environment variables for email:
    SMTP_HOST       SMTP server (default: smtp.gmail.com)
    SMTP_PORT       SMTP port (default: 587)
    SMTP_USER       Email address (sender)
    SMTP_PASS       App password or SMTP password
    REPORT_TO       Recipient email (defaults to SMTP_USER)
"""

import io
import os
import sys
import contextlib
from datetime import date, datetime


def _capture_weekly():
    """Run the weekly workflow and capture stdout."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        from commands.workflow import weekly
        weekly()
    return buf.getvalue()


def _build_report():
    """Build a concise change-focused email body."""
    lines = []
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"STOCK SCREENER — WEEKLY REPORT  {now}")
    lines.append("=" * 50)

    # --- 1. Macro one-liner ---
    from analysis.macro import analyze_macro
    macro = analyze_macro()
    from analysis.macro import macro_one_liner
    lines.append("")
    lines.append(macro_one_liner(macro))

    # --- 2. Score changes (movers) ---
    from utils.scores_db import get_biggest_movers
    from utils.lists import portfolio_list, watchlist_list
    p_set = set(t.upper() for t in portfolio_list())
    w_set = set(t.upper() for t in watchlist_list())
    tracked = p_set | w_set

    movers = get_biggest_movers()
    tracked_movers = [m for m in movers if m["symbol"] in tracked and abs(m["change"]) >= 2]

    if tracked_movers:
        lines.append("")
        lines.append("SCORE CHANGES")
        lines.append("-" * 50)
        lines.append(f"  {'Symbol':<8}{'Old':>6}{'New':>6}{'Chg':>7}  List")
        for m in tracked_movers[:15]:
            arrow = "▲" if m["change"] > 0 else "▼"
            tag = "PORT" if m["symbol"] in p_set else "WATCH"
            lines.append(f"  {m['symbol']:<8}{m['old_score']:>6.1f}{m['new_score']:>6.1f}{arrow}{abs(m['change']):>5.1f}  {tag}")
    else:
        lines.append("")
        lines.append("SCORE CHANGES: none (first scan or no changes)")

    # --- 3. Verdicts for watchlist ---
    if w_set:
        from analysis.technical import analyze_technical
        from analysis.verdict import compute_verdict
        from utils.scores_db import get_latest_scores
        latest_bs = {r["symbol"]: r for r in get_latest_scores()}

        verdicts = []
        for sym in sorted(w_set):
            ta = analyze_technical(sym)
            tech = ta.get("tech_score", 0) if ta else None
            fund = latest_bs.get(sym, {}).get("fundamental_score")
            v = compute_verdict(fund, tech, macro["macro_score"])
            verdicts.append((sym, v))

        _ORDER = {"STRONG BUY": 0, "BUY": 1, "ACCUMULATE": 2, "NEUTRAL": 3,
                  "WATCH": 4, "HOLD": 5, "AVOID": 6}
        verdicts.sort(key=lambda x: (_ORDER.get(x[1]["verdict"], 9),
                                      -(x[1].get("fund") or 0)))

        lines.append("")
        lines.append("WATCHLIST VERDICTS")
        lines.append("-" * 50)
        lines.append(f"  {'Symbol':<8}{'Fund':>5}{'Tech':>5}{'Macro':>6} {'Verdict':<14}{'Size'}")
        for sym, v in verdicts:
            f = f"{v['fund']:.0f}" if v.get("fund") is not None else "-"
            t = f"{v['tech']:.0f}" if v.get("tech") is not None else "-"
            m = f"{v['macro']:.0f}" if v.get("macro") is not None else "-"
            sz = v.get("position", "-")
            lines.append(f"  {sym:<8}{f:>5}{t:>5}{m:>6} {v['verdict']:<14}{sz}")

        # Highlight actionable
        buys = [s for s, v in verdicts if v["verdict"] in ("STRONG BUY", "BUY")]
        if buys:
            lines.append(f"\n  >> ACTION: {', '.join(buys)}")

        # Buying opportunities (undervalued)
        opps = []
        for sym in w_set:
            row = latest_bs.get(sym)
            if row and row.get("margin_of_safety") and row["margin_of_safety"] > 0:
                opps.append(row)
        if opps:
            opps.sort(key=lambda x: x["margin_of_safety"], reverse=True)
            lines.append("")
            lines.append("UNDERVALUED ON WATCHLIST")
            lines.append("-" * 50)
            for o in opps[:10]:
                price = f"${o['current_price']:.2f}" if o.get("current_price") else "-"
                iv = f"${o['intrinsic_value']:.2f}" if o.get("intrinsic_value") else "-"
                lines.append(f"  {o['symbol']:<8} Score:{o['fundamental_score']:>5.0f}  MoS:{o['margin_of_safety']:>6.1f}%  Price:{price}  IV:{iv}")

    # --- 4. Portfolio alerts ---
    if p_set:
        from commands.alerts import scan_alerts
        alerts = scan_alerts()
        p_alerts = {k: [a for a in v if a["symbol"] in p_set]
                    for k, v in alerts.items() if k in ("bargains", "score_drops", "undervalued")}
        has_alerts = any(p_alerts.values())

        if has_alerts:
            lines.append("")
            lines.append("PORTFOLIO ALERTS")
            lines.append("-" * 50)
            for kind, items in p_alerts.items():
                for a in items:
                    if kind == "score_drops":
                        lines.append(f"  ▼ {a['symbol']} score dropped {abs(a.get('change', 0)):.0f} pts")
                    elif kind == "bargains":
                        lines.append(f"  ★ {a['symbol']} bargain — Score:{a.get('fundamental_score', 0):.0f} MoS:{a.get('margin_of_safety', 0):.1f}%")
                    elif kind == "undervalued":
                        lines.append(f"  ✓ {a['symbol']} undervalued — MoS:{a.get('margin_of_safety', 0):.1f}%")

    # --- 5. New discoveries ---
    from commands.discover import _collect_all_candidates
    from utils.discovery import PRESETS
    all_results, excluded = _collect_all_candidates()
    new_cands = {t: info for t, info in all_results.items() if t not in excluded}
    ranked = sorted(new_cands.values(), key=lambda x: len(x["presets"]), reverse=True)

    if ranked:
        lines.append("")
        lines.append(f"NEW DISCOVERIES ({len(ranked)} stocks)")
        lines.append("-" * 50)
        for info in ranked[:10]:
            conv = len(info["presets"])
            stars = "★" * conv
            lines.append(f"  {info['ticker']:<8}{info['company'][:30]:<30} {stars}")
        if len(ranked) > 10:
            lines.append(f"  ... and {len(ranked) - 10} more")

    lines.append("")
    lines.append("=" * 50)
    lines.append(f"Generated by Stock Screener  {now}")
    return "\n".join(lines)


def _send_email(subject, body):
    """Send plain-text email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText

    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or "587")
    user = os.environ["SMTP_USER"]
    pw = os.environ["SMTP_PASS"]
    to = os.environ.get("REPORT_TO") or user

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, pw)
        server.send_message(msg)

    print(f"Email sent to {to}")


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    send = "--email" in args

    from utils.config import enable_cache
    enable_cache()

    # Run the full weekly analysis first (populates scores.db)
    print("Running weekly analysis...")
    output = _capture_weekly()

    # Build concise report
    print("Building report...")
    report = _build_report()

    if send:
        today = date.today().strftime("%b %d")
        _send_email(f"Stock Report — {today}", report)
    else:
        print()
        print(report)


if __name__ == "__main__":
    main()
