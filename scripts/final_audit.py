import pandas as pd
import numpy as np
import os
from scripts.gamf_engine import backtest, HedgeMode, GAMFConfig

def run_global_audit():
    print("[INFO] Executing Final Project Audit (Full Spectrum 1999-2025)...")
    
    config = GAMFConfig()
    results = []
    
    modes = [
        ("Options Hedge (V13-Ultimate)", HedgeMode.OPTIONS),
        ("Adaptive Collar (V14-PRO)", HedgeMode.ADAPTIVE_COLLAR),
        ("Bond Rotation (V13-Lecture)", HedgeMode.BOND_ROTATION),
        ("Cash Defense (V13-Conservative)", HedgeMode.CASH)
    ]
    
    for name, mode in modes:
        print(f"  -> Running {name}...")
        s_rets, b_rets, w_df, r_df = backtest(hedge_mode=mode, config=config)
        
        cum_s = (1 + s_rets).cumprod()
        cum_b = (1 + b_rets).cumprod()
        
        cagr = (cum_s.iloc[-1]**(252/len(s_rets))) - 1
        vol = s_rets.std() * np.sqrt(252)
        sharpe = cagr / vol
        dd = (cum_s / cum_s.cummax()) - 1
        max_dd = dd.min()
        
        results.append({
            'Strategy': name,
            'CAGR': f"{cagr:.2%}",
            'Sharpe': f"{sharpe:.2f}",
            'MaxDD': f"{max_dd:.2%}",
            'Volatility': f"{vol:.2%}"
        })
        
    # Benchmark
    b_cum = (1 + b_rets).cumprod()
    b_cagr = (b_cum.iloc[-1]**(252/len(b_rets))) - 1
    b_vol = b_rets.std() * np.sqrt(252)
    b_sharpe = b_cagr / b_vol
    b_dd = (b_cum / b_cum.cummax()) - 1
    b_max_dd = b_dd.min()
    
    results.append({
        'Strategy': 'S&P 500 (Benchmark)',
        'CAGR': f"{b_cagr:.2%}",
        'Sharpe': f"{b_sharpe:.2f}",
        'MaxDD': f"{b_max_dd:.2%}",
        'Volatility': f"{b_vol:.2%}"
    })
    
    df_results = pd.DataFrame(results)
    os.makedirs('data/processed', exist_ok=True)
    df_results.to_csv('data/processed/final_project_metrics.csv', index=False)
    print("\n--- FINAL RESEARCH METRICS ---")
    print(df_results.to_string(index=False))
    print("-------------------------------\n")

if __name__ == "__main__":
    run_global_audit()
