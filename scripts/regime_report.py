import pandas as pd
import numpy as np
import os
from scripts.gamf_engine import backtest, HedgeMode

def calculate_stats(strat_rets, bench_rets):
    """Annualized stats for a specific slice."""
    days = len(strat_rets)
    if days ==0: return 0.0, 0.0, 0.0, 0.0
    
    # Cumulative returns for the slice (starting at 1.0)
    cum_s = (1 + strat_rets).cumprod()
    cum_b = (1 + bench_rets).cumprod()
    
    cagr_s = (cum_s.iloc[-1] / 1.0)**(252/days) - 1
    cagr_b = (cum_b.iloc[-1] / 1.0)**(252/days) - 1
    
    sharpe = (strat_rets.mean() / strat_rets.std()) * np.sqrt(252) if strat_rets.std() != 0 else 0.0
    
    rolling_max = cum_s.cummax()
    dd = (cum_s - rolling_max) / rolling_max
    max_dd = dd.min()
    
    return cagr_s, cagr_b, sharpe, max_dd

def generate_regime_report():
    print("[INFO] Initializing GAMF Multi-Decade Regime Investigation (1999-2025)...")
    
    # 1. Execute backtest for the full horizon
    s_rets, b_rets, w_df, r_df = backtest()
    
    # 2. Define historical regimes
    regimes = [
        ("Dot-com Cycle (1999-2002)", "1999-01-01", "2002-12-31"),
        ("Post-9/11 Recovery (2003-2007)", "2003-01-01", "2007-12-31"),
        ("Global Financial Crisis (2008-2009)", "2008-01-01", "2009-12-31"),
        ("Post-GFC Expansion (2010-2019)", "2010-01-01", "2019-12-31"),
        ("COVID-19 Shock & Rally (2020-2021)", "2020-01-01", "2021-12-31"),
        ("Modern Inflation Cycle (2022-2024)", "2022-01-01", "2024-12-31")
    ]
    
    results = []
    
    for name, start, end in regimes:
        # Slice data
        s_slice = s_rets.loc[start:end]
        b_slice = b_rets.loc[start:end]
        r_slice = r_df.loc[start:end]
        
        if s_slice.empty: continue
        
        # Calculate performance
        c_s, c_b, sh, mdd = calculate_stats(s_slice, b_slice)
        
        # Calculate diagnostics (Regime Composition)
        counts = r_slice.value_counts(normalize=True).to_dict()
        def_freq = counts.get('DEFENSE_OPTIONS', 0.0) + counts.get('DEFENSE_ROTATION', 0.0) + counts.get('DEFENSE_CASH', 0.0)
        bull_freq = counts.get('BULL_STD', 0.0)
        
        results.append({
            'Market Regime': name,
            'GAMF CAGR': f"{c_s:.1%}",
            'SPY CAGR': f"{c_b:.1%}",
            'Alpha/Beta': f"{(c_s - c_b):.1%}",
            'Sharpe': f"{sh:.2f}",
            'Max DD': f"{mdd:.1%}",
            'Defense Mode %': f"{def_freq:.1%}",
            'Bull Mode %': f"{bull_freq:.1%}"
        })
        
    df_results = pd.DataFrame(results)
    
    print("\n--- GAMF MULTI-DECADE PERFORMANCE REPORT (1999-2025) ---")
    print(df_results.to_string(index=False))
    
    # Save to data/processed for report embedding
    os.makedirs('data/processed', exist_ok=True)
    df_results.to_csv('data/processed/regime_investigation.csv', index=False)
    print(f"\n[INFO] Regime-specific report saved to data/processed/regime_investigation.csv")

if __name__ == "__main__":
    generate_regime_report()
