"""Analysis engines — fundamental, technical, macro, and verdict scoring."""

from .fundamental import (
    analyze_eps_growth,
    analyze_roe,
    analyze_free_cash_flow,
    analyze_balance_sheet,
    analyze_dividends,
    calculate_dcf_intrinsic_value,
    analyze_revenue_growth,
)
from .technical import (
    rsi,
    sma,
    ema,
    bollinger_bands,
    macd,
    week52_position,
    compute_tech_score,
    analyze_technical,
    entry_rating,
    print_technical,
)
from .macro import (
    analyze_macro,
    print_macro_full,
    print_macro_compact,
    macro_one_liner,
    score_vix,
    score_sp500_vs_200,
    score_sp500_52w,
)
from .verdict import (
    compute_verdict,
    should_buy,
    should_sell,
    print_verdict,
    print_verdict_table,
    verdict_one_liner,
)
