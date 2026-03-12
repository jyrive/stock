"""Parameter correlation study — find which features predict forward returns.

Builds a historical dataset across many tickers by computing technical + macro
features at regular intervals, then measuring forward returns. Uses Random Forest
to rank feature importance and shows how fundamental, technical, and macro
interact.

Usage:
    python stock.py study                  # full study, default universe
    python stock.py study --tickers 50     # larger universe (slower)
    python stock.py study --period 3y      # longer history
    python stock.py study --quick          # fast mode, fewer tickers

Approach:
    1. Fundamental data: use CURRENT fundamentals (only 4 annual periods available
       from yfinance — can't reconstruct historical fundamental snapshots).
       This introduces look-ahead bias, but fundamentals change slowly.
    2. Technical data: FULLY historical — computed from past price data at
       each evaluation point.  No look-ahead bias.
    3. Macro data: FULLY historical — computed from past index/VIX data at
       each evaluation point.  No look-ahead bias.
    4. Target: forward 1-month, 3-month, and 6-month returns.
    5. ML: Random Forest feature importance + correlation analysis.

Key questions answered:
    - Which individual features predict forward returns best?
    - Does technical timing improve results for fundamentally strong stocks?
    - Which macro conditions create the best entry points?
    - What is the optimal weighting of fundamental vs technical vs macro?
"""

import sys
import os
import math
from datetime import datetime, timedelta, date
from collections import defaultdict

import numpy as np
import pandas as pd
from datasources.market import get_price_history, get_info, get_macro_history

from analysis.technical import rsi, sma, bollinger_bands, week52_position, macd

def _nan(val):
    """Convert None to np.nan for ML feature pipelines."""
    return np.nan if val is None else val

# ═══════════════════════════════════════════════════════════════════════
#  Stock universe
# ═══════════════════════════════════════════════════════════════════════

# Diverse, liquid US stocks across sectors (not cherry-picked for performance)
_DEFAULT_UNIVERSE = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "ADBE", "CRM", "ORCL", "INTC",
    # Health
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "AMGN", "BMY", "GILD", "EXEL",
    # Finance
    "JPM", "BAC", "GS", "MS", "BLK", "V", "MA", "AXP", "EVR", "SCHW",
    # Industrial
    "CAT", "HON", "GE", "MMM", "RTX", "LMT", "DE", "UPS", "CSL", "ALSN",
    # Consumer
    "AMZN", "HD", "MCD", "NKE", "COST", "WMT", "PG", "KO", "PEP", "SBUX",
    # Energy/Materials
    "XOM", "CVX", "SLB", "GFI", "NEM", "FCX", "APD", "LIN", "ECL", "DOW",
]

# Macro indicators to fetch
_MACRO_TICKERS = [
    "^GSPC", "^STOXX", "^N225", "EEM", "^VIX", "^TNX", "2YY=F",
    "DX-Y.NYB", "GC=F", "CL=F", "HG=F",
]

# ═══════════════════════════════════════════════════════════════════════
#  Technical feature computation (from historical closes, no bias)
# ═══════════════════════════════════════════════════════════════════════

def compute_tech_features(closes):
    """Compute all technical features from a close price array.

    Returns dict of feature_name → value.  All can be nan if not enough data.
    """
    price = closes[-1] if len(closes) > 0 else np.nan
    sma50 = _nan(sma(closes, 50))
    sma200 = _nan(sma(closes, 200))

    # Bollinger band position (0-1)
    bands = bollinger_bands(closes)
    if bands[0] is None:
        bb_pos = np.nan
    else:
        lower, _, upper = bands
        bb_pos = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5

    # MACD histogram
    macd_result = macd(closes)
    macd_hist = macd_result["histogram"] if macd_result else np.nan

    return {
        "rsi_14": _nan(rsi(closes)),
        "price_vs_sma50_pct": ((price - sma50) / sma50 * 100) if not np.isnan(sma50) and sma50 > 0 else np.nan,
        "price_vs_sma200_pct": ((price - sma200) / sma200 * 100) if not np.isnan(sma200) and sma200 > 0 else np.nan,
        "bb_position": bb_pos,
        "week52_position": _nan(week52_position(closes)),
        "macd_histogram": macd_hist,
        "volatility_20d": float(np.std(np.diff(np.log(closes[-21:])), ddof=1) * np.sqrt(252))
            if len(closes) >= 22 else np.nan,
        "momentum_1m": (closes[-1] / closes[-21] - 1) * 100 if len(closes) >= 22 else np.nan,
        "momentum_3m": (closes[-1] / closes[-63] - 1) * 100 if len(closes) >= 64 else np.nan,
    }

# ═══════════════════════════════════════════════════════════════════════
#  Macro feature computation (from historical index data, no bias)
# ═══════════════════════════════════════════════════════════════════════

def compute_macro_features(macro_histories, eval_idx):
    """Compute macro features at a given index position in the macro data.

    macro_histories: dict of ticker → full close array
    eval_idx: integer index into the date array (how far into the data)
    """
    feats = {}

    def _get(ticker, length=None):
        if ticker not in macro_histories:
            return None
        arr = macro_histories[ticker]
        if length:
            return arr[:eval_idx + 1][-length:] if eval_idx + 1 >= length else arr[:eval_idx + 1]
        return arr[:eval_idx + 1]

    # VIX
    vix_closes = _get("^VIX")
    feats["vix"] = float(vix_closes[-1]) if vix_closes is not None and len(vix_closes) > 0 else np.nan

    # S&P 500 vs 200-MA
    sp = _get("^GSPC")
    if sp is not None and len(sp) > 0:
        sma200 = np.mean(sp[-200:]) if len(sp) >= 200 else np.mean(sp)
        feats["sp500_vs_200ma_pct"] = (sp[-1] / sma200 - 1) * 100
        lo, hi = np.min(sp[-252:] if len(sp) >= 252 else sp), np.max(sp[-252:] if len(sp) >= 252 else sp)
        feats["sp500_52w_pos"] = (sp[-1] - lo) / (hi - lo) * 100 if hi != lo else 50
    else:
        feats["sp500_vs_200ma_pct"] = np.nan
        feats["sp500_52w_pos"] = np.nan

    # 10Y yield
    tnx = _get("^TNX")
    feats["yield_10y"] = float(tnx[-1]) if tnx is not None and len(tnx) > 0 else np.nan

    # 2Y yield + spread
    t2y = _get("2YY=F")
    if tnx is not None and t2y is not None and len(tnx) > 0 and len(t2y) > 0:
        feats["yield_2y"] = float(t2y[-1])
        feats["yield_spread"] = float(tnx[-1]) - float(t2y[-1])
    else:
        feats["yield_2y"] = np.nan
        feats["yield_spread"] = np.nan

    # USD index
    usd = _get("DX-Y.NYB")
    feats["usd_index"] = float(usd[-1]) if usd is not None and len(usd) > 0 else np.nan

    # Gold
    gold = _get("GC=F")
    if gold is not None and len(gold) > 0:
        feats["gold_vs_200ma"] = (gold[-1] / np.mean(gold[-200:] if len(gold) >= 200 else gold) - 1) * 100
    else:
        feats["gold_vs_200ma"] = np.nan

    # Oil
    oil = _get("CL=F")
    if oil is not None and len(oil) > 0:
        feats["oil_vs_200ma"] = (oil[-1] / np.mean(oil[-200:] if len(oil) >= 200 else oil) - 1) * 100
    else:
        feats["oil_vs_200ma"] = np.nan

    # Global breadth: how many major indices above their 200-MA
    breadth_above = 0
    breadth_total = 0
    for idx_ticker in ["^GSPC", "^STOXX", "^N225", "EEM"]:
        arr = _get(idx_ticker)
        if arr is not None and len(arr) > 50:
            sma = np.mean(arr[-200:] if len(arr) >= 200 else arr)
            breadth_total += 1
            if arr[-1] >= sma:
                breadth_above += 1
    feats["breadth_pct"] = breadth_above / breadth_total * 100 if breadth_total > 0 else 50

    return feats

# ═══════════════════════════════════════════════════════════════════════
#  Fundamental features (current — look-ahead bias acknowledged)
# ═══════════════════════════════════════════════════════════════════════

def fetch_fundamentals(ticker_sym):
    """Fetch current fundamental features for a ticker. Returns dict or None."""
    try:
        info = get_info(ticker_sym) or {}
        return _info_to_features(info)
    except Exception:
        return None

def _info_to_features(info):
    """Extract ML features from a yfinance info dict (or datastore snapshot)."""
    if not info:
        return None

    feats = {
        "market_cap_b": info.get("marketCap", 0) / 1e9 if info.get("marketCap") else
                        info.get("market_cap") if info.get("market_cap") else np.nan,
        "trailing_pe": info.get("trailingPE", info.get("trailing_pe", np.nan)),
        "forward_pe": info.get("forwardPE", info.get("forward_pe", np.nan)),
        "roe_pct": _safe_pct(info, "returnOnEquity", "roe_pct"),
        "debt_to_equity": info.get("debtToEquity", info.get("debt_to_equity", np.nan)),
        "current_ratio": info.get("currentRatio", info.get("current_ratio", np.nan)),
        "dividend_yield_pct": _safe_pct(info, "dividendYield", "dividend_yield"),
        "payout_ratio_pct": _safe_pct(info, "payoutRatio", "payout_ratio"),
        "profit_margin_pct": _safe_pct(info, "profitMargins", "profit_margin"),
        "revenue_growth_pct": _safe_pct(info, "revenueGrowth", "revenue_growth"),
        "earnings_growth_pct": _safe_pct(info, "earningsGrowth", "earnings_growth"),
        "fcf_yield_pct": np.nan,
        "price_to_book": info.get("priceToBook", info.get("price_to_book", np.nan)),
        "price_to_sales": info.get("priceToSalesTrailing12Months", info.get("price_to_sales", np.nan)),
        "beta": info.get("beta", np.nan),
    }

    # FCF yield from yfinance info
    fcf = info.get("freeCashflow")
    mc = info.get("marketCap")
    if fcf and mc and mc > 0:
        feats["fcf_yield_pct"] = fcf / mc * 100
    elif info.get("fcf_yield") is not None:
        feats["fcf_yield_pct"] = info["fcf_yield"]

    # Sector encoding
    sector_map = {
        "Technology": 0, "Healthcare": 1, "Financial Services": 2,
        "Industrials": 3, "Consumer Cyclical": 4, "Consumer Defensive": 5,
        "Energy": 6, "Basic Materials": 7, "Communication Services": 8,
        "Real Estate": 9, "Utilities": 10,
    }
    sector_str = info.get("sector", "")
    feats["sector_code"] = sector_map.get(sector_str, -1)

    return feats

def _safe_pct(info, yf_key, snap_key=None):
    """Get a percentage value, handling both yfinance (0-1) and snapshot (already %) formats."""
    val = info.get(yf_key)
    if val is not None:
        return float(val) * 100
    if snap_key and info.get(snap_key) is not None:
        return float(info[snap_key])  # already in % from datastore
    return 0.0

# ═══════════════════════════════════════════════════════════════════════
#  Dataset builder — uses cached data when available
# ═══════════════════════════════════════════════════════════════════════

def _load_snapshot_history(symbol):
    """Load all fundamental snapshots for a ticker from the datastore.

    Returns list of (date_str, features_dict) sorted by date, or empty list.
    """
    try:
        from utils.snapshot_db import get_fundamental_history
        snapshots = get_fundamental_history(symbol)
        if not snapshots:
            return []

        result = []
        for snap in snapshots:
            # Try to parse from stored info_json first (richest data)
            info_json = snap.get("info_json")
            if info_json:
                try:
                    import json
                    info = json.loads(info_json)
                    feats = _info_to_features(info)
                except Exception:
                    feats = _info_to_features(snap)  # fallback to column data
            else:
                feats = _info_to_features(snap)

            if feats:
                result.append((snap["snapshot_date"], feats))

        return result
    except Exception:
        return []

def _get_pit_fundamentals(symbol, eval_date_str, snapshot_history, current_fundamentals):
    """Get point-in-time fundamentals for a ticker at a given date.

    Uses the most recent snapshot on or before eval_date_str.
    Falls back to current fundamentals if no snapshots available.

    Returns (features_dict, is_point_in_time).
    """
    if snapshot_history:
        # Find most recent snapshot on or before eval_date
        best = None
        for snap_date, feats in snapshot_history:
            if snap_date <= eval_date_str:
                best = feats
            else:
                break
        if best is not None:
            return best, True

    # Fallback to current (look-ahead bias)
    return current_fundamentals or {}, False

def build_dataset(tickers, period_years=2, eval_interval_days=21):
    """Build the full feature + forward-return dataset.

    For each ticker, at each evaluation point:
        - compute technical features from historical closes (no bias)
        - compute macro features from historical index data (no bias)
        - use point-in-time fundamentals when available (from datastore)
        - fall back to current fundamentals if no snapshots exist
        - compute forward returns (1m, 3m, 6m)

    Also caches all fetched data to the datastore for future use.

    Returns a pandas DataFrame.
    """
    from utils.snapshot_db import save_prices, save_macro, save_fundamental_snapshot

    print(f"\n  Building dataset: {len(tickers)} tickers × {period_years}y history")
    print(f"  Evaluation interval: {eval_interval_days} trading days (~monthly)\n")

    # ── Load snapshot history from datastore ────────────────────
    print(f"  Loading point-in-time fundamental snapshots...")
    snapshot_histories = {}
    pit_tickers = 0
    for sym in tickers:
        hist = _load_snapshot_history(sym)
        if hist:
            snapshot_histories[sym] = hist
            pit_tickers += 1
    if pit_tickers > 0:
        total_snaps = sum(len(h) for h in snapshot_histories.values())
        print(f"  ✓ Found snapshots for {pit_tickers}/{len(tickers)} tickers ({total_snaps} total snapshots)")
    else:
        print(f"  ⚠ No snapshots found — using current fundamentals (look-ahead bias)")
        print(f"    Run 'python stock.py collect --backfill' to start building history")

    # ── Fetch all price histories ─────────────────────────────────
    period_str = f"{period_years + 1}y"  # extra year for look-back
    print(f"\n  Fetching price histories ({period_str})...")

    stock_data = {}
    for i, sym in enumerate(tickers):
        try:
            h = get_price_history(sym, period=period_str)
            if h is not None and len(h) >= 200:
                stock_data[sym] = {
                    "closes": h["Close"].values.astype(float),
                    "dates": h.index,
                }
                # Cache prices
                try:
                    save_prices(sym, h)
                except Exception:
                    pass
            else:
                print(f"    ⚠ {sym}: insufficient data ({len(h) if h is not None else 0} days)")
        except Exception as e:
            print(f"    ⚠ {sym}: {e}")
        if (i + 1) % 10 == 0:
            print(f"    ... {i + 1}/{len(tickers)} tickers")

    print(f"  Got price data for {len(stock_data)} tickers")

    # ── Fetch macro histories ─────────────────────────────────────
    print(f"  Fetching macro indicator histories...")
    macro_histories = {}
    macro_dates = {}
    for sym in _MACRO_TICKERS:
        try:
            h = get_macro_history(sym, period=period_str)
            if h is not None and len(h) >= 50:
                macro_histories[sym] = h["Close"].values.astype(float)
                macro_dates[sym] = h.index
                # Cache macro data
                try:
                    save_macro(sym, h)
                except Exception:
                    pass
        except Exception:
            pass
    print(f"  Got macro data for {len(macro_histories)} indicators")

    # ── Fetch fundamentals (current — fallback for tickers without snapshots) ──
    tickers_needing_current = [sym for sym in stock_data if sym not in snapshot_histories]
    if tickers_needing_current:
        print(f"  Fetching current fundamentals for {len(tickers_needing_current)} tickers (no snapshots)...")
        fund_data = {}
        for i, sym in enumerate(tickers_needing_current):
            fd = fetch_fundamentals(sym)
            if fd:
                fund_data[sym] = fd
                # Also snapshot it for next time
                try:
                    save_fundamental_snapshot(sym, get_info(sym))
                except Exception:
                    pass
            if (i + 1) % 10 == 0:
                print(f"    ... {i + 1}/{len(tickers_needing_current)} tickers")
        print(f"  Got fundamental data for {len(fund_data)} tickers")
    else:
        fund_data = {}
        print(f"  ✓ All tickers have point-in-time snapshots — no current fetch needed")

    # ── Build feature rows ────────────────────────────────────────
    print(f"\n  Computing features at each evaluation point...")
    rows = []
    pit_count = 0
    current_count = 0

    for sym, sd in stock_data.items():
        closes = sd["closes"]
        dates = sd["dates"]
        n = len(closes)

        # Start evaluating after 252 trading days (1 year look-back)
        # Stop with 126 days left (need 6 months forward returns)
        start_idx = min(252, n - 130)
        if start_idx < 50:
            continue

        eval_points = range(start_idx, n - 126, eval_interval_days)
        snap_hist = snapshot_histories.get(sym, [])

        for idx in eval_points:
            hist_closes = closes[:idx + 1]
            price_now = closes[idx]

            # Get eval date string for point-in-time lookup
            eval_date_str = dates[idx].strftime("%Y-%m-%d") if hasattr(dates[idx], "strftime") else str(dates[idx])[:10]

            # Forward returns
            fwd_1m = (closes[min(idx + 21, n - 1)] / price_now - 1) * 100
            fwd_3m = (closes[min(idx + 63, n - 1)] / price_now - 1) * 100
            fwd_6m = (closes[min(idx + 126, n - 1)] / price_now - 1) * 100

            # Technical features (pure historical — no bias)
            tech = compute_tech_features(hist_closes)

            # Macro features (pure historical — no bias)
            macro_idx = min(idx, len(macro_histories.get("^GSPC", [])) - 1)
            macro = compute_macro_features(macro_histories, macro_idx)

            # Fundamentals — point-in-time when available
            fund, is_pit = _get_pit_fundamentals(sym, eval_date_str, snap_hist, fund_data.get(sym))
            if is_pit:
                pit_count += 1
            else:
                current_count += 1

            row = {
                "symbol": sym,
                "eval_idx": idx,
                "eval_date": eval_date_str,
                "price": price_now,
                "fwd_return_1m": fwd_1m,
                "fwd_return_3m": fwd_3m,
                "fwd_return_6m": fwd_6m,
                "fund_pit": 1 if is_pit else 0,
            }
            row.update({f"tech_{k}": v for k, v in tech.items()})
            row.update({f"macro_{k}": v for k, v in macro.items()})
            row.update({f"fund_{k}": v for k, v in fund.items()})

            rows.append(row)

    df = pd.DataFrame(rows)
    print(f"  Dataset: {len(df)} observations × {len(df.columns)} columns")
    print(f"  Tickers with data: {df['symbol'].nunique()}")

    # Report data quality
    if pit_count > 0:
        total_obs = pit_count + current_count
        pit_pct = pit_count / total_obs * 100
        print(f"  Fundamental data quality:")
        print(f"    Point-in-time (unbiased):  {pit_count:>5d} ({pit_pct:.0f}%)")
        print(f"    Current snapshot (biased):  {current_count:>5d} ({100 - pit_pct:.0f}%)")
    else:
        print(f"  ⚠ All fundamental data is current (look-ahead bias)")

    return df

# ═══════════════════════════════════════════════════════════════════════
#  Analysis: Feature importance with Random Forest
# ═══════════════════════════════════════════════════════════════════════

def analyze_feature_importance(df, target="fwd_return_3m"):
    """Run Random Forest to rank feature importance for predicting forward returns.

    Returns:
        importances: sorted list of (feature_name, importance, direction)
        model_score: R² score on test set
    """
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    # Select feature columns
    feature_cols = [c for c in df.columns if c.startswith(("tech_", "macro_", "fund_"))
                    and c != "fund_sector_code"]
    feature_cols = [c for c in feature_cols if df[c].notna().sum() > len(df) * 0.5]

    X = df[feature_cols].copy()
    y = df[target].copy()

    # Drop rows with too many NaN
    mask = X.notna().sum(axis=1) >= len(feature_cols) * 0.7
    X = X[mask]
    y = y[mask]

    # Fill remaining NaN with median
    X = X.fillna(X.median())

    if len(X) < 50:
        print(f"  ⚠ Only {len(X)} usable observations — too few for reliable ML")
        return [], 0, None, feature_cols

    print(f"\n  ── Random Forest Feature Importance (target: {target}) ──")
    print(f"  Observations: {len(X)}, Features: {len(feature_cols)}")

    # Random Forest
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
    )

    # Cross-validated R²
    scores = cross_val_score(rf, X, y, cv=5, scoring="r2")
    mean_r2 = np.mean(scores)
    print(f"  Cross-validated R²: {mean_r2:.3f} (±{np.std(scores):.3f})")

    # Fit on full data for importances
    rf.fit(X, y)

    # Feature importances
    imp = list(zip(feature_cols, rf.feature_importances_))
    imp.sort(key=lambda x: x[1], reverse=True)

    # Correlations (for direction)
    correlations = {}
    for col in feature_cols:
        valid = df[[col, target]].dropna()
        if len(valid) > 10:
            correlations[col] = np.corrcoef(valid[col], valid[target])[0, 1]

    results = []
    for feat, importance in imp:
        corr = correlations.get(feat, 0)
        direction = "+" if corr > 0 else "−"
        results.append((feat, importance, direction, corr))

    return results, mean_r2, rf, feature_cols

# ═══════════════════════════════════════════════════════════════════════
#  Analysis: Correlation matrix
# ═══════════════════════════════════════════════════════════════════════

def analyze_correlations(df, target="fwd_return_3m"):
    """Compute correlations between all features and forward returns."""
    feature_cols = [c for c in df.columns if c.startswith(("tech_", "macro_", "fund_"))]
    targets = ["fwd_return_1m", "fwd_return_3m", "fwd_return_6m"]

    correlations = []
    for col in feature_cols:
        for tgt in targets:
            valid = df[[col, tgt]].dropna()
            if len(valid) > 20:
                r = np.corrcoef(valid[col], valid[tgt])[0, 1]
                correlations.append({
                    "feature": col,
                    "target": tgt,
                    "correlation": r,
                    "abs_correlation": abs(r),
                    "n": len(valid),
                })

    corr_df = pd.DataFrame(correlations)
    return corr_df

# ═══════════════════════════════════════════════════════════════════════
#  Analysis: Layer interaction study
# ═══════════════════════════════════════════════════════════════════════

def _add_composite_scores(df):
    """Add composite scores for each layer to the DataFrame (in place)."""
    # Technical: lower RSI + below 200 MA + low BB position → better entry
    df["tech_composite"] = (
        (100 - df["tech_rsi_14"].fillna(50)) / 100 * 0.3 +
        (-df["tech_price_vs_sma200_pct"].fillna(0).clip(-20, 20) + 20) / 40 * 0.3 +
        (1 - df["tech_bb_position"].fillna(0.5)) * 0.2 +
        (1 - df["tech_week52_position"].fillna(0.5)) * 0.2
    ) * 100

    # Macro: high VIX = opportunity, S&P below 200 MA = opportunity
    df["macro_composite"] = 0
    if "macro_vix" in df.columns:
        df["macro_composite"] += df["macro_vix"].fillna(18).clip(10, 40) / 40 * 25
    if "macro_sp500_vs_200ma_pct" in df.columns:
        df["macro_composite"] += (-df["macro_sp500_vs_200ma_pct"].fillna(0).clip(-20, 20) + 20) / 40 * 25
    if "macro_yield_spread" in df.columns:
        spread = df["macro_yield_spread"].fillna(0.5)
        df["macro_composite"] += np.where(
            (spread >= 0.3) & (spread <= 1.5), 20,
            np.where(spread > 1.5, 10, np.where(spread >= 0, 8, 2))
        )
    if "macro_breadth_pct" in df.columns:
        df["macro_composite"] += (100 - df["macro_breadth_pct"].fillna(50)) / 100 * 15

    # Fund: use ROE, FCF yield, profit margin as quality proxies
    df["fund_composite"] = 0
    fund_features = {
        "fund_roe_pct": (0, 40, 0.25),
        "fund_fcf_yield_pct": (-5, 15, 0.20),
        "fund_profit_margin_pct": (-10, 40, 0.20),
        "fund_revenue_growth_pct": (-20, 50, 0.15),
        "fund_current_ratio": (0.5, 3, 0.10),
        "fund_earnings_growth_pct": (-30, 50, 0.10),
    }
    for col, (lo, hi, wt) in fund_features.items():
        if col in df.columns:
            normalized = (df[col].fillna((lo + hi) / 2).clip(lo, hi) - lo) / (hi - lo)
            df["fund_composite"] += normalized * wt * 100

    return df

def analyze_layer_interaction(df):
    """Study how fundamental, technical, and macro layers interact.

    Tests: do stocks with good fundamentals AND good technicals outperform
    stocks with only one layer favorable?

    Returns a summary dict with group returns.
    """
    df = df.copy()
    _add_composite_scores(df)

    # Group by layer quality
    results = {}
    for target in ["fwd_return_1m", "fwd_return_3m", "fwd_return_6m"]:
        groups = {}

        # Quintile analysis for each composite
        for layer_name, col in [("Fund", "fund_composite"), ("Tech", "tech_composite"), ("Macro", "macro_composite")]:
            if col in df.columns and df[col].notna().sum() > 20:
                try:
                    df[f"{col}_q"] = pd.qcut(df[col], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")
                    quintile_means = df.groupby(f"{col}_q", observed=True)[target].mean()
                    groups[layer_name] = {
                        "Q1_bottom": round(float(quintile_means.iloc[0]), 2) if len(quintile_means) > 0 else None,
                        "Q5_top": round(float(quintile_means.iloc[-1]), 2) if len(quintile_means) > 0 else None,
                        "spread": round(float(quintile_means.iloc[-1] - quintile_means.iloc[0]), 2) if len(quintile_means) > 1 else None,
                    }
                except Exception:
                    groups[layer_name] = {"Q1_bottom": None, "Q5_top": None, "spread": None}

        # Interaction: combo of layers
        try:
            fund_med = df["fund_composite"].median()
            tech_med = df["tech_composite"].median()
            macro_med = df["macro_composite"].median()

            conditions = {
                "All 3 layers favorable": (df["fund_composite"] >= fund_med) & (df["tech_composite"] >= tech_med) & (df["macro_composite"] >= macro_med),
                "Fund+Tech (macro weak)": (df["fund_composite"] >= fund_med) & (df["tech_composite"] >= tech_med) & (df["macro_composite"] < macro_med),
                "Fund only (tech+macro weak)": (df["fund_composite"] >= fund_med) & (df["tech_composite"] < tech_med) & (df["macro_composite"] < macro_med),
                "Tech only (fund+macro weak)": (df["fund_composite"] < fund_med) & (df["tech_composite"] >= tech_med) & (df["macro_composite"] < macro_med),
                "No layers favorable": (df["fund_composite"] < fund_med) & (df["tech_composite"] < tech_med) & (df["macro_composite"] < macro_med),
            }

            combos = {}
            for label, mask in conditions.items():
                subset = df[mask][target]
                if len(subset) > 5:
                    combos[label] = {
                        "mean_return": round(float(subset.mean()), 2),
                        "median_return": round(float(subset.median()), 2),
                        "count": len(subset),
                        "positive_pct": round((subset > 0).sum() / len(subset) * 100, 1),
                    }
            groups["combinations"] = combos
        except Exception:
            pass

        results[target] = groups

    return results

# ═══════════════════════════════════════════════════════════════════════
#  Analysis: Optimal weighting
# ═══════════════════════════════════════════════════════════════════════

def analyze_weight_optimization(df, target="fwd_return_3m"):
    """Grid search for optimal fund/tech/macro weighting.

    Tests different blends of the three composite scores and measures
    which weighting best predicts forward returns.
    """
    df = df.copy()
    if "fund_composite" not in df.columns:
        _add_composite_scores(df)

    # Normalize composites to 0-1
    dfc = df[["fund_composite", "tech_composite", "macro_composite", target]].dropna()
    if len(dfc) < 50:
        return {}

    for col in ["fund_composite", "tech_composite", "macro_composite"]:
        mn, mx = dfc[col].min(), dfc[col].max()
        if mx > mn:
            dfc[col] = (dfc[col] - mn) / (mx - mn)

    best_corr = -999
    best_weights = (0.33, 0.33, 0.34)
    results = []

    # Grid search in 10% increments
    for fw in range(0, 11):
        for tw in range(0, 11 - fw):
            mw = 10 - fw - tw
            wf = fw / 10
            wt = tw / 10
            wm = mw / 10

            combo = dfc["fund_composite"] * wf + dfc["tech_composite"] * wt + dfc["macro_composite"] * wm
            corr = np.corrcoef(combo, dfc[target])[0, 1]

            results.append({
                "fund_weight": wf, "tech_weight": wt, "macro_weight": wm,
                "correlation": corr,
            })
            if corr > best_corr:
                best_corr = corr
                best_weights = (wf, wt, wm)

    results_df = pd.DataFrame(results).sort_values("correlation", ascending=False)
    return {
        "best_weights": best_weights,
        "best_correlation": best_corr,
        "top_10": results_df.head(10).to_dict("records"),
        "current_weights": (0.70, 0.15, 0.15),  # approximate current system
        "current_corr": results_df[
            (results_df["fund_weight"].round(1) == 0.7) &
            (results_df["tech_weight"].round(1) == 0.2) &
            (results_df["macro_weight"].round(1) == 0.1)
        ]["correlation"].values[0] if len(results_df[
            (results_df["fund_weight"].round(1) == 0.7) &
            (results_df["tech_weight"].round(1) == 0.2) &
            (results_df["macro_weight"].round(1) == 0.1)
        ]) > 0 else None,
    }

# ═══════════════════════════════════════════════════════════════════════
#  Output: Terminal report
# ═══════════════════════════════════════════════════════════════════════

def print_report(df, importance_results, corr_df, interactions, weights, model_r2):
    """Print comprehensive terminal report."""
    G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; W = "\033[0m"; BOLD = "\033[1m"

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║       PARAMETER CORRELATION STUDY                          ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")

    # ── Dataset summary ──
    print(f"  {BOLD}Dataset Summary{W}")
    print(f"  Observations:  {len(df):,}")
    print(f"  Tickers:       {df['symbol'].nunique()}")
    print(f"  Features:      {len([c for c in df.columns if c.startswith(('tech_', 'macro_', 'fund_'))])}")
    print(f"  Model R²:      {model_r2:.3f}  (cross-validated, 3-month forward return)")
    print()

    # Interpret R²
    if model_r2 > 0.15:
        print(f"  {G}→ R² > 0.15 — features have meaningful predictive power{W}")
    elif model_r2 > 0.05:
        print(f"  {Y}→ R² = {model_r2:.3f} — weak but real signal; noisy markets are hard to predict{W}")
    else:
        print(f"  {R}→ R² = {model_r2:.3f} — limited predictive power; be cautious with over-fitting{W}")
    print()

    # ── Feature importance top 20 ──
    importances, _, _, _ = importance_results
    print(f"  {BOLD}Top 20 Features (Random Forest Importance){W}")
    print(f"  {'Rank':>4s}  {'Feature':35s}  {'Importance':>10s}  {'Corr':>6s}  {'Direction':>9s}")
    print(f"  {'─' * 75}")

    for i, (feat, imp, direction, corr) in enumerate(importances[:20]):
        layer = feat.split("_")[0].upper()
        layer_color = B if layer == "TECH" else (G if layer == "FUND" else Y)
        bar = "█" * int(imp * 200)
        print(f"  {i + 1:>3d}.  {layer_color}{feat:35s}{W}  {imp:>10.4f}  {corr:>+6.3f}  {direction:>4s}  {bar}")

    # ── Layer breakdown ──
    print(f"\n  {BOLD}Importance by Layer{W}")
    layer_sums = {"tech": 0, "macro": 0, "fund": 0}
    for feat, imp, _, _ in importances:
        layer = feat.split("_")[0]
        if layer in layer_sums:
            layer_sums[layer] += imp

    total = sum(layer_sums.values()) or 1
    for layer, s in sorted(layer_sums.items(), key=lambda x: -x[1]):
        pct = s / total * 100
        bar = "█" * int(pct / 2)
        color = B if layer == "tech" else (G if layer == "fund" else Y)
        print(f"  {color}{layer.upper():10s}{W}  {pct:5.1f}%  {bar}")

    # ── Strongest correlations ──
    if corr_df is not None and len(corr_df) > 0:
        print(f"\n  {BOLD}Strongest Correlations with Forward Returns{W}")
        for target in ["fwd_return_1m", "fwd_return_3m", "fwd_return_6m"]:
            subset = corr_df[corr_df["target"] == target].sort_values("abs_correlation", ascending=False).head(5)
            horizon = {"fwd_return_1m": "1-month", "fwd_return_3m": "3-month", "fwd_return_6m": "6-month"}[target]
            print(f"\n  {horizon}:")
            for _, row in subset.iterrows():
                c = row["correlation"]
                color = G if c > 0 else R
                print(f"    {color}{row['feature']:35s}  r = {c:+.3f}{W}  (n={row['n']:.0f})")

    # ── Layer interaction ──
    print(f"\n  {BOLD}Layer Interaction Study{W}")
    print(f"  Question: Does combining layers improve returns?\n")

    for target, groups in interactions.items():
        horizon = {"fwd_return_1m": "1-month", "fwd_return_3m": "3-month", "fwd_return_6m": "6-month"}.get(target, target)

        # Quintile spreads
        for layer_name in ["Fund", "Tech", "Macro"]:
            data = groups.get(layer_name, {})
            if data.get("spread") is not None:
                s = data["spread"]
                color = G if s > 0 else R
                print(f"  {layer_name:6s}  Q5−Q1 spread ({horizon}): {color}{s:+.1f}%{W}  "
                      f"(Q1={data['Q1_bottom']:+.1f}%, Q5={data['Q5_top']:+.1f}%)")

        # Combination analysis
        combos = groups.get("combinations", {})
        if combos:
            print(f"\n  Combined layers ({horizon}):")
            for label, stats in combos.items():
                ret = stats["mean_return"]
                color = G if ret > 0 else R
                print(f"    {label:35s}  {color}{ret:+5.1f}%{W}  "
                      f"({stats['positive_pct']:.0f}% positive, n={stats['count']})")
        print()

    # ── Weight optimization ──
    if weights:
        print(f"  {BOLD}Optimal Weight Search{W}")
        bw = weights.get("best_weights", (0.33, 0.33, 0.34))
        bc = weights.get("best_correlation", 0)
        print(f"  Best weights:   Fund {bw[0]*100:.0f}% / Tech {bw[1]*100:.0f}% / Macro {bw[2]*100:.0f}%")
        print(f"  Best corr:      {bc:+.3f}")

        cc = weights.get("current_corr")
        if cc is not None:
            print(f"  Current system: Fund 70% / Tech 20% / Macro 10%  (corr: {cc:+.3f})")
            if bc > cc + 0.01:
                print(f"  {G}→ Optimal weights would improve correlation by {bc - cc:+.3f}{W}")
            else:
                print(f"  {Y}→ Current weights are near-optimal{W}")

        print(f"\n  Top 10 weight combinations:")
        for combo in weights.get("top_10", [])[:10]:
            print(f"    F={combo['fund_weight']*100:3.0f}% T={combo['tech_weight']*100:3.0f}% "
                  f"M={combo['macro_weight']*100:3.0f}%   corr={combo['correlation']:+.3f}")

    # ── Key insights ──
    print(f"\n  {BOLD}═══ KEY INSIGHTS ═══{W}\n")

    # 1. Which features matter most
    top3 = importances[:3]
    print(f"  1. {BOLD}Most predictive features:{W}")
    for feat, imp, direction, corr in top3:
        print(f"     • {feat} (importance={imp:.3f}, r={corr:+.3f})")

    # 2. Layer importance
    dominant_layer = max(layer_sums, key=layer_sums.get)
    print(f"\n  2. {BOLD}Dominant layer:{W} {dominant_layer.upper()} ({layer_sums[dominant_layer]/total*100:.0f}% of total importance)")

    # 3. Data sufficiency
    n = len(df)
    n_features = len([c for c in df.columns if c.startswith(("tech_", "macro_", "fund_"))])
    ratio = n / max(1, n_features)
    print(f"\n  3. {BOLD}Data sufficiency:{W}")
    print(f"     {n} observations / {n_features} features = {ratio:.0f}:1 ratio")
    if ratio > 20:
        print(f"     {G}Sufficient for Random Forest (>20:1 is good){W}")
    elif ratio > 10:
        print(f"     {Y}Marginal — results should be taken directionally{W}")
    else:
        print(f"     {R}Insufficient — high risk of overfitting. Need more tickers or longer history{W}")

    # 4. Recommendation
    print(f"\n  4. {BOLD}Recommendation for your scoring system:{W}")
    if layer_sums.get("tech", 0) > layer_sums.get("fund", 0) and layer_sums.get("tech", 0) > layer_sums.get("macro", 0):
        print(f"     Technical timing matters more than expected.")
        print(f"     Consider increasing tech_influence from 30% → 40-50%.")
    elif layer_sums.get("fund", 0) > layer_sums.get("tech", 0) * 2:
        print(f"     Fundamentals dominate. Your current emphasis on quality is correct.")
        print(f"     Technical timing adds modest value for entry points.")
    elif layer_sums.get("macro", 0) > layer_sums.get("fund", 0):
        print(f"     Macro conditions matter more than individual stock quality.")
        print(f"     Consider macro_influence > 50% (currently {50}%).")
    else:
        print(f"     All three layers contribute. The current balanced approach works.")
        print(f"     Fine-tune weights based on the optimization above.")

    print(f"\n  {BOLD}Note:{W} ", end="")
    # Check if we have point-in-time data
    if "fund_pit" in df.columns and df["fund_pit"].sum() > 0:
        pit_pct = df["fund_pit"].sum() / len(df) * 100
        if pit_pct > 80:
            print(f"{G}Fundamental data is {pit_pct:.0f}% point-in-time (unbiased).{W}")
        else:
            print(f"{Y}{pit_pct:.0f}% of fundamental data is point-in-time (unbiased).{W}")
            print(f"  Run 'python stock.py collect' weekly to build more history.")
    else:
        print(f"{Y}Fundamental features have look-ahead bias (current data used at all{W}")
        print(f"  historical points). Run 'python stock.py collect --backfill' to start")
        print(f"  building point-in-time snapshots. Technical and macro features are")
        print(f"  historically accurate.")
    print()

# ═══════════════════════════════════════════════════════════════════════
#  Save results
# ═══════════════════════════════════════════════════════════════════════

def save_study_data(df, importance_results, interactions, weights):
    """Save study results to CSV and JSON for future reference."""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Save dataset
    csv_path = os.path.join(output_dir, f"study_dataset_{date.today().isoformat()}.csv")
    df.to_csv(csv_path, index=False)
    print(f"  Dataset saved:  {csv_path}")

    # Save importance
    importances, r2, _, _ = importance_results
    import json
    results = {
        "date": date.today().isoformat(),
        "observations": len(df),
        "tickers": int(df["symbol"].nunique()),
        "model_r2": round(r2, 4),
        "feature_importance": [
            {"feature": f, "importance": round(i, 6), "direction": d, "correlation": round(c, 4)}
            for f, i, d, c in importances
        ],
        "layer_interaction": interactions,
        "weight_optimization": {
            "best_weights": list(weights.get("best_weights", [])),
            "best_correlation": round(weights.get("best_correlation", 0), 4),
        } if weights else {},
    }
    json_path = os.path.join(output_dir, f"study_results_{date.today().isoformat()}.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results saved:  {json_path}")

# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════

def main(args=None):
    """Execute the parameter correlation study."""
    if args is None:
        args = sys.argv[1:]
    if not args:
        print("Usage: python stock.py study")
        print("       python stock.py study --quick          # fast mode (15 tickers)")
        print("       python stock.py study --tickers 50     # larger universe")
        print("       python stock.py study --period 3y      # longer history")
        return
    # Parse args
    n_tickers = 30  # default
    period = 2
    quick = False

    for i, a in enumerate(args):
        if a == "--tickers" and i + 1 < len(args):
            n_tickers = int(args[i + 1])
        elif a == "--period" and i + 1 < len(args):
            period = int(args[i + 1].replace("y", ""))
        elif a == "--quick":
            quick = True
            n_tickers = 15

    tickers = _DEFAULT_UNIVERSE[:n_tickers]

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║       PARAMETER CORRELATION STUDY                          ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝\n")
    print(f"  Universe:    {len(tickers)} tickers")
    print(f"  History:     {period} years")
    print(f"  Eval freq:   monthly (~21 trading days)")
    print(f"  ML model:    Random Forest (200 trees)")
    print(f"  Targets:     1-month, 3-month, 6-month forward returns")
    print()

    # 1. Build dataset
    df = build_dataset(tickers, period_years=period)

    if len(df) < 50:
        print(f"\n  ⚠ Too few observations ({len(df)}). Try more tickers or longer period.")
        return

    # 2. Feature importance
    print(f"\n  ━━━ FEATURE IMPORTANCE ANALYSIS ━━━")
    imp_results = analyze_feature_importance(df, target="fwd_return_3m")
    importances, model_r2, rf_model, feature_cols = imp_results

    # 3. Correlations
    print(f"\n  ━━━ CORRELATION ANALYSIS ━━━")
    corr_df = analyze_correlations(df)
    print(f"  Computed {len(corr_df)} correlation pairs")

    # 4. Layer interaction
    print(f"\n  ━━━ LAYER INTERACTION ANALYSIS ━━━")
    interactions = analyze_layer_interaction(df)

    # 5. Weight optimization
    print(f"\n  ━━━ WEIGHT OPTIMIZATION ━━━")
    weights = analyze_weight_optimization(df, target="fwd_return_3m")

    # 6. Print report
    print_report(df, imp_results, corr_df, interactions, weights, model_r2)

    # 7. Save results
    save_study_data(df, imp_results, interactions, weights)

if __name__ == "__main__":
    main()
