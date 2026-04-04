import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from gamf_backtester import backtest

def visualize_composition():
    print("[INFO] Running GAMF V13.0 Bootstrap Composition Analysis (FULL HORIZON: 2010-2025)...")
    # Execute backtest to get weight history
    _, _, weight_df, _ = backtest()
    
    # 1. Select the FULL Time Horizon: 2010-2025
    target_slice = weight_df
    
    # 2. Prepare Data for Stacked Area Chart
    active_tickers = target_slice.columns[(target_slice != 0).any()].tolist()
    plot_df = target_slice[active_tickers]
    
    # 3. Create the Visualization
    sns.set_theme(style="white", palette="muted")
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # Custom color palette for readability
    colors = sns.color_palette("husl", len(active_tickers))
    color_map = {ticker: colors[i] for i, ticker in enumerate(active_tickers)}
    color_map['SPY'] = '#34495e' # Deep Navy for Core
    
    # Plot Stacked Area
    ax.stackplot(plot_df.index, 
                 [plot_df[t] for t in active_tickers], 
                 labels=active_tickers, 
                 colors=[color_map[t] for t in active_tickers],
                 alpha=0.85)
    
    # Formatting
    ax.set_title("GAMF Portfolio Composition: 15-Year Life Cycle (2010-2025)", fontsize=22, fontweight='bold')
    ax.set_ylabel("Gross Portfolio Exposure (Core + Satellite Overlay)", fontsize=16)
    ax.set_ylim(0, 2.0)
    ax.axhline(1.0, color='white', linestyle='--', alpha=0.5, label='100% Equity Baseline')
    
    # Add Regime Annotations (Historical Scale)
    ax.annotate('S&P Downgrade / Flash Crash\n(Hedge Exit)', 
                xy=(pd.to_datetime('2011-08-01'), 0.2), 
                xytext=(pd.to_datetime('2010-06-01'), 0.6),
                arrowprops=dict(facecolor='black', shrink=0.05),
                fontsize=11)
    
    ax.annotate('Structural Bull Market\n(1.75x Leverage)', 
                xy=(pd.to_datetime('2013-10-01'), 1.5), 
                xytext=(pd.to_datetime('2013-01-01'), 1.8),
                arrowprops=dict(facecolor='black', shrink=0.05),
                fontsize=11)

    ax.annotate('COVID Crash / Exit', 
                xy=(pd.to_datetime('2020-03-20'), 0.1), 
                xytext=(pd.to_datetime('2019-01-01'), 0.6),
                arrowprops=dict(facecolor='black', shrink=0.05),
                fontsize=11, fontweight='bold')
    
    ax.annotate('Inflation Rotation', 
                xy=(pd.to_datetime('2022-06-01'), 1.3), 
                xytext=(pd.to_datetime('2021-01-01'), 1.8),
                arrowprops=dict(edgecolor='black', shrink=0.05),
                fontsize=11)

    ax.annotate('Modern AI Expansion', 
                xy=(pd.to_datetime('2024-06-01'), 1.6), 
                xytext=(pd.to_datetime('2023-01-01'), 1.9),
                arrowprops=dict(edgecolor='black', shrink=0.05),
                fontsize=11, fontweight='bold')
    
    # Move legend outside
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), title="Portfolio Assets", fontsize=9)
    
    plt.tight_layout()
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/composition_full_lifecycle.png', dpi=300)
    print("\n[INFO] 15-Year Life Cycle composition figure saved to figures/composition_full_lifecycle.png")

if __name__ == "__main__":
    visualize_composition()
