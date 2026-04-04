import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scripts.gamf_backtester import backtest as backtest_options
from scripts.gamf_backtester_rotation import backtest as backtest_rotation

def compare():
    print("[INFO] Comparing Defensive Postures: Options Hedge vs Bond Rotation...")
    
    # Run Both Backtests
    print("  -> Execution 1: Options Hedge (V13-Ultimate)...")
    s_opt, b_rets, w_opt, r_opt = backtest_options()
    
    print("  -> Execution 2: Bond Rotation (V13-Lecture)...")
    s_rot, _, w_rot, r_rot = backtest_rotation()
    
    # 1. Performance Summary
    def get_stats(rets, b_rets):
        cum = (1 + rets).cumprod()
        cagr = (cum.iloc[-1]**(252/len(rets))) - 1
        vol = rets.std() * np.sqrt(252)
        sharpe = cagr / vol
        dd = (cum / cum.cummax()) - 1
        max_dd = dd.min()
        return {'CAGR': cagr, 'Sharpe': sharpe, 'MaxDD': max_dd}

    stats_opt = get_stats(s_opt, b_rets)
    stats_rot = get_stats(s_rot, b_rets)
    stats_bench = get_stats(b_rets, b_rets)
    
    df_stats = pd.DataFrame([stats_opt, stats_rot, stats_bench], 
                            index=['Options Hedge', 'Bond Rotation', 'Benchmark (SPY)'])
    
    print("\n--- COMPARATIVE STRATEGY MATRIX ---")
    print(df_stats)
    print("------------------------------------\n")
    
    # 2. Visual Comparison
    plt.figure(figsize=(14, 10))
    plt.plot((1 + s_opt).cumprod(), label='V13-Options (Insurance Approach)', color='#2ECC71', linewidth=2)
    plt.plot((1 + s_rot).cumprod(), label='V13-Bonds (Rotation Approach)', color='#3498DB', linewidth=2)
    plt.plot((1 + b_rets).cumprod(), label='SP500', color='#34495E', alpha=0.5, linestyle='--')
    
    plt.title('GAMF Comparative Analysis: Defensive Postures (1999-2025)', fontsize=16, fontweight='bold')
    plt.yscale('log')
    plt.ylabel('Growth of $1')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    os.makedirs('figures/presentation', exist_ok=True)
    plt.savefig('figures/presentation/strategy_comparison_options_vs_bonds.png', dpi=300)
    print(f"[SUCCESS] Comparison figure saved to figures/presentation/strategy_comparison_options_vs_bonds.png")
    
    # Save Matrix
    df_stats.to_csv('data/processed/strategy_comparison_matrix.csv')

if __name__ == "__main__":
    compare()
