import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scripts.gamf_engine import backtest, HedgeMode

# ==============================================================================
# STYLE CONFIGURATION (Institutional Premium)
# ==============================================================================
GAMF_GREEN = '#2ECC71'
SKY_BLUE = '#3498DB'
INDEX_SLATE = '#34495E'
HEDGE_RED = '#E74C3C'

plt.rcParams.update({
    'font.size': 10,
    'axes.titleweight': 'bold',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'figure.facecolor': 'white'
})

def generate_regime_visuals():
    print("[INFO] Initializing GAMF Architectural Visualization (Full Horizon Comparison)...")
    
    # 1. Execute Dual-Backtest (V29 Options vs Bonds)
    print("  -> Running V29 Options (Adaptive Collar)...")
    s_rets_opt, b_rets, w_opt, r_opt = backtest(hedge_mode=HedgeMode.OPTIONS)
    
    print("  -> Running V29 Bond Rotation (Duration Momentum)...")
    s_rets_bond, _, w_bond, r_bond = backtest(hedge_mode=HedgeMode.BOND_ROTATION)
    
    # Cumulative Growth
    cum_opt = (1 + s_rets_opt).cumprod()
    cum_bond = (1 + s_rets_bond).cumprod()
    cum_bench = (1 + b_rets).cumprod()
    
    # 2. Define Regimes
    regimes = [
        ("Dot-com Bust", "1999-01-01", "2002-12-31"),
        ("Post-9/11 Cycle", "2003-01-01", "2007-12-31"),
        ("Global Financial Crisis", "2008-01-01", "2009-12-31"),
        ("Post-GFC Expansion", "2010-01-01", "2019-12-31"),
        ("COVID Flash Shock", "2020-01-01", "2021-12-31"),
        ("Modern Inflation Era", "2022-01-01", "2024-12-31")
    ]
    
    os.makedirs('figures/presentation', exist_ok=True)
    
    # --- FIGURE 1: REGIME FACET GRID (Triple Line) ---
    print("[INFO] Generating Regime Facet Grid (Triple Strategy Analysis)...")
    fig, axes = plt.subplots(2, 3, figsize=(22, 13))
    axes = axes.flatten()
    
    for i, (name, start, end) in enumerate(regimes):
        ax = axes[i]
        sl_opt = cum_opt.loc[start:end]
        sl_bond = cum_bond.loc[start:end]
        sl_bench = cum_bench.loc[start:end]
        
        if sl_opt.empty: continue
        
        # Normalize to 1.0 at start of regime
        sl_opt = sl_opt / sl_opt.iloc[0] if not sl_opt.empty else sl_opt
        sl_bond = sl_bond / sl_bond.iloc[0] if not sl_bond.empty else sl_bond
        sl_bench = sl_bench / sl_bench.iloc[0] if not sl_bench.empty else sl_bench
        
        ax.plot(sl_opt.index, sl_opt, color=HEDGE_RED, label='V29 Options', linewidth=2.5)
        ax.plot(sl_bond.index, sl_bond, color=GAMF_GREEN, label='V29 Bonds', linewidth=2.0)
        ax.plot(sl_bench.index, sl_bench, color=INDEX_SLATE, label='SPY (Index)', linestyle='--')
        
        ax.set_title(name, fontsize=14)
        ax.set_yscale('log' if (max(sl_opt.max(), sl_bond.max()) / min(sl_opt.min(), sl_bond.min())) > 2.5 else 'linear')
        ax.legend(prop={'size': 7}, loc='upper left')
        plt.setp(ax.get_xticklabels(), rotation=30)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.suptitle('GAMF V29 Synergy: Options Hedge vs. Bond Rotation Alpha Comparison (1999-2025)', fontsize=22, fontweight='bold')
    plt.savefig('figures/presentation/regime_facet_grid.png', dpi=300)
    
    # --- FIGURE 2: TAIL-RISK TRIPLE DISTRIBUTION ---
    print("[INFO] Generating Tail-Risk Distribution Analysis (KDE Comparison)...")
    plt.figure(figsize=(12, 7))
    sns.kdeplot(b_rets, fill=True, color=INDEX_SLATE, label='SPY Benchmark')
    sns.kdeplot(s_rets_opt, fill=True, color=HEDGE_RED, label='V29 Adaptive Options')
    sns.kdeplot(s_rets_bond, fill=True, color=GAMF_GREEN, label='V29 Bond Rotation')
    
    plt.axvline(x=0, color='grey', linestyle='--', alpha=0.5)
    plt.title('V29 Dual Distribution: Strategy-Specific Tail-Risk Truncation', fontsize=16)
    plt.xlabel('Daily % Return')
    plt.ylabel('Density')
    plt.xlim(-0.06, 0.06) 
    plt.grid(True, alpha=0.2)
    plt.legend()
    plt.savefig('figures/presentation/tail_risk_truncation.png', dpi=300)
    
    # --- FIGURE 3: ALPHA HEATMAP (V29 Bond Baseline) ---
    print("[INFO] Refreshing Alpha-Beta Heatmap (V29 Bond Alpha)...")
    q_rets = pd.concat([s_rets_bond, b_rets], axis=1).resample('Q').apply(lambda x: (1+x).prod() - 1)
    q_rets.columns = ['GAMF', 'SPY']
    q_alpha = q_rets['GAMF'] - q_rets['SPY']
    q_alpha_df = q_alpha.reset_index(); q_alpha_df['Year'] = q_alpha_df['index'].dt.year; q_alpha_df['Quarter'] = q_alpha_df['index'].dt.quarter
    matrix = q_alpha_df.pivot(index='Year', columns='Quarter', values=0)
    plt.figure(figsize=(11, 9))
    sns.heatmap(matrix, cmap='RdYlGn', center=0, annot=True, fmt='.1%', cbar_kws={'label': 'Options Alpha'})
    plt.title('Strategic Alpha Heatmap: Quarterly Outperformance (V14 Options PRO)', fontsize=16)
    plt.savefig('figures/presentation/alpha_heatmap.png', dpi=300)

if __name__ == "__main__":
    generate_regime_visuals()
