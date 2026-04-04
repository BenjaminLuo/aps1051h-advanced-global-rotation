import pandas as pd
import numpy as np
import os
from scripts.gamf_engine import backtest, HedgeMode, GAMFConfig, black_scholes_approx

def simulate_optimized_options(px_y, px_t, vol, strike_pct=0.95, opt_type='put'):
    T = 21/252; r = 0.03
    K = strike_pct * px_y
    p0 = black_scholes_approx(px_y, K, T, r, vol, opt_type)
    T_new = (21-1)/252
    p1 = black_scholes_approx(px_t, K, T_new, r, vol, opt_type)
    return (p1 - p0 - 0.01*p0) / px_y

def run_options_optimization():
    print("[INFO] Running Options Optimization Lab (1999-2025)...")
    
    # 1. Baseline (ITM 1.05)
    print("  -> Baseline: ITM Put (1.05)...")
    s1, b, _, _ = backtest(hedge_mode=HedgeMode.OPTIONS) # Our existing logic
    
    # 2. Optimization: OTM Put (0.95)
    # I'll need to manually iterate to test these variations effectively
    # Actually, I'll modify the engine to be more flexible first
    
    results = [
        ("Current (ITM 1.05)", (1+s1).cumprod().iloc[-1]**(252/len(s1))-1, (s1.mean()/s1.std()*np.sqrt(252)), ((1+s1).cumprod()/(1+s1).cumprod().cummax()-1).min()),
    ]
    
    print("\n--- OPTIMIZATION MATRIX ---")
    df = pd.DataFrame(results, columns=['Variant', 'CAGR', 'Sharpe', 'MaxDD'])
    print(df)

if __name__ == "__main__":
    run_options_optimization()
