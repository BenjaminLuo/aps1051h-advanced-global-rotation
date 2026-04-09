"""
Janus Rotational System — White's Reality Check (Bootstrap)
============================================================
Tests H0: the Janus annualised Sharpe Ratio is no better than a naive
random-selection strategy applied to the same universe and time period.

Method (as specified in the project brief)
------------------------------------------
  1. For each of N_SIMS simulations, on every Friday in the OOS window,
     randomly draw 3 ETFs (without replacement) from the COMBINED 30-ticker
     universe, equal-weight them, and record the weekly return.

  2. From the resulting weekly return series, compute the Annualised Sharpe
     Ratio.  Bootstrapping the SHARPE (not the mean return) avoids overstating
     the test statistic when strategies differ in volatility.

  3. The empirical p-value is:
       p = fraction of naive Sharpe Ratios >= Janus Sharpe Ratio

  A small p-value (< 0.05) means the null hypothesis can be rejected:
  the Janus Sharpe Ratio is statistically superior to random selection.

Implementation notes
--------------------
- Uses numpy vectorised fancy indexing: the full (n_sims × n_weeks × 3)
  return tensor is built in a single operation — no Python loops over sims.
- Janus Sharpe is also computed from weekly returns for methodological
  consistency with the naive distribution.
- Naive strategies have no transaction costs, which makes this a
  conservative (harder) test for Janus.

References
----------
White, H. (2000). A Reality Check for Data Snooping.
  Econometrica, 68(5), 1097–1126.
Hansen, P. R. (2005). A Test for Superior Predictive Ability.
  Journal of Business & Economic Statistics, 23(4), 365–380.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def run_whites_reality_check(
    janus_equity_curve: pd.Series,
    prices:             pd.DataFrame,
    oos_fridays:        list[pd.Timestamp],
    n_sims:             int   = 500,
    rf:                 float = 0.02,
    seed:               int   = 42,
) -> dict:
    """
    Execute the White's Reality Check bootstrap.

    Parameters
    ----------
    janus_equity_curve : pd.Series
        Daily portfolio value (from LadderResult.daily['portfolio_value']).
    prices : pd.DataFrame
        Daily adjusted-close prices for the COMBINED universe (30 tickers).
        Index = DatetimeIndex.
    oos_fridays : list of pd.Timestamp
        Ordered list of selection Fridays within the OOS window.
        These define the weekly holding periods.
    n_sims : int
        Number of naive strategy simulations.  Default 500.
    rf : float
        Annual risk-free rate.  Default 0.02.
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    dict with keys:
        janus_sharpe   — Janus annualised Sharpe (from weekly returns)
        naive_sharpes  — np.ndarray of length n_sims
        p_value        — empirical p-value
        n_sims, rf
        naive_mean, naive_std, naive_p5, naive_p50, naive_p95
    """
    # ── Janus weekly Sharpe ────────────────────────────────────────────────
    janus_weekly = janus_equity_curve.reindex(oos_fridays, method="ffill").dropna()
    j_weekly_rets = janus_weekly.pct_change().dropna().values

    j_ann_mean   = j_weekly_rets.mean() * 52.0 - rf
    j_ann_std    = j_weekly_rets.std()   * np.sqrt(52.0)
    janus_sharpe = j_ann_mean / j_ann_std

    logger.info(
        "Janus weekly Sharpe: %.4f  (ann_mean=%.4f  ann_std=%.4f)",
        janus_sharpe, j_ann_mean + rf, j_ann_std,
    )

    # ── Pre-compute weekly return matrix for all 30 tickers ───────────────
    # Shape: (n_weeks, n_tickers)
    # Align prices to the OOS Friday grid (ffill handles market-holiday Fridays)
    all_tickers  = sorted(prices.columns.tolist())
    price_weekly = prices[all_tickers].reindex(oos_fridays, method="ffill")
    weekly_rets  = price_weekly.pct_change().iloc[1:].values    # drop first NaN row
    n_weeks, n_tickers = weekly_rets.shape

    logger.info(
        "White's test: %d weeks × %d tickers → %d simulations",
        n_weeks, n_tickers, n_sims,
    )

    # ── Vectorised simulation ─────────────────────────────────────────────
    # Draw random ticker indices: shape (n_sims, n_weeks, 3)
    # rng.integers gives values in [0, n_tickers), no-replacement per row
    # handled by choice; for large n_tickers vs 3 picks, collisions are rare
    # but we enforce no-replacement with a shuffle-based approach below.
    rng = np.random.default_rng(seed)

    # (n_sims, n_weeks, n_tickers) shuffled indices; take first 3 → no replacement
    shuffle_idx = np.argsort(rng.random((n_sims, n_weeks, n_tickers)), axis=2)[:, :, :3]

    # Gather returns: weekly_rets[week, ticker]
    # row axis (n_sims, n_weeks, 3) → broadcast week index
    week_idx = np.arange(n_weeks)[np.newaxis, :, np.newaxis]          # (1, n_weeks, 1)
    sim_rets = weekly_rets[week_idx, shuffle_idx]                      # (n_sims, n_weeks, 3)

    # Equal-weight: (n_sims, n_weeks)
    port_rets = sim_rets.mean(axis=2)

    # Annualised Sharpe for all 500 sims at once
    ann_mean     = port_rets.mean(axis=1) * 52.0 - rf
    ann_std      = port_rets.std(axis=1)  * np.sqrt(52.0)
    naive_sharpes = ann_mean / ann_std                                  # (n_sims,)

    # Replace any NaN/Inf from zero-variance simulations
    naive_sharpes = naive_sharpes[np.isfinite(naive_sharpes)]

    p_value = float((naive_sharpes >= janus_sharpe).mean())

    logger.info(
        "White's Reality Check: Janus Sharpe=%.4f | "
        "Naive dist: mean=%.4f std=%.4f p95=%.4f | p-value=%.4f",
        janus_sharpe,
        naive_sharpes.mean(), naive_sharpes.std(),
        np.percentile(naive_sharpes, 95),
        p_value,
    )

    return {
        "janus_sharpe":  float(janus_sharpe),
        "naive_sharpes": naive_sharpes,
        "p_value":       p_value,
        "n_sims":        n_sims,
        "rf":            rf,
        "naive_mean":    float(naive_sharpes.mean()),
        "naive_std":     float(naive_sharpes.std()),
        "naive_p5":      float(np.percentile(naive_sharpes,  5)),
        "naive_p50":     float(np.percentile(naive_sharpes, 50)),
        "naive_p95":     float(np.percentile(naive_sharpes, 95)),
    }
