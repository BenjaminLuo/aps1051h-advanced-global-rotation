import pandas as pd
import numpy as np
import os

UNIVERSE_FILE = "df_etf_universe.parquet"
US_SECTORS = ['XLK', 'XLF', 'XLV', 'XLY', 'XLC', 'XLI', 'XLE', 'XLP', 'XLB', 'XLU', 'XLRE']

def run_diagnostic():
    df_all = pd.read_parquet(UNIVERSE_FILE)
    df_all['date'] = pd.to_datetime(df_all['date'])
    df_all = df_all.sort_values(['ticker', 'date'])
    
    px = df_all.pivot(index='date', columns='ticker', values='prc').ffill()
    rets_raw = df_all.pivot(index='date', columns='ticker', values='ret').fillna(0)
    
    dates = px.index[(px.index >= '2011-01-01') & (px.index <= '2012-01-01')]
    
    portfolio_returns = []
    portfolio_dates = []
    triggers = []
    holdings = []

    # Simple 252d momentum for selection mock
    for d in dates:
        history_px = px.loc[:d].iloc[:-1]
        if len(history_px) < 252: continue
        
        # 1. Selection (Simulated V20 Top-1)
        mom = (history_px.iloc[-1] / history_px.iloc[-252]) - 1
        sector_mom = mom[US_SECTORS].dropna()
        top_sector = sector_mom.idxmax()
        
        # 2. Breadth
        b_val = (mom > 0).mean()
        
        # 3. Panic (CPI)
        corr_mat = history_px[US_SECTORS].tail(21).pct_change().corr()
        cpi = (corr_mat.values[np.triu_indices_from(corr_mat.values, k=1)]).mean()
        
        is_panic = (cpi > 0.85) or (b_val < 0.35) # Simple proxy
        
        # 4. Exposure
        if not is_panic:
            exposure_core = 1.0; exposure_sat = 0.5
        else:
            exposure_core = 0.0; exposure_sat = 0.0
            
        # 5. Return
        daily_ret = (rets_raw.loc[d]['SPY'] * exposure_core) + (rets_raw.loc[d][top_sector] * exposure_sat)
        
        portfolio_returns.append(daily_ret)
        portfolio_dates.append(d)
        triggers.append(cpi)
        holdings.append(top_sector)
        
    diag = pd.DataFrame({
        'date': portfolio_dates,
        'ret': portfolio_returns,
        'cpi': triggers,
        'holding': holdings,
        'spy_ret': rets_raw.loc[portfolio_dates, 'SPY'].values
    })
    
    diag['cum_strat'] = (1 + diag['ret']).cumprod()
    diag['cum_spy'] = (1 + diag['spy_ret']).cumprod()
    
    print("--- 2011 DIAGNOSTIC SUMMARY ---")
    print(diag.sort_values(by='ret').head(10)) # Top losses
    
    crash_day = diag.loc[diag['ret'].idxmin()]
    print(f"\nCRASH EVENT DETECTED ON: {crash_day['date']}")
    print(f"Strategy Return: {crash_day['ret']:.2%}")
    print(f"SPY Return: {crash_day['spy_ret']:.2%}")
    print(f"CPI (Correlation Panic): {crash_day['cpi']:.2f}")
    print(f"Top Sector Held: {crash_day['holding']}")

if __name__ == "__main__":
    run_diagnostic()
