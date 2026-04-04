from scripts.gamf_engine import backtest as unified_backtest, HedgeMode, calculate_whites_reality_check
import matplotlib.pyplot as plt
import os
import pandas as pd
import numpy as np

UNIVERSE_FILE = "data/processed/df_etf_universe.parquet"

def backtest(lookback=252, min_warmup=252, breadth_stop=0.50, breadth_trigger=0.5, n_assets=5, overlay_weight=0.5):
    # Using Unified Engine in OPTIONS mode
    return unified_backtest(hedge_mode=HedgeMode.OPTIONS)

def plot_results(s_rets, b_rets, w_df, r_df, label="V13-ULTIMATE"):
    plt.close('all')
    fig, axes = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]})
    cum_s = (1 + s_rets).cumprod()
    cum_b = (1 + b_rets).cumprod()
    axes[0].plot(cum_s, label=f"GAMF {label}", color='#2ECC71', linewidth=2.5)
    axes[0].plot(cum_b, label="SPY (Benchmark)", color='#34495E', alpha=0.6)
    axes[0].set_title(f"GAMF OVERLAY: {label} (Long-Term Horizon)", fontsize=16, fontweight='bold')
    axes[0].set_yscale('log')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    dd_s = (cum_s / cum_s.cummax()) - 1
    axes[1].fill_between(dd_s.index, dd_s, 0, color='#E74C3C', alpha=0.3)
    axes[1].set_title("Drawdown Profile", fontsize=12)
    plt.tight_layout()
    os.makedirs('figures/presentation', exist_ok=True)
    plt.savefig('figures/presentation/v13_ultimate_dashboard.png', dpi=300)
    
    # Audit printout
    excess = s_rets - b_rets
    p_val = calculate_whites_reality_check(excess)
    print(f"\n--- STRATEGIC AUDIT ({label}) ---")
    print(f"CAGR           : {((1+s_rets).cumprod().iloc[-1]**(252/len(s_rets)))-1:.2%}")
    print(f"Sharpe Ratio   : {(s_rets.mean()/s_rets.std()*np.sqrt(252)):.2f}")
    print(f"Max Drawdown   : {dd_s.min():.2%}")
    print(f"Reality Check  : {p_val:.2%} Confidence")
    print("------------------------------------------\n")

if __name__ == "__main__":
    if os.path.exists(UNIVERSE_FILE):
        s, b, w, r = backtest()
        plot_results(s, b, w, r)
    else:
        print("[ERROR] Data missing. Run get_gamf_data.py first.")
