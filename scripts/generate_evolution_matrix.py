import pandas as pd
import numpy as np
import os
from gamf_backtester import backtest

def calculate_stats(strat_rets):
    # Calculate cumulative returns from daily returns
    cum_rets = (1 + strat_rets).cumprod()
    
    days = len(strat_rets)
    if days == 0: return 0.0, 0.0, 0.0
    
    cagr = (cum_rets.iloc[-1] / 1.0)**(252/days) - 1 # Assuming $1 initial wealth
    sharpe = (strat_rets.mean() / strat_rets.std()) * np.sqrt(252) if strat_rets.std() != 0 else 0.0
    rolling_max = cum_rets.cummax()
    dd = (cum_rets - rolling_max) / rolling_max
    return cagr, sharpe, dd.min()

def generate_matrix():
    print("[INFO] Generating Evolution Matrix (V1.0 vs V7.0 vs V13.0)...")
    
    # Updated to work with latest gamf_backtester.py API (V25.0)
    # V1.0 - Baseline (Fixed Window 252, Price-Only, 1.0 Gross)
    s1, _, _, _ = backtest(lookback=252, min_warmup=252, overlay_weight=0.0)
    v1_cagr, v1_sh, v1_dd = calculate_stats(s1)
    
    # V7.0 - Core Overlay (Fixed Window 252, +50% Satellite, Price-Only)
    s7, _, _, _ = backtest(lookback=252, min_warmup=252, overlay_weight=0.5)
    v7_cagr, v7_sh, v7_dd = calculate_stats(s7)
    
    # V13.0 - Bootstrap (Adaptive 63->252, +75% Satellite, Total Return)
    s13, _, _, _ = backtest(lookback=252, min_warmup=63, overlay_weight=0.75)
    v13_cagr, v13_sh, v13_dd = calculate_stats(s13)

    data = [
        ["V1.0 Baseline", "Price", "252d Fixed", "1.0x Core", f"{v1_cagr:.1%}", f"{v1_sh:.2f}", f"{v1_dd:.1%}"],
        ["V7.0 Overlay", "Price", "252d Fixed", "1.5x Multi", f"{v7_cagr:.1%}", f"{v7_sh:.2f}", f"{v7_dd:.1%}"],
        ["V13.0 Bootstrap", "Total Return", "63d Adaptive", "1.75x Alpha", f"{v13_cagr:.1%}", f"{v13_sh:.2f}", f"{v13_dd:.1%}"]
    ]
    
    df = pd.DataFrame(data, columns=["Version", "Data Engine", "Signal Window", "Exposure Model", "CAGR", "Sharpe", "Max DD"])
    print("\n--- GAMF STRATEGY EVOLUTION MATRIX ---")
    print(df.to_string(index=False))
    
    # Save to CSV for the report to reference if needed
    os.makedirs('data/processed', exist_ok=True)
    df.to_csv('data/processed/evolution_matrix.csv', index=False)
    print(f"\n[INFO] Evolution matrix saved to data/processed/evolution_matrix.csv")

if __name__ == "__main__":
    generate_matrix()
