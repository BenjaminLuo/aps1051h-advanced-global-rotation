"""
Janus Rotational System — Crisis Stress Experiment (2005–2024)
==============================================================
Compares 'Aggressive' vs 'Recovery' fundamental stress levels for the 2008 GFC.

Usage:
    python run_experiment.py
"""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path

from janus_rotational.config import (
    DATA_START, DATA_END, EQUITY_UNIVERSE, BOND_UNIVERSE, RANDOM_SEED
)
from janus_rotational.data.fetcher import fetch_equity_and_bond
from janus_rotational.execution.ladder import LadderEngine
from janus_rotational.regime.macro import build_weekly_regime
from janus_rotational.signals.selector import build_weekly_selections
from janus_rotational.analytics.metrics import compute_metrics
from janus_rotational.analytics.benchmarks import build_spy_benchmark, build_6040_benchmark

# Settings
OOS_START       = "2005-01-01"
OOS_END         = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0
RF              = 0.02

PLOT_DIR = Path("plots")
PLOT_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("run_experiment")

def run_scenario(severity: str, prices: pd.DataFrame, volume: pd.DataFrame):
    logger.info(f"--- Running Scenario: {severity.upper()} ---")
    
    # 1. Build Regime (with severity toggle)
    regime = build_weekly_regime(
        start=DATA_START, end=DATA_END, 
        prices=prices, stress_severity=severity
    )
    
    # 2. Build Selections
    selections = build_weekly_selections(
        prices=prices, volume=volume, regime=regime,
        equity_universe=EQUITY_UNIVERSE, bond_universe=BOND_UNIVERSE
    )
    
    # 3. Run Ladder
    # Categorization for granular tracking
    US_ETFS     = ["SPY", "QQQ", "DIA", "IWM", "MDY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLV"]
    GLOBAL_ETFS = ["EWC", "EFA", "EZU", "EWJ", "EWU", "EWG", "EWA", "EEM", "EWZ"]
    
    engine = LadderEngine(
        initial_capital = INITIAL_CAPITAL,
        execution_lag   = 1,
        asset_classes   = {
            "us_equity":     US_ETFS,
            "global_equity": GLOBAL_ETFS,
            "bond":          BOND_UNIVERSE,
        }
    )
    
    result = engine.run(
        prices=prices, selections=selections,
        start=OOS_START, end=OOS_END
    )
    
    return result.daily["portfolio_value"], regime

if __name__ == "__main__":
    # Fetch Data once
    universes = fetch_equity_and_bond(
        equity_universe=EQUITY_UNIVERSE,
        bond_universe=BOND_UNIVERSE,
        start=DATA_START,
        end=DATA_END
    )
    eq_prices, eq_vol     = universes["equity"]
    bond_prices, bond_vol = universes["bond"]
    prices = pd.concat([eq_prices, bond_prices], axis=1).sort_index()
    volume = pd.concat([eq_vol,    bond_vol],    axis=1).sort_index()

    # Run Scenarios
    curve_agg, reg_agg = run_scenario("aggressive", prices, volume)
    curve_rec, reg_rec = run_scenario("recovery",   prices, volume)

    # Benchmarks
    spy_curve  = build_spy_benchmark(prices, INITIAL_CAPITAL, OOS_START, OOS_END)
    bench_6040 = build_6040_benchmark(INITIAL_CAPITAL, OOS_START, OOS_END)

    # Alignment
    common_idx = curve_agg.index
    spy_curve  = spy_curve.reindex(common_idx, method="ffill")
    bench_6040 = bench_6040.reindex(common_idx, method="ffill")

    # Metrics
    m_agg  = compute_metrics(curve_agg, rf=RF)
    m_rec  = compute_metrics(curve_rec, rf=RF)
    m_spy  = compute_metrics(spy_curve, rf=RF)
    m_6040 = compute_metrics(bench_6040, rf=RF)

    # Display comparison
    print("\n" + "="*80)
    print(f"{'Metric':<20} {'Aggressive':>15} {'Recovery':>15} {'SPY':>15}")
    print("-" * 80)
    for k in ["cagr", "sharpe", "max_drawdown"]:
        fmt = "{:+.2%}" if "dd" in k or "cagr" in k else "{:.3f}"
        v_agg = fmt.format(m_agg[k])
        v_rec = fmt.format(m_rec[k])
        v_spy = fmt.format(m_spy[k])
        print(f"{k.upper():<20} {v_agg:>15} {v_rec:>15} {v_spy:>15}")
    print("="*80)

    # Plot Comparison
    plt.figure(figsize=(14, 7))
    plt.semilogy(curve_agg.index, curve_agg, color="#1B263B", label="Janus (Aggressive GFC Stress)", lw=1.8)
    plt.semilogy(curve_rec.index, curve_rec, color="#388E3C", label="Janus (Recovery GFC Stress)", lw=1.2, alpha=0.8, linestyle="--")
    plt.semilogy(spy_curve.index, spy_curve, color="#E63946", label="SPY (100%)", lw=1.2, alpha=0.5)
    
    plt.title("Janus Rotational System — GFC Stress Severity Experiment (2005–2024)", fontweight="bold")
    plt.ylabel("Log Portfolio Value (USD)")
    plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    save_path = PLOT_DIR / "experiment_gfc_comparison.png"
    plt.savefig(save_path, bbox_inches="tight", dpi=200)
    print(f"\nExperiment plot saved to: {save_path}")
