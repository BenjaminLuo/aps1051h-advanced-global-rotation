"""
Janus Rotational System — Phase 2: Weekly Signal Generation & Selection (v2.0)
===============================================================================
Janus 2.0 changes vs v1.0:

  1. DUAL MOMENTUM  — score = avg(63-day return, 126-day return)
     More responsive to recent acceleration while retaining medium-term
     trend confirmation.  Reduces lag at turning points.

  2. V-RATIO AS MULTIPLIER  — Final_Score = Dual_Momentum × V-Ratio_Rank
     The V-Ratio percentile rank within the active universe (0 to 1) is
     applied as a multiplicative discount.  High-volume, low-volatility
     ETFs receive full momentum credit; thin/choppy ETFs are discounted
     toward zero.  No hard bottom-25% cut — the multiplier handles it
     continuously and avoids binary cliff effects.

  3. TOP-5 SELECTIONS  — top_n = 5 (up from 3)
     Each tranche holds 5 ETFs at 20% each.  Broader diversification
     reduces idiosyncratic drawdown without sacrificing trend capture.

Pipeline (executed every Friday):
  Step 1 — Universe gate      (Phase 1 crash_regime → equity or bond)
  Step 2 — Dual momentum      (avg 63-day + 126-day return)
  Step 3 — V-Ratio multiplier (percentile rank as score weight)
  Step 4 — Select top-5       (highest Final_Score in active universe)
"""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
import pandas as pd

from janus_rotational.signals.momentum import compute_dual_momentum
from janus_rotational.signals.vratio   import compute_vratio

logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_MOMENTUM_SHORT: int = 63    # 3-month window
DEFAULT_MOMENTUM_LONG:  int = 126   # 6-month window
DEFAULT_VRATIO_WINDOW:  int = 20    # 1-month V-Ratio
DEFAULT_TOP_N:          int = 5     # Janus 2.0: top 5


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sample_weekly(daily: pd.DataFrame, friday_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Forward-fill daily signals onto the weekly Friday index."""
    return daily.reindex(friday_index, method="ffill")


def _select_one_week(
    mom_row:  pd.Series,
    vr_row:   pd.Series,
    universe: Sequence[str],
    top_n:    int,
) -> dict:
    """
    Core selection for a single Friday — Janus 2.0 logic.

    Algorithm
    ---------
    1. Intersect the active universe with tickers that have valid (non-NaN)
       dual-momentum AND V-Ratio values.
    2. Compute the cross-sectional percentile rank of V-Ratio (0 → 1).
       This maps the raw V-Ratio (billions) onto a uniform [0,1] scale.
    3. Final_Score = dual_momentum × v_ratio_rank
    4. Select the top-N by Final_Score.

    No hard filter is applied — the multiplier continuously discounts
    low-quality tickers rather than cutting them abruptly.
    """
    mom_u = mom_row.reindex(universe).dropna()
    vr_u  = vr_row.reindex(universe).dropna()
    valid  = mom_u.index.intersection(vr_u.index)

    if len(valid) == 0:
        return {
            "valid_tickers":   0,
            "after_vr_filter": 0,
            "selected":        [],
            "mom_scores":      {},
            "vr_scores":       {},
            "final_scores":    {},
        }

    mom_valid = mom_u[valid]
    vr_valid  = vr_u[valid]

    # V-Ratio percentile rank in [0,1]; highest V-Ratio → rank 1.0
    # .rank(pct=True) returns values in (0,1] (min = 1/n, max = 1)
    vr_rank = vr_valid.rank(pct=True)

    # Composite score: momentum weighted by V-Ratio quality
    final_score = mom_valid * vr_rank

    # Select top-N (clamp to available if fewer than top_n valid tickers)
    n_select = min(top_n, len(valid))
    selected = final_score.nlargest(n_select).index.tolist()

    return {
        "valid_tickers":   len(valid),
        "after_vr_filter": len(valid),   # no hard cut; kept for schema compat
        "selected":        selected,
        "mom_scores":      mom_valid[selected].to_dict(),
        "vr_scores":       vr_valid.reindex(selected).to_dict(),
        "final_scores":    final_score[selected].to_dict(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_weekly_selections(
    prices:               pd.DataFrame,
    volume:               pd.DataFrame,
    regime:               pd.DataFrame,
    equity_universe:      Sequence[str],
    bond_universe:        Sequence[str],
    momentum_short:       int = DEFAULT_MOMENTUM_SHORT,
    momentum_long:        int = DEFAULT_MOMENTUM_LONG,
    vratio_window:        int = DEFAULT_VRATIO_WINDOW,
    top_n:                int = DEFAULT_TOP_N,
) -> pd.DataFrame:
    """
    Build the complete weekly selection table (Janus 2.0).

    Parameters
    ----------
    prices, volume : pd.DataFrame
        Daily total-return-adjusted close and volume for the combined universe.
    regime : pd.DataFrame
        Output of `regime.macro.build_weekly_regime()`.
    equity_universe, bond_universe : sequences of str
    momentum_short : int
        Short momentum window in trading days.  Default 63 (3 months).
    momentum_long : int
        Long momentum window in trading days.  Default 126 (6 months).
    vratio_window : int
        V-Ratio rolling window.  Default 20 (1 month).
    top_n : int
        Final selections per Friday.  Default 5.

    Returns
    -------
    pd.DataFrame  (index = friday_date)
        crash_regime | active_universe | universe_size | valid_signals |
        rank_1 .. rank_{top_n} | mom_1 .. mom_{top_n} |
        vr_1 .. vr_{top_n} | final_1 .. final_{top_n}
    """
    eq_avail   = [t for t in equity_universe if t in prices.columns]
    bond_avail = [t for t in bond_universe   if t in prices.columns]

    missing_eq   = set(equity_universe) - set(eq_avail)
    missing_bond = set(bond_universe)   - set(bond_avail)
    if missing_eq or missing_bond:
        logger.warning("Missing tickers — equity: %s  bond: %s",
                       sorted(missing_eq), sorted(missing_bond))

    logger.info(
        "Computing signals: dual_mom(%d/%d-day) | V-Ratio(%d-day) × rank | "
        "top-%d | equity=%d bond=%d",
        momentum_short, momentum_long, vratio_window,
        top_n, len(eq_avail), len(bond_avail),
    )

    # ── Daily signals on the full combined universe ───────────────────────
    all_cols  = sorted(set(eq_avail) | set(bond_avail))
    mom_daily = compute_dual_momentum(
        prices[all_cols],
        window_short=momentum_short,
        window_long=momentum_long,
    )
    vr_daily  = compute_vratio(prices[all_cols], volume[all_cols], window=vratio_window)

    # ── Sample to weekly Friday grid ──────────────────────────────────────
    friday_idx = regime.index
    mom_weekly = _sample_weekly(mom_daily, friday_idx)
    vr_weekly  = _sample_weekly(vr_daily,  friday_idx)

    # ── Per-Friday selection loop ─────────────────────────────────────────
    records: list[dict] = []

    for friday in friday_idx:
        crash    = bool(regime.loc[friday, "crash_regime"])
        universe = bond_avail if crash else eq_avail

        result = _select_one_week(
            mom_row  = mom_weekly.loc[friday],
            vr_row   = vr_weekly.loc[friday],
            universe = universe,
            top_n    = top_n,
        )

        row: dict = {
            "crash_regime":    crash,
            "active_universe": "bond" if crash else "equity",
            "universe_size":   len(universe),
            "valid_signals":   result["valid_tickers"],
            "after_vr_filter": result["after_vr_filter"],
        }

        sel = result["selected"]
        for i in range(top_n):
            ticker = sel[i] if i < len(sel) else None
            row[f"rank_{i+1}"]  = ticker
            row[f"mom_{i+1}"]   = round(result["mom_scores"].get(ticker,   np.nan), 4) if ticker else np.nan
            row[f"vr_{i+1}"]    = round(result["vr_scores"].get(ticker,    np.nan), 0) if ticker else np.nan
            row[f"final_{i+1}"] = round(result["final_scores"].get(ticker, np.nan), 6) if ticker else np.nan

        records.append({"friday_date": friday, **row})

    selections = pd.DataFrame(records).set_index("friday_date")
    selections.index.name = "friday_date"

    crash_count = int(selections["crash_regime"].sum())
    logger.info(
        "Selections built: %d Fridays | %d crash (bond) | %d normal (equity)",
        len(selections), crash_count, len(selections) - crash_count,
    )
    return selections


def build_long_form(selections: pd.DataFrame, top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    """Long-form: one row per (friday_date, rank). Used by analytics modules."""
    rows = []
    for friday, row in selections.iterrows():
        for i in range(1, top_n + 1):
            ticker = row.get(f"rank_{i}")
            if pd.isna(ticker):
                continue
            rows.append({
                "friday_date":     friday,
                "crash_regime":    row["crash_regime"],
                "active_universe": row["active_universe"],
                "rank":            i,
                "ticker":          ticker,
                "momentum_dual":   row.get(f"mom_{i}"),
                "vratio_20d":      row.get(f"vr_{i}"),
                "final_score":     row.get(f"final_{i}"),
            })
    return pd.DataFrame(rows).set_index("friday_date")
