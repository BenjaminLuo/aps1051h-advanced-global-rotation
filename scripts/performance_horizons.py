import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scripts.gamf_engine import backtest, HedgeMode

def calculate_stats(series):
    """Annualized Stats."""
    days = len(series)
    if days ==0: return 0, 0, 0
    cagr = (series.iloc[-1] / series.iloc[0])**(252/days) - 1
    rets = series.pct_change().dropna()
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252)
    rolling_max = series.cummax()
    dd = (series - rolling_max).min()
    return cagr, sharpe, dd

def temporal_analysis():
    print("[INFO] Running GAMF V13.0 Bootstrap Horizon Analysis...")
    strat_rets, bench_rets, weight_history, _ = backtest()
    
    # Calculate cumulative returns
    cum_rets = (1 + strat_rets).cumprod()
    bench_cum = (1 + bench_rets).cumprod()
    
    # Combined DF
    df = pd.DataFrame({'Strategy': cum_rets, 'Benchmark': bench_cum})
    
    # 1. Calendar Year Performance
    yearly = []
    for yr in range(1999, 2025):
        yr_data = df[df.index.year == yr]
        if yr_data.empty: continue
        
        # We need the start of the year as the base (1.0)
        # So we normalize the year slice
        norm = yr_data / yr_data.iloc[0]
        s_cagr, s_sh, s_dd = calculate_stats(norm['Strategy'])
        b_cagr, b_sh, b_dd = calculate_stats(norm['Benchmark'])
        
        yearly.append({
            'Year': yr,
            'Strat CAGR': f"{s_cagr:.1%}",
            'BM CAGR': f"{b_cagr:.1%}",
            'Alpha': f"{(s_cagr - b_cagr):.1%}",
            'Strat Sharpe': f"{s_sh:.2f}",
            'Strat DD': f"{s_dd:.1%}"
        })
        
    df_yearly = pd.DataFrame(yearly)
    print("\n--- ANNUAL PERFORMANCE (1999-2025) ---")
    print(df_yearly.to_string(index=False))
    
    # 2. Regime Analysis
    regimes = {
        "Dot-com Cycle (1999-2002)": ('1999-01-01', '2002-12-31'),
        "Post-9/11 Recovery (2003-2007)": ('2003-01-01', '2007-12-31'),
        "Great Financial Crisis (2008-2009)": ('2008-01-01', '2009-12-31'),
        "Post-GFC Recovery (2010-2014)": ('2010-01-01', '2014-12-31'),
        "Low-Vol Cycle (2015-2019)": ('2015-01-01', '2019-12-31'),
        "COVID Chaos (2020-2021)": ('2020-01-01', '2021-12-31'),
        "The Pivot/Inflation (2022-2024)": ('2022-01-01', '2024-12-31')
    }
    
    print("\n--- REGIME ANALYSIS ---")
    regime_results = []
    for name, (start, end) in regimes.items():
        slice_df = df.loc[start:end]
        if slice_df.empty: continue
        norm = slice_df / slice_df.iloc[0]
        s_cagr, s_sh, s_dd = calculate_stats(norm['Strategy'])
        b_cagr, _, _ = calculate_stats(norm['Benchmark'])
        
        regime_results.append({
            'Regime': name,
            'Strat CAGR': f"{s_cagr:.1%}",
            'Bench CAGR': f"{b_cagr:.1%}",
            'Sharpe': f"{s_sh:.2f}",
            'Max DD': f"{s_dd:.1%}"
        })
        
    df_regimes = pd.DataFrame(regime_results)
    print(df_regimes.to_string(index=False))

    # 3. Rolling 3-Year CAGR Heatmap (Mental Check)
    # Simple plot
    rolling_3y = df.pct_change(252*3).dropna()
    plt.figure(figsize=(12, 6))
    plt.plot((1+rolling_3y['Strategy'])**(1/3)-1, label='Strategy 3Y Rolling CAGR', color='#2ecc71')
    plt.plot((1+rolling_3y['Benchmark'])**(1/3)-1, label='Index 3Y Rolling CAGR', color='#34495e', linestyle='--')
    plt.title('Rolling 3-Year CAGR (Structural Outperformance)')
    plt.legend()
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/rolling_performance.png', dpi=300)
    print("\n[INFO] Rolling 3Y CAGR figure saved to figures/rolling_performance.png")

if __name__ == "__main__":
    temporal_analysis()
