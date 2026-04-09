"""
Janus Rotational System — Regime-Partitioned Backtest (2005–2024)
================================================================
Runs the full system across three specific market regimes:
  1. GFC & Recovery (2005–2010)
  2. The Long Bull   (2011–2019)
  3. Modern Vol      (2020–2024)

Generates dedicated figures and a comparative KPI table.
"""

import logging
import pandas as pd
from pathlib import Path

from janus_rotational.config import (
    DATA_START, DATA_END, EQUITY_UNIVERSE, BOND_UNIVERSE
)
from janus_rotational.data.fetcher import fetch_equity_and_bond
from janus_rotational.execution.ladder import LadderEngine
from janus_rotational.regime.macro import build_weekly_regime
from janus_rotational.signals.selector import build_weekly_selections
from janus_rotational.analytics.metrics import compute_metrics
from janus_rotational.analytics.benchmarks import build_spy_benchmark, build_6040_benchmark
from janus_rotational.analytics.plots import (
    plot_regime_overlay, plot_capital_allocation, 
    plot_equity_and_drawdown, plot_whites_test
)
from janus_rotational.analytics.whites_test import run_whites_reality_check

# Configuration
INITIAL_CAPITAL = 1_000_000.0
RF              = 0.02

REGIMES = [
    {"name": "1_GFC",    "start": "2005-01-01", "end": "2010-12-31", "title": "(2005–2010: GFC & Recovery)"},
    {"name": "2_Bull",   "start": "2011-01-01", "end": "2019-12-31", "title": "(2011–2019: The Long Bull)"},
    {"name": "3_Modern", "start": "2020-01-01", "end": "2024-12-31", "title": "(2020–2024: Pandemic & Inflation)"},
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("run_regimes")

def run_single_regime(name, start, end, title, prices, volume):
    logger.info(f"\n>>> ANALYSING REGIME: {name} [{start} to {end}]")
    
    out_dir = Path("plots") / f"regime_{name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Build Regime
    regime = build_weekly_regime(start=DATA_START, end=DATA_END, prices=prices)
    
    # 2. Build Selections
    selections = build_weekly_selections(
        prices=prices, volume=volume, regime=regime,
        equity_universe=EQUITY_UNIVERSE, bond_universe=BOND_UNIVERSE
    )
    
    # 3. Run Ladder
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
    
    result = engine.run(prices=prices, selections=selections, start=start, end=end)
    
    # 4. Benchmarks
    spy_curve  = build_spy_benchmark(prices, INITIAL_CAPITAL, start, end)
    bench_6040 = build_6040_benchmark(INITIAL_CAPITAL, start, end)
    
    # 5. Metrics
    common_idx = result.daily.index
    spy_aligned = spy_curve.reindex(common_idx, method="ffill")
    b6040_aligned = bench_6040.reindex(common_idx, method="ffill")
    
    m_janus = compute_metrics(result.daily["portfolio_value"], rf=RF)
    m_spy   = compute_metrics(spy_aligned, rf=RF)
    m_6040  = compute_metrics(b6040_aligned, rf=RF)
    
    metrics_sum = {"janus": m_janus, "spy": m_spy, "6040": m_6040}
    
    # 6. White's Reality Check
    logger.info("  Running White's Reality Check (500 sims)...")
    oos_fridays = selections.loc[start:end].index.tolist()
    whites = run_whites_reality_check(
        janus_equity_curve = result.daily["portfolio_value"],
        prices             = prices,
        oos_fridays        = oos_fridays,
        rf                 = RF
    )
    
    # 7. Plots
    logger.info("  Generating figures...")
    start_fig = 5 + (REGIMES.index(next(r for r in REGIMES if r["name"] == name)) * 4)
    
    plot_regime_overlay(
        prices, regime, start, end, 
        output_dir=out_dir, title_suffix=title, fig_num=start_fig
    )
    plot_capital_allocation(
        result.daily, regime, 
        output_dir=out_dir, title_suffix=title, fig_num=start_fig+1
    )
    plot_equity_and_drawdown(
        result.daily["portfolio_value"], spy_aligned, b6040_aligned, 
        regime, metrics_sum, output_dir=out_dir, title_suffix=title, fig_num=start_fig+2
    )
    plot_whites_test(
        whites, output_dir=out_dir, title_suffix=title, fig_num=start_fig+3
    )
    
    return {
        "regime": name,
        "Janus_CAGR": m_janus["cagr"],
        "Janus_Sharpe": m_janus["sharpe"],
        "Janus_DD": m_janus["max_drawdown"],
        "SPY_CAGR": m_spy["cagr"],
        "Bench_CAGR": m_6040["cagr"],
        "p_value": whites["p_value"]
    }

if __name__ == "__main__":
    # Fetch data once
    universes = fetch_equity_and_bond(
        equity_universe=EQUITY_UNIVERSE,
        bond_universe=BOND_UNIVERSE,
        start=DATA_START,
        end=DATA_END
    )
    eq_p, eq_v = universes["equity"]
    bn_p, bn_v = universes["bond"]
    prices = pd.concat([eq_p, bn_p], axis=1).sort_index()
    volume = pd.concat([eq_v, bn_v], axis=1).sort_index()

    records = []
    for reg in REGIMES:
        res = run_single_regime(
            reg["name"], reg["start"], reg["end"], reg["title"], 
            prices, volume
        )
        records.append(res)

    # Summary Table
    df = pd.DataFrame(records).set_index("regime")
    print("\n" + "="*95)
    print("REGIME-PARTITIONED PERFORMANCE SUMMARY (2005-2024)")
    print("="*95)
    print(df.to_string(formatters={
        "Janus_CAGR": "{:+.2%}".format,
        "Janus_DD":   "{:+.2%}".format,
        "SPY_CAGR":   "{:+.2%}".format,
        "Bench_CAGR": "{:+.2%}".format,
        "Janus_Sharpe": "{:.3f}".format,
        "p_value":    "{:.4f}".format,
    }))
    print("="*95)
    print("All figures saved to plots/regime_*/ subdirectories.")
