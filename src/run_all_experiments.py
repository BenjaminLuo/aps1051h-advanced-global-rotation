import sys
import os
# Ensure package can be found in src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from janus_rotational.config import (
    BOND_UNIVERSE, DATA_END, DATA_START, EQUITY_UNIVERSE,
)
from janus_rotational.data.fetcher import fetch_equity_and_bond
from janus_rotational.execution.ladder import LadderEngine
from janus_rotational.regime.macro import build_weekly_regime
from janus_rotational.signals.selector import build_weekly_selections
from janus_rotational.analytics.metrics import compute_metrics

# ── Setup ──
OOS_START = "2005-01-01"
OOS_END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0
PLOTS_DIR = "plots/research/"
os.makedirs(PLOTS_DIR, exist_ok=True)

# ── Suppression ──
logging.basicConfig(level=logging.ERROR)
import warnings
warnings.filterwarnings("ignore")

print("... Initializing Research Suite ...")
EXTENDED_EQUITY = list(EQUITY_UNIVERSE) + ["NVDA", "AAPL"]
universes = fetch_equity_and_bond(EXTENDED_EQUITY, BOND_UNIVERSE, DATA_START, DATA_END)
eq_prices, eq_vol = universes["equity"]
bond_prices, bond_vol = universes["bond"]
prices = pd.concat([eq_prices, bond_prices], axis=1).sort_index()
volume = pd.concat([eq_vol, bond_vol], axis=1).sort_index()

def run_backtest(
    slippage=0.0002, 
    commission=0.005, 
    n_tranches=4, 
    mom_short=63, 
    mom_long=126, 
    lag_days=45,
    equity_list=EQUITY_UNIVERSE,
    bond_list=BOND_UNIVERSE
):
    regime = build_weekly_regime(start=DATA_START, end=DATA_END, prices=prices, lag_days=lag_days)
    sel = build_weekly_selections(
        prices=prices, volume=volume, regime=regime,
        equity_universe=equity_list, bond_universe=bond_list,
        momentum_short=mom_short, momentum_long=mom_long
    )
    engine = LadderEngine(
        initial_capital=INITIAL_CAPITAL,
        execution_lag=1,
        n_tranches=n_tranches,
        slippage=slippage,
        commission=commission
    )
    res = engine.run(prices=prices, selections=sel, start=OOS_START, end=OOS_END)
    # Return both metrics and the equity curve
    curve = res.daily["portfolio_value"]
    return compute_metrics(curve), curve

# ── [Exp 1] Cost Sensitivity ──
def exp_cost():
    print("\n[Exp 1] Cost Breakeven Analysis...")
    slips = [0.0, 0.0002, 0.0005, 0.0010, 0.0020, 0.0050]
    results = []
    curves = []
    for s in slips:
        m, c = run_backtest(slippage=s)
        results.append({"Slippage": f"{s*10000:.0f} bps", "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})
        curves.append(c.rename(f"{s*10000:.0f} bps"))
    
    # Plot cost decay
    plt.figure(figsize=(10, 6))
    for c in curves:
        plt.plot(c.index, c.values / 1e6, label=c.name)
    plt.title("Cost Impact on Portfolio Growth (Log Scale)")
    plt.yscale('log')
    # Granular Log-Scale Axis
    import matplotlib.ticker as mtick
    plt.gca().yaxis.set_major_locator(mtick.LogLocator(base=10, subs=[1.0, 2.0, 5.0]))
    plt.gca().yaxis.set_major_formatter(mtick.ScalarFormatter())
    plt.gca().get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    
    plt.ylabel("Portfolio Value ($M)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{PLOTS_DIR}research_1_cost_sensitivity.png")
    plt.close()
    return results

# ── [Exp 2] Momentum Sensitivity ──
def exp_mom():
    print("[Exp 2] Momentum Sensitivity Analysis...")
    windows = [(21, 63), (63, 126), (126, 252)]
    results = []
    for s, l in windows:
        m, _ = run_backtest(mom_short=s, mom_long=l)
        results.append({"Window": f"{s}/{l}d", "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})
    
    # Plot bar chart for CAGR vs Sharpe
    df = pd.DataFrame(results)
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()
    
    x = np.arange(len(df))
    width = 0.35
    
    ax1.bar(x - width/2, df['CAGR'], width, color='skyblue', label='CAGR')
    ax2.bar(x + width/2, df['Sharpe'], width, color='orange', label='Sharpe', alpha=0.7)
    
    ax1.set_ylabel('CAGR (%)', color='skyblue')
    ax2.set_ylabel('Sharpe Ratio', color='orange')
    ax1.yaxis.set_major_locator(plt.MaxNLocator(nbins=6))
    ax2.yaxis.set_major_locator(plt.MaxNLocator(nbins=6))
    plt.xticks(x, df['Window'])
    plt.title("Momentum Window Comparison")
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{PLOTS_DIR}research_2_momentum_windows.png")
    plt.close()
    return results

# ── [Exp 3] Tranche Smoothing ──
def exp_smoothing():
    print("[Exp 3] Tranche Smoothing Analysis...")
    tranches = [1, 4, 12]
    results = []
    curves = []
    for n in tranches:
        m, c = run_backtest(n_tranches=n)
        results.append({"Tranches": n, "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})
        curves.append(c.rename(f"{n} Tranches"))
    
    plt.figure(figsize=(10, 6))
    for c in curves:
        plt.plot(c.index, c.values / 1e6, label=c.name)
    plt.title("Effect of Laddered Smoothing on Equity Curve")
    plt.yscale('log')
    # Granular Log-Scale Axis
    import matplotlib.ticker as mtick
    plt.gca().yaxis.set_major_locator(mtick.LogLocator(base=10, subs=[1.0, 2.0, 5.0]))
    plt.gca().yaxis.set_major_formatter(mtick.ScalarFormatter())
    plt.gca().get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    
    plt.ylabel("Portfolio Value ($M)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{PLOTS_DIR}research_3_tranche_smoothing.png")
    plt.close()
    return results

# ── [Exp 4] Macro Lag Stress ──
def exp_lag():
    print("[Exp 4] Macro Lag Stress Analysis...")
    lags = [0, 45, 90, 180]
    results = []
    for l in lags:
        m, _ = run_backtest(lag_days=l)
        results.append({"Lag": f"{l} days", "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})
    
    df = pd.DataFrame(results)
    plt.figure(figsize=(10, 6))
    plt.plot(lags, df['CAGR'] * 100, marker='o', color='red', label='CAGR')
    plt.title("Performance Sensitivity to Reporting Lag")
    plt.xlabel("Reporting Lag (Days)")
    plt.ylabel("CAGR (%)")
    plt.gca().yaxis.set_major_locator(plt.MaxNLocator(nbins=8))
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{PLOTS_DIR}research_4_fundamental_lag.png")
    plt.close()
    return results

# ── [Exp 5] Universe Utility ──
def exp_universe():
    print("[Exp 5] Universe Utility Analysis...")
    results = []
    # Standard
    m_div, c_div = run_backtest()
    results.append({"Universe": "Diversified (Global)", "CAGR": m_div['cagr'], "Sharpe": m_div['sharpe'], "MaxDD": m_div['max_drawdown']})
    # Tech focus
    tech_universe = ["SPY", "QQQ", "XLK", "NVDA", "AAPL"]
    m_tech, c_tech = run_backtest(equity_list=tech_universe)
    results.append({"Universe": "US Tech Focus", "CAGR": m_tech['cagr'], "Sharpe": m_tech['sharpe'], "MaxDD": m_tech['max_drawdown']})
    
    plt.figure(figsize=(10, 6))
    plt.plot(c_div.index, c_div.values / 1e6, label="Global Diversification")
    plt.plot(c_tech.index, c_tech.values / 1e6, label="US Tech Concentration")
    plt.title("Alpha Comparison: Diversification vs Concentrated Tech")
    plt.yscale('log')
    # Granular Log-Scale Axis
    import matplotlib.ticker as mtick
    plt.gca().yaxis.set_major_locator(mtick.LogLocator(base=10, subs=[1.0, 2.0, 5.0]))
    plt.gca().yaxis.set_major_formatter(mtick.ScalarFormatter())
    plt.gca().get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    
    plt.ylabel("Portfolio Value ($M)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{PLOTS_DIR}research_5_universe_comparison.png")
    plt.close()
    return results

def to_md(results): # simplified for console output
    keys = list(results[0].keys())
    header = f"| {' | '.join(keys)} |"
    sep    = f"| {' | '.join(['---'] * len(keys))} |"
    print(header)
    print(sep)
    for r in results:
        v = [str(r[k]) if not isinstance(r[k], float) else f"{r[k]:+.2%}" if 'Sharpe' not in k else f"{r[k]:.3f}" for k in keys]
        print(f"| {' | '.join(v)} |")

# ── Execution ──
c_res = exp_cost()
m_res = exp_mom()
s_res = exp_smoothing()
l_res = exp_lag()
u_res = exp_universe()

print("\n... All Research Figures Generated in plots/research/ ...")
