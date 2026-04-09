
import logging
import pandas as pd
import numpy as np
from janus_rotational.config import (
    BOND_UNIVERSE, DATA_END, DATA_START, EQUITY_UNIVERSE,
)
from janus_rotational.data.fetcher import fetch_equity_and_bond
from janus_rotational.execution.ladder import LadderEngine
from janus_rotational.regime.macro import build_weekly_regime
from janus_rotational.signals.selector import build_weekly_selections
from janus_rotational.analytics.metrics import compute_metrics
from janus_rotational.analytics.benchmarks import build_6040_benchmark

# ── Suppression ──
logging.basicConfig(level=logging.ERROR)
import warnings
warnings.filterwarnings("ignore")

# ── Setup ──
OOS_START = "2005-01-01"
OOS_END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0

print("... Initializing data for Multiverse Research ...")
# Expanded universe to include individual stocks for Experiment 5
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
    # 1. Regime
    regime = build_weekly_regime(start=DATA_START, end=DATA_END, prices=prices, lag_days=lag_days)
    # 2. Selections
    sel = build_weekly_selections(
        prices=prices, volume=volume, regime=regime,
        equity_universe=equity_list, bond_universe=bond_list,
        momentum_short=mom_short, momentum_long=mom_long
    )
    # 3. Execution
    engine = LadderEngine(
        initial_capital=INITIAL_CAPITAL,
        execution_lag=1,
        n_tranches=n_tranches,
        slippage=slippage,
        commission=commission
    )
    res = engine.run(prices=prices, selections=sel, start=OOS_START, end=OOS_END)
    return compute_metrics(res.daily["portfolio_value"])

# ── EXPERIMENT 1: Cost Breakeven ──
print("\n[Exp 1] Running Cost Breakeven Analysis...")
cost_results = []
for slip in [0.0, 0.0002, 0.0005, 0.0010, 0.0020]:
    m = run_backtest(slippage=slip)
    cost_results.append({"Slippage": f"{slip*10000:.0f} bps", "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})

# ── EXPERIMENT 2: Momentum Sensitivity ──
print("[Exp 2] Running Momentum Sensitivity Analysis...")
mom_results = []
for short, long in [(21, 63), (63, 126), (126, 252)]:
    m = run_backtest(mom_short=short, mom_long=long)
    mom_results.append({"Window": f"{short}/{long}d", "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})

# ── EXPERIMENT 3: Tranche Smoothing ──
print("[Exp 3] Running Tranche Smoothing Analysis...")
tranche_results = []
for n in [1, 4, 12]:
    m = run_backtest(n_tranches=n)
    tranche_results.append({"Tranches": n, "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})

# ── EXPERIMENT 4: Macro Lag Stress ──
print("[Exp 4] Running Macro Lag Stress Analysis...")
lag_results = []
for lag in [0, 45, 90]:
    m = run_backtest(lag_days=lag)
    lag_results.append({"Lag": f"{lag} days", "CAGR": m['cagr'], "Sharpe": m['sharpe'], "MaxDD": m['max_drawdown']})

# ── EXPERIMENT 5: Universe Utility ──
print("[Exp 5] Running Universe Utility Analysis...")
US_TECH = ["SPY", "QQQ", "XLK", "NVDA", "AAPL"] # Proxy for US Tech Focus
uni_results = []
# Standard (Diversified)
m_div = run_backtest()
uni_results.append({"Universe": "Diversified (30)", "CAGR": m_div['cagr'], "Sharpe": m_div['sharpe'], "MaxDD": m_div['max_drawdown']})
# US Tech Focus
m_tech = run_backtest(equity_list=US_TECH)
uni_results.append({"Universe": "US Tech Focus", "CAGR": m_tech['cagr'], "Sharpe": m_tech['sharpe'], "MaxDD": m_tech['max_drawdown']})

# ── Final Reporting ──
def to_md(results, title):
    if not results:
        return
    
    keys = list(results[0].keys())
    
    # Headers
    header = f"\n### {title}\n\n| {' | '.join(keys)} |"
    sep    = f"| {' | '.join(['---'] * len(keys))} |"
    
    # Rows
    rows = []
    for r in results:
        row_vals = []
        for k in keys:
            val = r[k]
            if isinstance(val, float):
                if k in ['CAGR', 'MaxDD']:
                    val = f"{val:+.2%}"
                elif k == 'Sharpe':
                    val = f"{val:.4f}"
            row_vals.append(str(val))
        rows.append(f"| {' | '.join(row_vals)} |")
    
    print(header)
    print(sep)
    print("\n".join(rows))

print("\n" + "="*80)
print("RESEARCH REPORT: ROBUSTNESS & SENSITIVITY")
print("="*80)
to_md(cost_results, "Cost Breakeven (Friction vs. CAGR)")
to_md(mom_results, "Momentum Windows (Speed vs. Stability)")
to_md(tranche_results, "Laddering Config (Smoothing vs. Latency)")
to_md(lag_results, "Fundamental Reporting Lag Stress")
to_md(uni_results, "Universe Composition Utility")
