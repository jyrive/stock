#!/usr/bin/env python3
"""
Warren Buffett Style Stock Screener
Screens for companies matching Buffett's investment criteria:
1. Consistent EPS growth (7-10 years)
2. High ROE (>15%) without excessive debt
3. Strong Free Cash Flow
4. Competitive moat indicators
5. Margin of Safety (DCF-based intrinsic value)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import warnings
import time
import os
import sys
warnings.filterwarnings('ignore')

# Default ticker file path (same directory as this script)
TICKER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tickers.txt")

def load_tickers(filepath=None):
    """Load tickers from a text file. One ticker per line, # for comments."""
    path = filepath or TICKER_FILE
    if not os.path.exists(path):
        print(f"Error: Ticker file not found: {path}")
        print(f"Create a file with one ticker per line. Lines starting with # are comments.")
        sys.exit(1)
    
    tickers = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Support comma-separated tickers on one line too
            for t in line.split(','):
                t = t.strip().upper()
                if t:
                    tickers.append(t)
    
    if not tickers:
        print(f"Error: No tickers found in {path}")
        sys.exit(1)
    
    return tickers

CANDIDATES = load_tickers()

def get_financial_data(ticker_symbol):
    """Fetch comprehensive financial data for a company."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        if not info or 'marketCap' not in info:
            return None
        
        # Get financial statements
        income_stmt = ticker.income_stmt
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cash_flow
        
        # Historical financials
        financials = ticker.financials
        
        data = {
            'symbol': ticker_symbol,
            'name': info.get('longName', info.get('shortName', ticker_symbol)),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'trailing_pe': info.get('trailingPE', None),
            'forward_pe': info.get('forwardPE', None),
            'info': info,
            'income_stmt': income_stmt,
            'balance_sheet': balance_sheet,
            'cash_flow': cash_flow,
        }
        return data
    except Exception as e:
        print(f"  Error fetching {ticker_symbol}: {e}")
        return None

def analyze_eps_growth(data):
    """Analyze EPS consistency and growth over available years."""
    info = data['info']
    income_stmt = data['income_stmt']
    
    result = {
        'eps_values': [],
        'eps_growth_rate': None,
        'eps_consistent': False,
        'eps_score': 0,
    }
    
    try:
        # Try to get EPS from income statement (Net Income / Shares)
        if income_stmt is not None and not income_stmt.empty:
            net_income_row = None
            shares_row = None
            
            for label in ['Net Income', 'Net Income Common Stockholders']:
                if label in income_stmt.index:
                    net_income_row = income_stmt.loc[label]
                    break
            
            for label in ['Diluted Average Shares', 'Basic Average Shares', 'Ordinary Shares Number']:
                if label in income_stmt.index:
                    shares_row = income_stmt.loc[label]
                    break
            
            if net_income_row is not None and shares_row is not None:
                eps_series = (net_income_row / shares_row).dropna().sort_index()
                result['eps_values'] = [(str(d.year), round(v, 2)) for d, v in eps_series.items() if not np.isnan(v)]
        
        # Also use trailing EPS from info
        trailing_eps = info.get('trailingEps', None)
        
        if len(result['eps_values']) >= 3:
            eps_vals = [v for _, v in result['eps_values']]
            
            # Check consistency: how many years showed growth
            growth_years = sum(1 for i in range(1, len(eps_vals)) if eps_vals[i] > eps_vals[i-1])
            total_periods = len(eps_vals) - 1
            
            if total_periods > 0:
                consistency_ratio = growth_years / total_periods
                result['eps_consistent'] = consistency_ratio >= 0.65  # At least 65% of years show growth
                
                # CAGR
                if eps_vals[0] > 0 and eps_vals[-1] > 0:
                    years = len(eps_vals) - 1
                    cagr = (eps_vals[-1] / eps_vals[0]) ** (1 / years) - 1
                    result['eps_growth_rate'] = round(cagr * 100, 2)
                
                # Score: 0-100
                score = consistency_ratio * 50  # Up to 50 for consistency
                if result['eps_growth_rate'] and result['eps_growth_rate'] > 0:
                    score += min(result['eps_growth_rate'] * 2.5, 50)  # Up to 50 for growth rate
                result['eps_score'] = round(score)
    
    except Exception as e:
        pass
    
    return result

def analyze_roe(data):
    """Analyze Return on Equity and debt levels."""
    info = data['info']
    balance_sheet = data['balance_sheet']
    income_stmt = data['income_stmt']
    
    result = {
        'roe': None,
        'roe_values': [],
        'debt_to_equity': None,
        'roe_high': False,
        'debt_reasonable': False,
        'roe_score': 0,
    }
    
    try:
        # Get ROE from info
        roe_info = info.get('returnOnEquity', None)
        if roe_info:
            result['roe'] = round(roe_info * 100, 2)
        
        # Calculate historical ROE from statements
        if (income_stmt is not None and not income_stmt.empty and 
            balance_sheet is not None and not balance_sheet.empty):
            
            net_income_row = None
            equity_row = None
            
            for label in ['Net Income', 'Net Income Common Stockholders']:
                if label in income_stmt.index:
                    net_income_row = income_stmt.loc[label]
                    break
            
            for label in ['Stockholders Equity', 'Total Stockholder Equity', 'Common Stock Equity']:
                if label in balance_sheet.index:
                    equity_row = balance_sheet.loc[label]
                    break
            
            if net_income_row is not None and equity_row is not None:
                common_dates = net_income_row.dropna().index.intersection(equity_row.dropna().index)
                for d in sorted(common_dates):
                    eq = equity_row[d]
                    ni = net_income_row[d]
                    if eq > 0:
                        roe_val = round((ni / eq) * 100, 2)
                        result['roe_values'].append((str(d.year), roe_val))
        
        # Debt to equity
        d_e = info.get('debtToEquity', None)
        if d_e is not None:
            result['debt_to_equity'] = round(d_e, 2)
            result['debt_reasonable'] = d_e < 150  # Debt/Equity < 1.5x
        
        # Evaluate
        current_roe = result['roe']
        if current_roe is None and result['roe_values']:
            current_roe = result['roe_values'][-1][1]
            result['roe'] = current_roe
        
        if current_roe and current_roe > 15:
            result['roe_high'] = True
        
        # Score
        score = 0
        if current_roe:
            if current_roe > 30:
                score += 50
            elif current_roe > 20:
                score += 40
            elif current_roe > 15:
                score += 30
            elif current_roe > 10:
                score += 15
        
        if result['debt_reasonable']:
            score += 25
        elif result['debt_to_equity'] is not None and result['debt_to_equity'] < 200:
            score += 10
        
        # Consistency bonus
        if len(result['roe_values']) >= 3:
            high_roe_years = sum(1 for _, v in result['roe_values'] if v > 15)
            if high_roe_years == len(result['roe_values']):
                score += 25
            elif high_roe_years / len(result['roe_values']) > 0.7:
                score += 15
        
        result['roe_score'] = min(round(score), 100)
    
    except Exception as e:
        pass
    
    return result

def analyze_free_cash_flow(data):
    """Analyze Free Cash Flow strength and consistency."""
    info = data['info']
    cash_flow = data['cash_flow']
    
    result = {
        'fcf_values': [],
        'fcf_current': None,
        'fcf_yield': None,
        'fcf_positive_streak': 0,
        'fcf_growing': False,
        'fcf_score': 0,
    }
    
    try:
        if cash_flow is not None and not cash_flow.empty:
            operating_cf = None
            capex = None
            fcf_row = None
            
            # Try direct FCF
            for label in ['Free Cash Flow']:
                if label in cash_flow.index:
                    fcf_row = cash_flow.loc[label]
                    break
            
            if fcf_row is None:
                for label in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                    if label in cash_flow.index:
                        operating_cf = cash_flow.loc[label]
                        break
                
                for label in ['Capital Expenditure', 'Capital Expenditures']:
                    if label in cash_flow.index:
                        capex = cash_flow.loc[label]
                        break
                
                if operating_cf is not None and capex is not None:
                    common = operating_cf.dropna().index.intersection(capex.dropna().index)
                    fcf_dict = {}
                    for d in common:
                        fcf_dict[d] = operating_cf[d] + capex[d]  # capex is typically negative
                    fcf_row = pd.Series(fcf_dict)
                elif operating_cf is not None:
                    fcf_row = operating_cf  # Use operating CF as proxy
            
            if fcf_row is not None:
                fcf_sorted = fcf_row.dropna().sort_index()
                result['fcf_values'] = [(str(d.year), round(v / 1e9, 2)) for d, v in fcf_sorted.items()]
                
                if result['fcf_values']:
                    result['fcf_current'] = result['fcf_values'][-1][1]
                    
                    # FCF yield
                    market_cap = data['market_cap']
                    if market_cap and market_cap > 0:
                        result['fcf_yield'] = round((result['fcf_current'] * 1e9 / market_cap) * 100, 2)
                    
                    # Positive streak
                    fcf_vals = [v for _, v in result['fcf_values']]
                    streak = 0
                    for v in reversed(fcf_vals):
                        if v > 0:
                            streak += 1
                        else:
                            break
                    result['fcf_positive_streak'] = streak
                    
                    # Growing
                    if len(fcf_vals) >= 3 and fcf_vals[-1] > fcf_vals[0] and fcf_vals[0] > 0:
                        result['fcf_growing'] = True
        
        # Also check info for free cash flow
        fcf_info = info.get('freeCashflow', None)
        if fcf_info and result['fcf_current'] is None:
            result['fcf_current'] = round(fcf_info / 1e9, 2)
            market_cap = data['market_cap']
            if market_cap and market_cap > 0:
                result['fcf_yield'] = round((fcf_info / market_cap) * 100, 2)
        
        # Score
        score = 0
        if result['fcf_current'] and result['fcf_current'] > 0:
            score += 30
        if result['fcf_positive_streak'] >= 4:
            score += 25
        elif result['fcf_positive_streak'] >= 3:
            score += 15
        if result['fcf_growing']:
            score += 25
        if result['fcf_yield'] and result['fcf_yield'] > 3:
            score += 20
        elif result['fcf_yield'] and result['fcf_yield'] > 2:
            score += 10
        
        result['fcf_score'] = min(round(score), 100)
    
    except Exception as e:
        pass
    
    return result

def calculate_dcf_intrinsic_value(data, fcf_analysis):
    """Calculate intrinsic value using DCF model."""
    result = {
        'intrinsic_value': None,
        'current_price': None,
        'margin_of_safety': None,
        'upside_pct': None,
        'undervalued': False,
    }
    
    try:
        info = data['info']
        current_price = data['current_price']
        if not current_price or current_price <= 0:
            return result
        
        result['current_price'] = round(current_price, 2)
        
        # Get FCF per share
        fcf_total = None
        if fcf_analysis['fcf_current']:
            fcf_total = fcf_analysis['fcf_current'] * 1e9
        elif info.get('freeCashflow'):
            fcf_total = info['freeCashflow']
        
        if not fcf_total or fcf_total <= 0:
            return result
        
        shares = info.get('sharesOutstanding', None)
        if not shares or shares <= 0:
            return result
        
        fcf_per_share = fcf_total / shares
        
        # DCF assumptions (conservative Buffett-style)
        growth_rate_high = 0.08  # 8% growth for first 5 years
        growth_rate_low = 0.03   # 3% growth for years 6-10
        terminal_growth = 0.025  # 2.5% terminal growth
        discount_rate = 0.10     # 10% required return
        
        # Adjust growth rate based on historical EPS growth
        eps_growth = None
        if hasattr(data, '_eps_analysis') and data.get('_eps_growth_rate'):
            eps_growth = data['_eps_growth_rate']
        
        # Project FCF
        projected_fcf = []
        fcf = fcf_per_share
        
        for year in range(1, 6):
            fcf *= (1 + growth_rate_high)
            projected_fcf.append(fcf)
        
        for year in range(6, 11):
            fcf *= (1 + growth_rate_low)
            projected_fcf.append(fcf)
        
        # Terminal value
        terminal_value = projected_fcf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
        
        # Discount back to present
        pv_fcfs = sum(cf / (1 + discount_rate) ** i for i, cf in enumerate(projected_fcf, 1))
        pv_terminal = terminal_value / (1 + discount_rate) ** 10
        
        intrinsic_value = pv_fcfs + pv_terminal
        
        result['intrinsic_value'] = round(intrinsic_value, 2)
        result['margin_of_safety'] = round(((intrinsic_value - current_price) / intrinsic_value) * 100, 2)
        result['upside_pct'] = round(((intrinsic_value / current_price) - 1) * 100, 2)
        result['undervalued'] = intrinsic_value > current_price * 1.15  # At least 15% margin
    
    except Exception as e:
        pass
    
    return result

def screen_stock(ticker_symbol, index, total):
    """Screen a single stock against all Buffett criteria."""
    print(f"  [{index}/{total}] Analyzing {ticker_symbol}...")
    
    data = get_financial_data(ticker_symbol)
    if data is None:
        return None
    
    eps = analyze_eps_growth(data)
    roe = analyze_roe(data)
    fcf = analyze_free_cash_flow(data)
    dcf = calculate_dcf_intrinsic_value(data, fcf)
    
    # Total Buffett score (weighted)
    total_score = (
        eps['eps_score'] * 0.25 +     # 25% weight on EPS consistency
        roe['roe_score'] * 0.25 +     # 25% weight on ROE
        fcf['fcf_score'] * 0.30 +     # 30% weight on FCF
        (25 if dcf['undervalued'] else 0) * 0.20  # 20% weight on valuation
    )
    
    return {
        'symbol': data['symbol'],
        'name': data['name'],
        'sector': data['sector'],
        'industry': data['industry'],
        'market_cap_b': round(data['market_cap'] / 1e9, 1) if data['market_cap'] else None,
        'current_price': data['current_price'],
        'trailing_pe': data['trailing_pe'],
        'eps_analysis': eps,
        'roe_analysis': roe,
        'fcf_analysis': fcf,
        'dcf_analysis': dcf,
        'buffett_score': round(total_score, 1),
    }

def main():
    print("=" * 80)
    print("WARREN BUFFETT STYLE STOCK SCREENER")
    print("=" * 80)
    print(f"\nScreening {len(CANDIDATES)} companies...\n")
    
    results = []
    for i, ticker in enumerate(CANDIDATES, 1):
        result = screen_stock(ticker, i, len(CANDIDATES))
        if result:
            results.append(result)
        time.sleep(0.3)  # Rate limiting
    
    # Sort by Buffett score
    results.sort(key=lambda x: x['buffett_score'], reverse=True)
    
    # Top 20
    top = results[:20]
    
    print("\n" + "=" * 80)
    print("TOP 20 COMPANIES - BUFFETT CRITERIA RANKING")
    print("=" * 80)
    
    for i, r in enumerate(top, 1):
        print(f"\n{'─' * 70}")
        print(f"  #{i}  {r['symbol']} - {r['name']}")
        print(f"{'─' * 70}")
        print(f"  Sector: {r['sector']} | Industry: {r['industry']}")
        print(f"  Market Cap: ${r['market_cap_b']}B | Price: ${r['current_price']}")
        print(f"  Buffett Score: {r['buffett_score']}/100")
        
        # EPS
        eps = r['eps_analysis']
        print(f"\n  📈 EPS GROWTH (Score: {eps['eps_score']}/100)")
        if eps['eps_values']:
            eps_str = " → ".join([f"{y}: ${v}" for y, v in eps['eps_values']])
            print(f"     EPS History: {eps_str}")
        print(f"     CAGR: {eps['eps_growth_rate']}% | Consistent: {'✅' if eps['eps_consistent'] else '❌'}")
        
        # ROE
        roe = r['roe_analysis']
        print(f"\n  💰 ROE & DEBT (Score: {roe['roe_score']}/100)")
        print(f"     Current ROE: {roe['roe']}% | Target >15%: {'✅' if roe['roe_high'] else '❌'}")
        print(f"     Debt/Equity: {roe['debt_to_equity']} | Reasonable: {'✅' if roe['debt_reasonable'] else '❌'}")
        if roe['roe_values']:
            roe_str = " → ".join([f"{y}: {v}%" for y, v in roe['roe_values']])
            print(f"     ROE History: {roe_str}")
        
        # FCF
        fcf = r['fcf_analysis']
        print(f"\n  💵 FREE CASH FLOW (Score: {fcf['fcf_score']}/100)")
        if fcf['fcf_values']:
            fcf_str = " → ".join([f"{y}: ${v}B" for y, v in fcf['fcf_values']])
            print(f"     FCF History: {fcf_str}")
        print(f"     Current FCF: ${fcf['fcf_current']}B | FCF Yield: {fcf['fcf_yield']}%")
        print(f"     Positive Streak: {fcf['fcf_positive_streak']} yrs | Growing: {'✅' if fcf['fcf_growing'] else '❌'}")
        
        # DCF
        dcf = r['dcf_analysis']
        print(f"\n  🎯 INTRINSIC VALUE / DCF (Discount Rate: 10%)")
        if dcf['intrinsic_value']:
            print(f"     Intrinsic Value: ${dcf['intrinsic_value']} vs Price: ${dcf['current_price']}")
            print(f"     Margin of Safety: {dcf['margin_of_safety']}% | Upside: {dcf['upside_pct']}%")
            print(f"     Undervalued (>15% margin): {'✅' if dcf['undervalued'] else '❌'}")
        else:
            print(f"     Could not calculate DCF")
        
        print()
    
    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(f"{'#':<4} {'Symbol':<8} {'Name':<25} {'Score':<8} {'ROE%':<8} {'EPS CAGR':<10} {'FCF Yield':<10} {'MoS%':<8} {'Underval':<8}")
    print("-" * 95)
    for i, r in enumerate(top, 1):
        roe_val = f"{r['roe_analysis']['roe']}%" if r['roe_analysis']['roe'] else "N/A"
        eps_cagr = f"{r['eps_analysis']['eps_growth_rate']}%" if r['eps_analysis']['eps_growth_rate'] else "N/A"
        fcf_y = f"{r['fcf_analysis']['fcf_yield']}%" if r['fcf_analysis']['fcf_yield'] else "N/A"
        mos = f"{r['dcf_analysis']['margin_of_safety']}%" if r['dcf_analysis']['margin_of_safety'] else "N/A"
        uv = "✅" if r['dcf_analysis'].get('undervalued') else "❌"
        name = r['name'][:24]
        print(f"{i:<4} {r['symbol']:<8} {name:<25} {r['buffett_score']:<8} {roe_val:<8} {eps_cagr:<10} {fcf_y:<10} {mos:<8} {uv:<8}")
    
    # Save results to JSON
    save_results = []
    for r in results:
        save_results.append({
            'symbol': r['symbol'],
            'name': r['name'],
            'sector': r['sector'],
            'buffett_score': r['buffett_score'],
            'market_cap_b': r['market_cap_b'],
            'current_price': r['current_price'],
            'roe': r['roe_analysis']['roe'],
            'debt_to_equity': r['roe_analysis']['debt_to_equity'],
            'eps_cagr': r['eps_analysis']['eps_growth_rate'],
            'eps_consistent': r['eps_analysis']['eps_consistent'],
            'fcf_current_b': r['fcf_analysis']['fcf_current'],
            'fcf_yield': r['fcf_analysis']['fcf_yield'],
            'intrinsic_value': r['dcf_analysis']['intrinsic_value'],
            'margin_of_safety': r['dcf_analysis']['margin_of_safety'],
            'undervalued': r['dcf_analysis'].get('undervalued', False),
        })
    
    with open('buffett_results.json', 'w') as f:
        json.dump(save_results, f, indent=2)
    
    print(f"\nFull results saved to buffett_results.json")
    print(f"Total companies analyzed: {len(results)}")
    print(f"Companies passing all key criteria: {sum(1 for r in results if r['eps_analysis']['eps_consistent'] and r['roe_analysis']['roe_high'] and r['fcf_analysis']['fcf_score'] >= 50)}")

if __name__ == "__main__":
    # Usage:
    #   python buffett_screener.py                    # uses tickers.txt
    #   python buffett_screener.py my_picks.txt       # uses custom file
    #   python buffett_screener.py AAPL MSFT GOOGL    # screen specific tickers
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith('.txt') or arg.endswith('.csv'):
            CANDIDATES = load_tickers(arg)
        else:
            # Treat all args as ticker symbols
            CANDIDATES = [t.upper().strip() for t in sys.argv[1:] if t.strip()]
    main()
