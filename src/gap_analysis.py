
import pandas as pd
import numpy as np
import logging
from janus_rotational.config import (
    BOND_UNIVERSE, DATA_END, DATA_START, EQUITY_UNIVERSE,
)
from janus_rotational.data.fetcher import fetch_equity_and_bond
from janus_rotational.execution.ladder import LadderEngine
from janus_rotational.regime.macro import build_weekly_regime
from janus_rotational.signals.selector import build_weekly_selections
from janus_rotational.analytics.metrics import compute_metrics
from janus_rotational.analytics.benchmarks import build_spy_benchmark, build_6040_benchmark

# ── Setup ──
OOS_START = "2005-01-01"
OOS_END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0

universes = fetch_equity_and_bond(EQUITY_UNIVERSE, BOND_UNIVERSE, DATA_START, DATA_END)
eq_prices, eq_vol = universes["equity"]
bond_prices, bond_vol = universes["bond"]
prices = pd.concat([eq_prices, bond_prices], axis=1).sort_index()
volume = pd.concat([eq_vol, bond_vol], axis=1).sort_index()
regime = build_weekly_regime(start=DATA_START, end=DATA_END)
selections = build_weekly_selections(prices, volume, regime, EQUITY_UNIVERSE, BOND_UNIVERSE)

def run_sim(slippage, commission, lag):
    engine = LadderEngine(
        initial_capital=INITIAL_CAPITAL,
        execution_lag=lag,
        n_tranches=4,
        slippage=slippage,
        commission=commission
    )
    res = engine.run(prices=prices, selections=selections, start=OOS_START, end=OOS_END)
    return compute_metrics(res.daily["portfolio_value"])

# 1. Baseline
m_base = run_sim(0.0002, 0.005, 1)

# 2. No Friction
m_no_fric = run_sim(0.0, 0.0, 1)

# 3. No Lag
m_no_lag = run_sim(0.0002, 0.005, 0)

# 4. No Friction + No Lag
m_perfect = run_sim(0.0, 0.0, 0)

# ── Output Report ──
spy_curve = build_spy_benchmark(prices, INITIAL_CAPITAL, OOS_START, OOS_END)
m_spy = compute_metrics(spy_curve)
bm_6040 = build_6040_benchmark(INITIAL_CAPITAL, OOS_START, OOS_END)
m_6040 = compute_metrics(bm_6040)

print("\n" + "="*50)
print("PERFORMANCE ATTRIBUTION ANALYSIS")
print("="*50)
print(f"{'Scenario':<25} {'CAGR':>10} {'MaxDD':>10} {'Sharpe':>10}")
print("-" * 50)
print(f"{'Janus (Baseline)':<25} {m_base['cagr']:>10.2%} {m_base['max_drawdown']:>10.2%} {m_base['sharpe']:>10.4f}")
print(f"{'Janus (No Friction)':<25} {m_no_fric['cagr']:>10.2%} {m_no_fric['max_drawdown']:>10.2%} {m_no_fric['sharpe']:>10.4f}")
print(f"{'Janus (No Lag)':<25} {m_no_lag['cagr']:>10.2%} {m_no_lag['max_drawdown']:>10.2%} {m_no_lag['sharpe']:>10.4f}")
print(f"{'Janus (Fric + Lag Free)':<25} {m_perfect['cagr']:>10.2%} {m_perfect['max_drawdown']:>10.2%} {m_perfect['sharpe']:>10.4f}")
print("-" * 50)
print(f"{'Benchmark (SPY)':<25} {m_spy['cagr']:>10.2%} {m_spy['max_drawdown']:>10.2%} {m_spy['sharpe']:>10.4f}")
print(f"{'Benchmark (60/40)':<25} {m_6040['cagr']:>10.2%} {m_6040['max_drawdown']:>10.2%} {m_6040['sharpe']:>10.4f}")

fric_drag = m_no_fric['cagr'] - m_base['cagr']
lag_drag = m_no_lag['cagr'] - m_base['cagr']
selection_alpha = m_perfect['cagr'] - m_spy['cagr']

print("\nKey Takeaways:")
print(f"1. Friction Drag   : {fric_drag:>7.2%} (CAGR lost to slippage/comm)")
print(f"2. Execution Lag   : {lag_drag:>7.2%} (CAGR lost to T+1 timing)")
print(f"3. Selection Alpha : {selection_alpha:>7.2%} (Janus assets vs broad market INDEX-only)")
print("="*50)
