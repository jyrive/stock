"""HTML report generator — produces a self-contained fund fact-sheet style report.

Generates clean, professional HTML with:
  - Key performance metrics
  - Monthly returns heatmap table
  - Yearly returns summary
  - Equity curve chart (inline SVG)
  - Trade journal
  - Benchmark comparison
  - All values in both USD and EUR
"""

import os
from datetime import datetime
from typing import Dict, List, Optional


# ── SVG chart generation ─────────────────────────────────────────────

def _svg_equity_curve(equity_curve: List[dict], benchmarks: dict, width=900, height=340) -> str:
    """Generate an inline SVG line chart of the equity curve + benchmarks."""
    if not equity_curve or len(equity_curve) < 2:
        return "<p>Not enough data for chart.</p>"

    margin = {"top": 30, "right": 120, "bottom": 40, "left": 70}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    # Normalize all series to 100 base
    dates = [e["date"] for e in equity_curve]
    portfolio_vals = [e["value_eur"] for e in equity_curve]
    base = portfolio_vals[0] if portfolio_vals[0] > 0 else 1
    portfolio_norm = [v / base * 100 for v in portfolio_vals]

    all_series = {"Portfolio": portfolio_norm}
    colors = {"Portfolio": "#2563eb"}
    bench_colors = ["#dc2626", "#16a34a", "#9333ea", "#ea580c"]

    for i, (sym, data) in enumerate(benchmarks.items()):
        series = data.get("series", [])
        if not series:
            continue
        # Build lookup
        bench_lookup = {s["date"]: s["price"] for s in series}
        bench_base = series[0]["price"] if series else 1
        bench_norm = []
        last_val = 100
        for d in dates:
            if d in bench_lookup:
                last_val = bench_lookup[d] / bench_base * 100
            bench_norm.append(last_val)
        all_series[sym] = bench_norm
        colors[sym] = bench_colors[i % len(bench_colors)]

    # Find global min/max
    all_vals = []
    for vals in all_series.values():
        all_vals.extend(vals)
    y_min = min(all_vals) * 0.95
    y_max = max(all_vals) * 1.05

    def x_pos(i):
        return margin["left"] + (i / max(1, len(dates) - 1)) * plot_w

    def y_pos(v):
        if y_max == y_min:
            return margin["top"] + plot_h / 2
        return margin["top"] + plot_h - ((v - y_min) / (y_max - y_min)) * plot_h

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;max-width:{width}px;height:auto;font-family:system-ui,sans-serif;">',
        # Background
        f'<rect width="{width}" height="{height}" fill="#fafafa" rx="8"/>',
    ]

    # Grid lines
    num_grid = 5
    for j in range(num_grid + 1):
        gy = margin["top"] + j * plot_h / num_grid
        gv = y_max - j * (y_max - y_min) / num_grid
        svg_parts.append(
            f'<line x1="{margin["left"]}" y1="{gy:.0f}" x2="{margin["left"] + plot_w}" '
            f'y2="{gy:.0f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        svg_parts.append(
            f'<text x="{margin["left"] - 8}" y="{gy + 4:.0f}" text-anchor="end" '
            f'fill="#6b7280" font-size="11">{gv:.0f}</text>'
        )

    # X-axis labels (show ~6 dates)
    step = max(1, len(dates) // 6)
    for j in range(0, len(dates), step):
        xp = x_pos(j)
        label = dates[j][:7]  # YYYY-MM
        svg_parts.append(
            f'<text x="{xp:.0f}" y="{margin["top"] + plot_h + 20}" text-anchor="middle" '
            f'fill="#6b7280" font-size="11">{label}</text>'
        )

    # Draw lines
    legend_y = margin["top"] + 15
    for name, vals in all_series.items():
        color = colors.get(name, "#6b7280")
        is_portfolio = name == "Portfolio"
        stroke_w = "2.5" if is_portfolio else "1.5"
        opacity = "1" if is_portfolio else "0.6"
        dash = "" if is_portfolio else 'stroke-dasharray="6,3"'

        points = " ".join(f"{x_pos(i):.1f},{y_pos(v):.1f}" for i, v in enumerate(vals))
        svg_parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_w}" opacity="{opacity}" {dash}/>'
        )

        # Legend
        lx = margin["left"] + plot_w + 10
        svg_parts.append(
            f'<line x1="{lx}" y1="{legend_y}" x2="{lx + 20}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2" {dash}/>'
        )
        svg_parts.append(
            f'<text x="{lx + 25}" y="{legend_y + 4}" fill="#374151" font-size="12">'
            f'{name}</text>'
        )
        # End value
        end_val = vals[-1]
        svg_parts.append(
            f'<text x="{lx + 25}" y="{legend_y + 17}" fill="#6b7280" font-size="10">'
            f'{end_val - 100:+.1f}%</text>'
        )
        legend_y += 35

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


# ── Monthly returns heatmap ──────────────────────────────────────────

def _monthly_returns_table(monthly_returns: List[dict]) -> str:
    """Generate HTML monthly returns heatmap table."""
    if not monthly_returns:
        return "<p>No monthly data.</p>"

    months_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Group by year
    by_year = {}
    for m in monthly_returns:
        by_year.setdefault(m["year"], {})[m["month"]] = m

    years = sorted(by_year.keys())

    rows = []
    # Header
    header = "<tr><th>Year</th>"
    for abbr in months_abbr:
        header += f"<th>{abbr}</th>"
    header += "<th>Year Total</th></tr>"
    rows.append(header)

    for year in years:
        row = f"<tr><td class='year-label'>{year}</td>"
        year_cum = 0
        for month in range(1, 13):
            if month in by_year[year]:
                ret = by_year[year][month]["return_pct"]
                year_cum += ret
                bg = _return_color(ret)
                row += f'<td style="background:{bg};color:#1f2937;text-align:center">{ret:+.1f}%</td>'
            else:
                row += '<td style="background:#f9fafb;color:#d1d5db;text-align:center">—</td>'
        # Year total
        bg = _return_color(year_cum)
        row += f'<td style="background:{bg};font-weight:600;text-align:center">{year_cum:+.1f}%</td>'
        row += "</tr>"
        rows.append(row)

    return f"""
    <table class="monthly-table">
        {"".join(rows)}
    </table>
    """


def _return_color(ret_pct: float) -> str:
    """Map a return percentage to a background color."""
    if ret_pct >= 5:
        return "#bbf7d0"
    if ret_pct >= 2:
        return "#dcfce7"
    if ret_pct >= 0:
        return "#f0fdf4"
    if ret_pct >= -2:
        return "#fef2f2"
    if ret_pct >= -5:
        return "#fecaca"
    return "#fca5a5"


# ── Yearly summary table ────────────────────────────────────────────

def _yearly_summary_table(yearly_returns: List[dict]) -> str:
    """Generate yearly summary HTML table."""
    if not yearly_returns:
        return "<p>No yearly data.</p>"

    rows = ["<tr><th>Year</th><th>Return</th><th>End Value (EUR)</th>"
            "<th>End Value (USD)</th><th>Dividends (EUR)</th></tr>"]

    for yr in yearly_returns:
        ret = yr.get("return_pct", 0)
        color = "#16a34a" if ret >= 0 else "#dc2626"
        rows.append(
            f"<tr>"
            f"<td>{yr['year']}</td>"
            f'<td style="color:{color};font-weight:600">{ret:+.1f}%</td>'
            f"<td>€{yr.get('value_eur', 0):,.0f}</td>"
            f"<td>${yr.get('value_usd', 0):,.0f}</td>"
            f"<td>€{yr.get('dividends_eur', 0):,.0f}</td>"
            f"</tr>"
        )

    return f'<table class="data-table">{"".join(rows)}</table>'


# ── Trade journal table ──────────────────────────────────────────────

def _trades_table(trades: List[dict]) -> str:
    """Generate trade journal HTML table."""
    if not trades:
        return "<p>No trades executed.</p>"

    rows = ["<tr><th>Date</th><th>Action</th><th>Symbol</th><th>Shares</th>"
            "<th>Price ($)</th><th>Value ($)</th><th>Value (€)</th><th>Reason</th></tr>"]

    for t in trades:
        action = t.get("action", "")
        icon = "🟢" if action == "BUY" else "🔴"
        action_class = "buy" if action == "BUY" else "sell"
        rows.append(
            f'<tr class="{action_class}">'
            f"<td>{t.get('date', '')}</td>"
            f"<td>{icon} {action}</td>"
            f"<td><strong>{t.get('symbol', '')}</strong></td>"
            f"<td>{t.get('shares', 0):.0f}</td>"
            f"<td>${t.get('price', 0):,.2f}</td>"
            f"<td>${t.get('value_usd', 0):,.0f}</td>"
            f"<td>€{t.get('value_eur', 0):,.0f}</td>"
            f"<td class='reason'>{t.get('reason', '')}</td>"
            f"</tr>"
        )

    return f'<table class="data-table trades-table">{"".join(rows)}</table>'


# ── Holdings table ───────────────────────────────────────────────────

def _holdings_table(holdings: List[dict]) -> str:
    """Generate final holdings HTML table."""
    if not holdings:
        return "<p>No open positions at end of period.</p>"

    rows = ["<tr><th>Symbol</th><th>Shares</th><th>Avg Cost</th>"
            "<th>Current</th><th>Value (€)</th><th>P&L</th><th>Weight</th></tr>"]

    for h in holdings:
        pnl = h.get("pnl_pct", 0)
        color = "#16a34a" if pnl >= 0 else "#dc2626"
        rows.append(
            f"<tr>"
            f"<td><strong>{h.get('symbol', '')}</strong></td>"
            f"<td>{h.get('shares', 0):.0f}</td>"
            f"<td>${h.get('avg_cost', 0):,.2f}</td>"
            f"<td>${h.get('current_price', 0):,.2f}</td>"
            f"<td>€{h.get('value_eur', 0):,.0f}</td>"
            f'<td style="color:{color};font-weight:600">{pnl:+.1f}%</td>'
            f"<td>{h.get('weight_pct', 0):.1f}%</td>"
            f"</tr>"
        )

    return f'<table class="data-table">{"".join(rows)}</table>'


# ── Benchmark comparison ─────────────────────────────────────────────

def _benchmark_table(portfolio_return: float, benchmarks: dict) -> str:
    """Generate benchmark comparison HTML table."""
    rows = ["<tr><th></th><th>Total Return</th><th>Annualized</th>"
            "<th>Max Drawdown</th><th>Alpha</th></tr>"]

    # Portfolio row
    color = "#16a34a" if portfolio_return >= 0 else "#dc2626"
    rows.append(
        f'<tr class="portfolio-row">'
        f'<td><strong>📊 Portfolio</strong></td>'
        f'<td style="color:{color};font-weight:700">{portfolio_return:+.1f}%</td>'
        f"<td>—</td><td>—</td><td>—</td></tr>"
    )

    for sym, data in benchmarks.items():
        ret = data.get("total_return_pct")
        ann = data.get("annualized_pct")
        dd = data.get("max_drawdown_pct")
        alpha = portfolio_return - ret if ret is not None else None

        color = "#16a34a" if (ret or 0) >= 0 else "#dc2626"
        alpha_color = "#16a34a" if (alpha or 0) >= 0 else "#dc2626"
        rows.append(
            f"<tr>"
            f"<td>{sym}</td>"
            f'<td style="color:{color}">{ret:+.1f}%</td>' if ret is not None else '<td>—</td>'
            f"<td>{ann:+.1f}%</td>" if ann is not None else "<td>—</td>"
            f"<td>{dd:.1f}%</td>" if dd is not None else "<td>—</td>"
            f'<td style="color:{alpha_color};font-weight:600">{alpha:+.1f}%</td>' if alpha is not None else "<td>—</td>"
            f"</tr>"
        )

    return f'<table class="data-table">{"".join(rows)}</table>'


# ── Cost breakdown table ─────────────────────────────────────────────

def _cost_breakdown_table(metrics: dict) -> str:
    """Generate friction cost breakdown HTML table."""
    spread = metrics.get("spread_cost_usd", 0)
    commission = metrics.get("commission_cost_usd", 0)
    div_tax = metrics.get("dividend_tax_usd", 0)
    cg_tax = metrics.get("capital_gains_tax_usd", 0)
    total = metrics.get("total_friction_usd", 0)
    total_eur = metrics.get("total_friction_eur", 0)

    if total <= 0:
        return "<p>No friction costs (all set to zero).</p>"

    rows = ["<tr><th>Cost Type</th><th>Amount (USD)</th><th>Notes</th></tr>"]
    if spread > 0:
        rows.append(f"<tr><td>Spread / Slippage</td><td>${spread:,.0f}</td>"
                    f"<td>Bid-ask spread on each buy &amp; sell</td></tr>")
    if commission > 0:
        rows.append(f"<tr><td>Broker Commission</td><td>${commission:,.0f}</td>"
                    f"<td>Per-trade commission</td></tr>")
    if div_tax > 0:
        rows.append(f"<tr><td>Dividend Withholding Tax</td><td>${div_tax:,.0f}</td>"
                    f"<td>Tax withheld on dividend payments</td></tr>")
    if cg_tax > 0:
        rows.append(f"<tr><td>Capital Gains Tax</td><td>${cg_tax:,.0f}</td>"
                    f"<td>Tax on realized profits (not losses)</td></tr>")
    rows.append(
        f'<tr style="font-weight:700;border-top:2px solid #334155">'
        f"<td>Total Friction</td><td>${total:,.0f}</td>"
        f"<td>≈ €{total_eur:,.0f}</td></tr>"
    )

    return f'<table class="data-table">{"".join(rows)}</table>'


# ── Parameters table ─────────────────────────────────────────────────

def _parameters_table(params: dict) -> str:
    """Generate strategy parameters HTML table."""
    labels = {
        "starting_cash": ("Starting Capital", lambda v: f"€{v:,.0f}"),
        "fund_buy_threshold": ("Fund. Buy Threshold", lambda v: f"≥ {v}"),
        "fund_sell_threshold": ("Fund. Sell Threshold", lambda v: f"< {v}"),
        "max_position_pct": ("Max Position Size", lambda v: f"{v*100:.0f}%"),
        "stop_loss_pct": ("Stop-Loss", lambda v: f"{v*100:.0f}%" if v > 0 else "Disabled"),
        "max_positions": ("Max Holdings", lambda v: f"{v}"),
        "tech_influence": ("Technical Influence", lambda v: f"{v*100:.0f}%"),
        "macro_influence": ("Macro Influence", lambda v: f"{v*100:.0f}%"),
        "eval_frequency": ("Eval Frequency", lambda v: v),
        "spread_pct": ("Spread / Slippage", lambda v: f"{v:.2f}%"),
        "dividend_tax_pct": ("Dividend Tax", lambda v: f"{v:.1f}%"),
        "capital_gains_tax_pct": ("Capital Gains Tax", lambda v: f"{v:.1f}%"),
        "commission_eur": ("Commission", lambda v: f"€{v:.2f}" if v > 0 else "None"),
    }

    rows = []
    for key, val in params.items():
        if key in labels:
            label, fmt = labels[key]
            rows.append(f"<tr><td>{label}</td><td><strong>{fmt(val)}</strong></td></tr>")

    return f'<table class="params-table">{"".join(rows)}</table>'


# ── Main report generator ───────────────────────────────────────────

def generate_html_report(data: dict) -> str:
    """Generate a complete self-contained HTML report.

    Parameters
    ----------
    data : dict with keys:
        title, period, parameters, tickers, metrics, equity_curve,
        monthly_returns, yearly_returns, benchmarks, trades, holdings
    """
    metrics = data.get("metrics", {})
    period = data.get("period", {})
    params = data.get("parameters", {})

    total_ret = metrics.get("total_return_pct", 0)
    ann_ret = metrics.get("annualized_return_pct", 0)
    max_dd = metrics.get("max_drawdown_pct", 0)
    sharpe = metrics.get("sharpe_ratio")
    total_divs_eur = metrics.get("total_dividends_eur", 0)
    win_rate = metrics.get("win_rate_pct")
    final_eur = metrics.get("final_value_eur", 0)
    final_usd = metrics.get("final_value_usd", 0)
    starting_eur = params.get("starting_cash", 0)
    total_trades = metrics.get("total_trades", 0)
    total_friction_eur = metrics.get("total_friction_eur", 0)
    tickers = data.get("tickers", [])
    strategy_note = data.get("strategy_note", "")

    ret_color = "#16a34a" if total_ret >= 0 else "#dc2626"
    ann_color = "#16a34a" if ann_ret >= 0 else "#dc2626"

    # Build chart
    chart_svg = _svg_equity_curve(
        data.get("equity_curve", []),
        data.get("benchmarks", {}),
    )

    # Build tables
    monthly_table = _monthly_returns_table(data.get("monthly_returns", []))
    yearly_table = _yearly_summary_table(data.get("yearly_returns", []))
    trades_html = _trades_table(data.get("trades", []))
    holdings_html = _holdings_table(data.get("holdings", []))
    benchmark_html = _benchmark_table(total_ret, data.get("benchmarks", {}))
    params_html = _parameters_table(params)
    cost_html = _cost_breakdown_table(metrics)

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{data.get('title', 'Backtest Report')}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #f8fafc; color: #1e293b; line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }}
  .header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    color: white; padding: 2.5rem 2rem; border-radius: 16px;
    margin-bottom: 2rem;
  }}
  .header h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 0.3rem; }}
  .header .subtitle {{ opacity: 0.85; font-size: 0.95rem; }}
  .header .period {{ opacity: 0.7; font-size: 0.85rem; margin-top: 0.5rem; }}

  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem; margin-bottom: 2rem;
  }}
  .kpi {{
    background: white; padding: 1.25rem 1.5rem; border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .kpi .label {{ font-size: 0.8rem; color: #64748b; text-transform: uppercase;
    letter-spacing: 0.05em; margin-bottom: 0.25rem; }}
  .kpi .value {{ font-size: 1.6rem; font-weight: 700; }}
  .kpi .sub {{ font-size: 0.8rem; color: #94a3b8; margin-top: 0.15rem; }}

  .section {{
    background: white; border-radius: 12px; padding: 1.5rem 2rem;
    margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .section h2 {{
    font-size: 1.1rem; font-weight: 600; color: #334155;
    margin-bottom: 1rem; padding-bottom: 0.5rem;
    border-bottom: 2px solid #e2e8f0;
  }}

  .strategy-note {{
    background: #eff6ff; border-left: 4px solid #2563eb;
    padding: 1rem 1.25rem; border-radius: 0 8px 8px 0;
    margin-bottom: 1.5rem; font-size: 0.9rem; color: #1e40af;
  }}

  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th {{ text-align: left; padding: 0.6rem 0.8rem; border-bottom: 2px solid #e2e8f0;
    color: #64748b; font-weight: 600; font-size: 0.78rem;
    text-transform: uppercase; letter-spacing: 0.04em; }}
  td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #f1f5f9; }}
  tr:hover td {{ background: #f8fafc; }}

  .monthly-table {{ font-size: 0.82rem; }}
  .monthly-table th {{ padding: 0.4rem 0.5rem; text-align: center; }}
  .monthly-table td {{ padding: 0.4rem 0.5rem; border-radius: 4px; }}
  .monthly-table .year-label {{ font-weight: 700; text-align: center;
    background: #f1f5f9 !important; }}

  .params-table td {{ padding: 0.4rem 0.8rem; }}
  .params-table td:first-child {{ color: #64748b; }}

  .portfolio-row td {{ background: #eff6ff !important; }}

  .trades-table .buy td:nth-child(2) {{ color: #16a34a; font-weight: 600; }}
  .trades-table .sell td:nth-child(2) {{ color: #dc2626; font-weight: 600; }}
  .trades-table .reason {{ font-size: 0.8rem; color: #64748b; max-width: 200px; }}

  .two-col {{ display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; }}
  @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  .footer {{
    text-align: center; color: #94a3b8; font-size: 0.78rem;
    margin-top: 2rem; padding: 1rem;
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>{data.get('title', 'Backtest Report')}</h1>
    <div class="subtitle">Long-term investor strategy · {len(tickers)} stocks</div>
    <div class="period">{period.get('start', '')} → {period.get('end', '')} · Generated {generated}</div>
  </div>

  {"<div class='strategy-note'>" + strategy_note + "</div>" if strategy_note else ""}

  <div class="kpi-grid">
    <div class="kpi">
      <div class="label">Total Return</div>
      <div class="value" style="color:{ret_color}">{total_ret:+.1f}%</div>
      <div class="sub">{ann_ret:+.1f}% annualized</div>
    </div>
    <div class="kpi">
      <div class="label">Final Value</div>
      <div class="value">€{final_eur:,.0f}</div>
      <div class="sub">${final_usd:,.0f} USD</div>
    </div>
    <div class="kpi">
      <div class="label">Max Drawdown</div>
      <div class="value" style="color:#dc2626">-{max_dd:.1f}%</div>
      <div class="sub">Peak to trough</div>
    </div>
    <div class="kpi">
      <div class="label">Sharpe Ratio</div>
      <div class="value">{sharpe:.2f}</div>
      <div class="sub">Risk-adjusted return</div>
    </div>
    <div class="kpi">
      <div class="label">Total Dividends</div>
      <div class="value">€{total_divs_eur:,.0f}</div>
      <div class="sub">{total_trades} trades · {f"{win_rate:.0f}% win rate" if win_rate else "—"}</div>
    </div>
    <div class="kpi">
      <div class="label">Starting Capital</div>
      <div class="value">€{starting_eur:,.0f}</div>
      <div class="sub">Gain: €{final_eur - starting_eur:+,.0f}</div>
    </div>
    <div class="kpi">
      <div class="label">Friction Costs</div>
      <div class="value" style="color:#dc2626">€{total_friction_eur:,.0f}</div>
      <div class="sub">{total_friction_eur / starting_eur * 100:.1f}% of capital</div>
    </div>
  </div>

  <div class="section">
    <h2>📈 Equity Curve (indexed to 100)</h2>
    {chart_svg}
  </div>

  <div class="section">
    <h2>📅 Monthly Returns</h2>
    {monthly_table}
  </div>

  <div class="two-col">
    <div class="section">
      <h2>📊 Yearly Summary</h2>
      {yearly_table}
    </div>
    <div class="section">
      <h2>⚙️ Parameters</h2>
      {params_html}
    </div>
  </div>

  <div class="section">
    <h2>🏁 Benchmark Comparison</h2>
    {benchmark_html}
  </div>

  <div class="section">
    <h2>💰 Cost of Active Investing</h2>
    <p style="color:#64748b;font-size:0.88rem;margin-bottom:1rem">
      These are the friction costs deducted during the simulation.
      A cheap accumulating index ETF (e.g. VWCE) has none of these costs —
      dividends are reinvested tax-free, no spread on rebalancing, no capital gains until you sell.
    </p>
    {cost_html}
  </div>

  <div class="section">
    <h2>💼 Final Holdings</h2>
    {holdings_html}
  </div>

  <div class="section">
    <h2>📝 Trade Journal</h2>
    {trades_html}
  </div>

  <div class="footer">
    Stock Screener · Backtest Report · {generated}<br>
    Past performance does not guarantee future results. Fundamental scores use current data (look-ahead bias).
  </div>

</div>
</body>
</html>"""

    return html


def save_report(html: str, filepath: str) -> str:
    """Save HTML report to file. Returns the absolute path."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(filepath)
