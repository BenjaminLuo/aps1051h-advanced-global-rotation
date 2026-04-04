import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from gamf_backtester import backtest

def calculate_stats(cum_rets, strat_rets):
    days = len(strat_rets)
    cagr = (cum_rets.iloc[-1] / cum_rets.iloc[0])**(252/days) - 1
    sharpe = (strat_rets.mean() / strat_rets.std()) * np.sqrt(252)
    rolling_max = cum_rets.cummax()
    dd = (cum_rets - rolling_max) / rolling_max
    return cagr, sharpe, dd.min()

def generate_presentation_assets():
    print("[INFO] Generating GAMF Presentation Assets (V13.1-HONEST-ALPHA)...")
    os.makedirs('figures/presentation', exist_ok=True)
    
    # 1. Acquire Performance for the "Evolution Scatter"
    versions = {}
    
    # SPY Index (Benchmark)
    _, b_r, _, _ = backtest(overlay_weight=0.0)
    b_c = (1 + b_r).cumprod()
    versions['Benchmark (SPY)'] = calculate_stats(b_c, b_r)
    
    # V1.0 - Baseline (Price-Only, Fixed Window)
    # Simulator-only parameters (Fixed Window 252, No Leverage)
    s1, b1_dummy, _, _ = backtest(lookback=252, min_warmup=252, overlay_weight=0.0)
    c1 = (1 + s1).cumprod()
    versions['V1.0 Baseline'] = calculate_stats(c1, s1)
    
    # V13.1 - Honest Alpha (Total Return, Adaptive, T-1 SIGNAL)
    s13, b13_dummy, w13, _ = backtest(lookback=252, min_warmup=63, overlay_weight=0.75)
    c13 = (1 + s13).cumprod()
    versions['V13.1 Honest'] = calculate_stats(c13, s13)
    
    # Use benchmark from the V13.1 run for consistency in plots
    b_r = b13_dummy

    # 2. Risk-Reward Efficiency Scatter Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.set_theme(style="whitegrid")
    
    points = []
    for name, stats in versions.items():
        points.append({'Model': name, 'CAGR': stats[0]*100, 'MaxDD': abs(stats[2]*100), 'Sharpe': stats[1]})
    
    df_plot = pd.DataFrame(points)
    scatter = sns.scatterplot(data=df_plot, x='MaxDD', y='CAGR', hue='Model', s=300, palette='viridis', ax=ax)
    
    # Annotate points
    for i in range(df_plot.shape[0]):
        ax.text(df_plot.MaxDD[i]+1, df_plot.CAGR[i], 
                f"{df_plot.Model[i]}\n(Sh: {df_plot.Sharpe[i]:.2f})", 
                fontsize=11, fontweight='bold')
    
    ax.set_title("Strategy Efficiency Frontier: Risk vs. Reward (2010-2025)", fontsize=18, fontweight='bold')
    ax.set_xlabel("Maximum Drawdown (%) - RISK", fontsize=14)
    ax.set_ylabel("Annualized Growth (CAGR %) - REWARD", fontsize=14)
    ax.set_xlim(df_plot.MaxDD.min()-5, df_plot.MaxDD.max()+15)
    ax.set_ylim(df_plot.CAGR.min()-2, df_plot.CAGR.max()+5)
    
    plt.tight_layout()
    plt.savefig('figures/presentation/risk_reward_frontier.png', dpi=300)
    print("  [SUCCESS] Efficiency Frontier saved to figures/presentation/risk_reward_frontier.png")
    
    # 3. Monthly Returns Heatmap (The Quilt)
    monthly_rets = s13.resample('ME').apply(lambda x: (1 + x).prod() - 1)
    df_heatmap = monthly_rets.to_frame(name='Return')
    df_heatmap['Year'] = df_heatmap.index.year
    df_heatmap['Month'] = df_heatmap.index.month_name().str[:3]
    
    pivot_heatmap = df_heatmap.pivot(index='Year', columns='Month', values='Return')
    months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    pivot_heatmap = pivot_heatmap[months_order]
    
    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(pivot_heatmap * 100, annot=True, fmt=".1f", linewidths=.5, cmap="RdYlGn", center=0, 
                cbar_kws={'label': 'Monthly Return (%)'}, ax=ax)
    
    ax.set_title("GAMF Strategy: Monthly Returns Heatmap (2010-2025)", fontsize=20, fontweight='bold')
    plt.tight_layout()
    plt.savefig('figures/presentation/monthly_heatmap_quilt.png', dpi=300)
    print("  [SUCCESS] Monthly Heatmap saved to figures/presentation/monthly_heatmap_quilt.png")
    
    # 4. Strategic Diagnostics Table
    # Monthly Win Rate
    win_rate = (monthly_rets > 0).mean()
    # Turnover (Simple approx by weight changes)
    weight_diff = w13.diff().abs().sum(axis=1).mean() * 52 # Weekly rebalances to Annual
    # Avg Hold Time: Length of persistent asset inclusion
    def get_avg_hold(w_df):
        all_holds = []
        for col in w_df.columns:
            is_held = (w_df[col] > 0).astype(int)
            runs = is_held.diff().ne(0).cumsum()
            hold_lengths = is_held.groupby(runs).sum()
            all_holds.extend(hold_lengths[hold_lengths > 0].tolist())
        return np.mean(all_holds) if all_holds else 0

    avg_hold = get_avg_hold(w13)
    
    diag_data = [
        ["Annualized Turnover", f"{weight_diff:.1%}"],
        ["Monthly Win Rate", f"{win_rate:.1%}"],
        ["Avg Asset Hold Time (Weeks)", f"{avg_hold:.1f}"],
        ["Worst Daily Drawdown", f"{abs(s13.min()):.1%}"],
        ["Best Daily Outperformance", f"{(s13 - b_r).max():.1%}"]
    ]
    df_diag = pd.DataFrame(diag_data, columns=["Diagnostic Metric", "Value"])
    print("\n--- STRATEGIC TRADE DIAGNOSTICS (V13.1) ---")
    print(df_diag.to_string(index=False))
    df_diag.to_csv('data/processed/strategic_diagnostics.csv', index=False)

if __name__ == "__main__":
    generate_presentation_assets()
