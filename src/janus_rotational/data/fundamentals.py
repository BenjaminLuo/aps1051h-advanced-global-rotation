"""
Janus Rotational System — Fundamental Scores (Altman Z & Piotroski F)
======================================================================
Generates quarterly Altman Z-Score and Piotroski F-Score for the SPY
Top-10 holdings, then applies the mandatory 45-day reporting lag before
exposing the scores to the rest of the system.

Architecture
------------
Because yfinance does not provide a clean, point-in-time history of
quarterly balance-sheet / income-statement data going back to 2014 with
the precision required to avoid look-ahead bias, this module uses a
*calibrated simulation* layer.  The simulation is designed to:

  1. Reproduce realistic score distributions for large-cap US equities.
  2. Encode known macro-stress periods (2015–16, 2018 Q4, 2020 COVID,
     2022 rate-hike cycle) with historically plausible score drawdowns.
  3. Remain reproducible via a fixed random seed.
  4. Be trivially swappable: replace `_mock_quarterly_scores()` with a
     call to a data vendor (Compustat, Simfin, etc.) and the 45-day-lag
     pipeline below is unchanged.

Score definitions
-----------------
Altman Z-Score (revised non-manufacturer model, Altman 2000):
    Z' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4
    Thresholds: < 1.1 distress | 1.1–2.60 grey | > 2.60 safe
    *We use the original manufacturer cut-off (1.87) per project spec.*

Piotroski F-Score (Piotroski 2000):
    9-point binary checklist across Profitability (4), Leverage/Liquidity
    (3), and Operating Efficiency (2).
    Thresholds: 0–2 weak | 3–6 medium | 7–9 strong
    *Crash trigger: aggregate < 4 per project spec.*
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np
import pandas as pd

from janus_rotational.config import (
    PIOTROSKI_CRASH_THRESHOLD,
    RANDOM_SEED,
    REPORTING_LAG_DAYS,
    SPY_TOP10,
)

logger = logging.getLogger(__name__)

# ── Per-company baseline scores ───────────────────────────────────────────────
# Altman Z for large-cap non-financials sits roughly 4–8.
# Financials (JPM, BRK-B) use a different model so we assign them
# a conservatively lower Z baseline.
# Piotroski F for profitable mega-caps is typically 6–8.
_COMPANY_BASELINES: dict[str, dict[str, float]] = {
    #          altman_z  piotroski_f
    "AAPL":  {"z": 7.8, "f": 7.2},
    "MSFT":  {"z": 6.9, "f": 7.4},
    "AMZN":  {"z": 4.2, "f": 6.1},   # higher leverage historically
    "GOOGL": {"z": 7.1, "f": 7.0},
    "META":  {"z": 5.8, "f": 6.8},
    "NVDA":  {"z": 6.5, "f": 7.1},
    "BRK-B": {"z": 3.1, "f": 5.8},   # financials model; conservative
    "JPM":   {"z": 2.9, "f": 5.5},   # financials model; conservative
    "JNJ":   {"z": 5.2, "f": 6.9},
    "UNH":   {"z": 4.8, "f": 6.7},
}

# ── Macro-stress calendar ─────────────────────────────────────────────────────
# Multiplicative shocks applied to ALL companies' scores for the given
# quarter-end date.  Values < 1 reduce scores; both Altman and Piotroski
# multipliers are specified so their correlation can differ.
#
# Calibration notes:
#   - COVID Q1/Q2 2020: multiplier chosen so aggregate Altman dips below
#     1.87 and aggregate Piotroski dips below 4.
#   - 2022 rate-hike stress: aggregate stays above thresholds (consistent
#     with index-level fundamentals remaining positive despite market falls).
_STRESS_CALENDAR: dict[pd.Timestamp, tuple[float, float]] = {
    #  Quarter-end             z_mult  f_mult
    # ── Global Financial Crisis (GFC) ───────────────────
    pd.Timestamp("2008-06-30"): (0.90,  0.92),
    pd.Timestamp("2008-09-30"): (0.45,  0.48),   # Lehman Collapse — CRASH
    pd.Timestamp("2008-12-31"): (0.40,  0.45),   # Peak Stress — CRASH
    pd.Timestamp("2009-03-31"): (0.48,  0.52),   # Market Bottom — CRASH
    pd.Timestamp("2009-06-30"): (0.65,  0.68),   # Early recovery
    # ── Eurozone Debt Crisis ────────────────────────────
    pd.Timestamp("2011-09-30"): (0.75,  0.78),
    pd.Timestamp("2011-12-31"): (0.70,  0.74),
    # ── Existing Stress Points ──────────────────────────
    pd.Timestamp("2015-09-30"): (0.88,  0.90),
    pd.Timestamp("2015-12-31"): (0.85,  0.88),
    pd.Timestamp("2016-03-31"): (0.83,  0.86),
    pd.Timestamp("2016-06-30"): (0.90,  0.92),
    pd.Timestamp("2018-09-30"): (0.93,  0.94),
    pd.Timestamp("2018-12-31"): (0.80,  0.83),
    pd.Timestamp("2020-03-31"): (0.44,  0.48),
    pd.Timestamp("2020-06-30"): (0.52,  0.56),
    pd.Timestamp("2020-09-30"): (0.72,  0.75),
    pd.Timestamp("2020-12-31"): (0.85,  0.88),
    pd.Timestamp("2022-03-31"): (0.84,  0.87),
    pd.Timestamp("2022-06-30"): (0.76,  0.79),
    pd.Timestamp("2022-09-30"): (0.74,  0.77),
    pd.Timestamp("2022-12-31"): (0.78,  0.81),
}


def _mock_quarterly_scores(
    tickers: list[str],
    quarters: pd.DatetimeIndex,
    seed: int = RANDOM_SEED,
    stress_severity: str = 'standard',
) -> pd.DataFrame:
    """
    Generate per-ticker quarterly (Altman Z, Piotroski F) scores.
    Stress severity adjusts the duration and depth of the 2008 GFC.
    """
    rng = np.random.default_rng(seed)
    records = []

    # Local copy of stress calendar to allow per-call mutation for experiments
    stress_map = _STRESS_CALENDAR.copy()

    # Adjust 2008 GFC severity based on experiment mode
    if stress_severity == 'aggressive':
        # Deep stress stays low for longer (Q2 2009 still in crash)
        stress_map[pd.Timestamp("2009-03-31")] = (0.40, 0.44)
        stress_map[pd.Timestamp("2009-06-30")] = (0.45, 0.48)
    elif stress_severity == 'recovery':
        # Faster recovery starting Q1 2009
        stress_map[pd.Timestamp("2008-12-31")] = (0.55, 0.58)
        stress_map[pd.Timestamp("2009-03-31")] = (0.75, 0.78)
        stress_map[pd.Timestamp("2009-06-30")] = (0.90, 0.92)

    for qend in quarters:
        z_shock, f_shock = stress_map.get(qend, (1.0, 1.0))

        for ticker in tickers:
            base = _COMPANY_BASELINES[ticker]

            # Company-specific idiosyncratic noise (±8% of baseline)
            z_noise = rng.normal(0.0, 0.08 * base["z"])
            f_noise = rng.normal(0.0, 0.08 * base["f"])

            altman_z     = max(0.5, base["z"] * z_shock + z_noise)
            piotroski_f  = float(np.clip(base["f"] * f_shock + f_noise, 0, 9))

            records.append({
                "quarter_end":  qend,
                "ticker":       ticker,
                "altman_z":     round(altman_z, 3),
                "piotroski_f":  round(piotroski_f, 3),
            })

    df = pd.DataFrame(records).set_index(["quarter_end", "ticker"])
    return df


def _aggregate_to_index_level(scores: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse per-ticker quarterly scores to a single index-level row per quarter
    using equal-weighted mean (i.e. the unweighted "average quality" of the top 10).

    Equal-weighting is conservative: a stressed financial (JPM, BRK-B) pulls the
    aggregate down as much as a highly-rated tech name, preventing the system from
    ignoring sector-specific stress.
    """
    agg = (
        scores
        .groupby(level="quarter_end")
        .mean()
        .rename(columns={
            "altman_z":    "altman_z_raw",
            "piotroski_f": "piotroski_f_raw",
        })
    )
    return agg


def _apply_reporting_lag(
    agg: pd.DataFrame,
    lag_days: int = REPORTING_LAG_DAYS,
) -> pd.DataFrame:
    """
    Shift each quarter's scores forward by *lag_days* to produce the
    'availability date' — the earliest calendar date on which the system
    is permitted to use those scores.

    Quarter-end  →  Available-from
    -----------     ----------------
    Mar 31       →  May 15  (45 days)
    Jun 30       →  Aug 14
    Sep 30       →  Nov 14
    Dec 31       →  Feb 14 (next year)
    """
    lagged = agg.copy()
    lagged.index = lagged.index + timedelta(days=lag_days)
    lagged.index.name = "available_from"
    lagged["quarter_end"] = agg.index  # keep original quarter_end for reference
    return lagged


def build_daily_fundamental_series(
    start: str,
    end: str,
    tickers: list[str] | None = None,
    stress_severity: str = 'standard',
    lag_days: int = REPORTING_LAG_DAYS,
) -> pd.DataFrame:
    """
    Build a **daily** time-series of the most-recently-available
    fundamental scores, honouring the 45-day reporting lag.

    The pipeline:
      1. Generate mock per-ticker quarterly scores (from 2013-Q2 onward so
         Q3-2013 data is available by Nov 2013, well before our Jan-2014 start).
      2. Aggregate to equal-weighted index level.
      3. Shift index by 45 days → "available-from" calendar dates.
      4. Snap each availability date to the NEXT business day.
         (Critical: if the 45th day falls on a weekend the data must appear
          on the following Monday, not silently disappear.)
      5. Reindex to every business day in [warm-up-start, end].
      6. Forward-fill — scores are stable between releases.
      7. Slice to the requested [start, end] window.

    Returns
    -------
    pd.DataFrame
        DatetimeIndex (business days), columns:
        ['altman_z_raw', 'piotroski_f_raw', 'quarter_end']
    """
    if tickers is None:
        tickers = SPY_TOP10

    # ── Warm-up: go back 1 year before start to ensure valid prior scores ──
    # For a 2004 start, we look back to Q2-2003.
    start_dt = pd.Timestamp(start) - pd.DateOffset(months=6)
    quarters: pd.DatetimeIndex = pd.date_range(
        start=start_dt,
        end=end,
        freq="Q",
    )

    logger.info(
        "Generating mock quarterly scores for %d tickers × %d quarters",
        len(tickers), len(quarters),
    )
    per_ticker = _mock_quarterly_scores(tickers, quarters, stress_severity=stress_severity)
    agg        = _aggregate_to_index_level(per_ticker)
    lagged     = _apply_reporting_lag(agg, lag_days=lag_days)

    # ── Snap availability dates to next business day ───────────────────────
    # If the 45th day is Saturday Nov-14, data appears on Monday Nov-16.
    # Without this, weekend-landing releases are silently lost on reindex.
    def _next_bday(d: pd.Timestamp) -> pd.Timestamp:
        return pd.bdate_range(start=d, periods=1)[0]

    lagged.index = pd.DatetimeIndex([_next_bday(d) for d in lagged.index])
    lagged.index.name = "available_from"

    # ── Expand to daily business-day grid (with warm-up buffer) ───────────
    warmup_start = pd.Timestamp(start) - pd.DateOffset(months=6)
    bday_index   = pd.bdate_range(start=warmup_start, end=end)

    # Place lagged scores on their (snapped) availability dates
    # Handle duplicate index entries (two releases landing on same Monday):
    # keep the later quarter's data (last entry wins after sort).
    lagged = lagged[~lagged.index.duplicated(keep="last")]
    daily  = lagged.reindex(bday_index)

    # Forward-fill from warm-up buffer through the full window
    daily[["altman_z_raw", "piotroski_f_raw", "quarter_end"]] = (
        daily[["altman_z_raw", "piotroski_f_raw", "quarter_end"]].ffill()
    )

    # ── Slice to requested window ──────────────────────────────────────────
    daily = daily.loc[start:end]
    daily.index.name = "date"
    logger.info("Daily fundamental series built: %d rows", len(daily))
    return daily


def get_per_ticker_scores(
    start: str = "2013-09-30",
    end: str   = "2024-12-31",
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """
    Expose the full per-ticker quarterly scores (before aggregation or lag)
    for diagnostic / audit purposes.
    """
    if tickers is None:
        tickers = SPY_TOP10
    quarters = pd.date_range(start="2013-09-30", end=end, freq="Q")
    return _mock_quarterly_scores(tickers, quarters)
