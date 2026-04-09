"""
Janus Rotational System — Phase 1: Global Macro Regime Switch (v2.0)
=====================================================================
Janus 2.0 adds a TECHNICAL FILTER alongside the original fundamental filter.

Double-Filter logic (OR combination):
  Fundamental crash = Altman Z < 1.87  OR  Piotroski F < 4
  Technical crash   = SPY Close < 200-day SMA

  crash_regime = fundamental_crash  OR  technical_crash

Rationale
---------
The fundamental filter (45-day lag) is inherently slow: it can only react to
deteriorating balance-sheet data published six weeks after quarter-end.
The technical filter fires immediately when price crosses below the 200-day
moving average — a well-established trend-following signal that captures:
  • 2015–16 commodity / EM slowdown
  • 2018 Q4 rate-shock
  • 2020 COVID sell-off (fires ~4 weeks EARLIER than the fundamental filter)
  • 2022 rate-hike cycle (active for most of the year)

The OR combination ensures the system rotates to bonds as soon as EITHER
signal fires, then exits only when BOTH are clear — a conservative "last man
standing" approach to drawdown protection.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from janus_rotational.config import (
    ALTMAN_CRASH_THRESHOLD,
    PIOTROSKI_CRASH_THRESHOLD,
    SMA_CRASH_WINDOW,
)
from janus_rotational.data.fundamentals import build_daily_fundamental_series

logger = logging.getLogger(__name__)


def build_weekly_regime(
    start:               str   = "2014-01-01",
    end:                 str   = "2024-12-31",
    prices:              pd.DataFrame | None = None,
    altman_threshold:    float = ALTMAN_CRASH_THRESHOLD,
    piotroski_threshold: float = PIOTROSKI_CRASH_THRESHOLD,
    sma_window:          int   = SMA_CRASH_WINDOW,
    stress_severity:     str   = 'standard',
    lag_days:            int   = 45,
) -> pd.DataFrame:
    """
    Build the weekly Friday macro-regime flag (Janus 2.0 double-filter).

    Parameters
    ----------
    start, end : str
        Analysis window.
    prices : pd.DataFrame, optional
        Daily adjusted-close prices containing at least a 'SPY' column.
        When supplied, the 200-day SMA technical filter is active.
        When None, only the fundamental filter runs (v1 behaviour).
    altman_threshold : float
        Altman Z crash threshold.  Default 1.87.
    piotroski_threshold : float
        Piotroski F crash threshold.  Default 4.
    sma_window : int
        SMA look-back for the technical filter.  Default 200.
    stress_severity : str
        Experiment mode: 'standard', 'aggressive', or 'recovery'.

    Returns
    -------
    pd.DataFrame (index = friday_date) with columns:
        quarter_end, days_since_qend,
        altman_z, piotroski_f,
        altman_trigger, piotroski_trigger, fundamental_crash,
        spy_price, spy_sma_200, technical_crash,
        crash_regime  (= fundamental_crash OR technical_crash)
    """
    daily = build_daily_fundamental_series(start=start, end=end, stress_severity=stress_severity, lag_days=lag_days)

    fridays_mask = daily.index.weekday == 4
    weekly = daily.loc[fridays_mask].copy()

    if weekly.empty:
        raise ValueError("No Friday business days found in the specified range.")

    # ── Fundamental signals ───────────────────────────────────────────────
    weekly["altman_z"]    = weekly["altman_z_raw"].round(3)
    weekly["piotroski_f"] = weekly["piotroski_f_raw"].round(3)

    weekly["days_since_qend"] = (
        (weekly.index - pd.to_datetime(weekly["quarter_end"])).dt.days
    )

    weekly["altman_trigger"]    = weekly["altman_z"]    < altman_threshold
    weekly["piotroski_trigger"] = weekly["piotroski_f"] < piotroski_threshold
    weekly["fundamental_crash"] = weekly["altman_trigger"] | weekly["piotroski_trigger"]

    # ── Technical filter: SMA-200 + MACD Confirmation ───────────────────
    if prices is not None and "SPY" in prices.columns:
        spy_daily = prices.loc[start:end, "SPY"].dropna()

        # 1. Primary Trend (SMA)
        sma_daily = spy_daily.rolling(sma_window, min_periods=sma_window).mean()

        # 2. Momentum Confirmation (MACD 12/26)
        exp1 = spy_daily.ewm(span=12, adjust=False).mean()
        exp2 = spy_daily.ewm(span=26, adjust=False).mean()
        macd_daily = exp1 - exp2

        # Confirmation Logic: Both Trend and Momentum must be bearish
        # This prevents whipsaws during 'shallow' price breaks
        below_sma  = (spy_daily < sma_daily)
        neg_macd   = (macd_daily < 0)
        crash_bool = below_sma & neg_macd

        # Sample to Friday grid (forward-fill handles holiday Fridays)
        weekly["spy_price"]   = spy_daily.reindex(weekly.index, method="ffill")
        weekly["spy_sma_200"] = sma_daily.reindex(weekly.index, method="ffill").round(2)
        weekly["spy_macd"]    = macd_daily.reindex(weekly.index, method="ffill").round(3)
        weekly["technical_crash"] = (
            crash_bool.reindex(weekly.index, method="ffill").fillna(False)
        )
        logger.info(
            "Technical filter active (Confirm: SMA-%d & MACD < 0): %d crash Fridays",
            sma_window,
            int(weekly["technical_crash"].sum()),
        )
    else:
        weekly["spy_price"]       = np.nan
        weekly["spy_sma_200"]     = np.nan
        weekly["spy_macd"]        = np.nan
        weekly["technical_crash"] = False
        logger.info("Technical filter inactive (no prices supplied — v1 mode)")

    # ── Combined regime (OR logic) ────────────────────────────────────────
    weekly["crash_regime"] = weekly["fundamental_crash"] | weekly["technical_crash"]

    # ── Column order for readability ──────────────────────────────────────
    weekly = weekly[[
        "quarter_end",
        "days_since_qend",
        "altman_z",
        "piotroski_f",
        "altman_trigger",
        "piotroski_trigger",
        "fundamental_crash",
        "spy_price",
        "spy_sma_200",
        "spy_macd",
        "technical_crash",
        "crash_regime",
    ]]
    weekly.index.name = "friday_date"

    logger.info(
        "Weekly regime built: %d Fridays | %d crash weeks (%.1f%%) "
        "[fundamental=%d  technical=%d  overlap=%d]",
        len(weekly),
        int(weekly["crash_regime"].sum()),
        100.0 * weekly["crash_regime"].mean(),
        int(weekly["fundamental_crash"].sum()),
        int(weekly["technical_crash"].sum()),
        int((weekly["fundamental_crash"] & weekly["technical_crash"]).sum()),
    )
    return weekly


def regime_summary(weekly: pd.DataFrame) -> pd.DataFrame:
    """Annual breakdown of crash weeks by trigger type."""
    annual = (
        weekly
        .groupby(weekly.index.year)
        .agg(
            total_fridays      = ("crash_regime",      "count"),
            crash_fridays      = ("crash_regime",      "sum"),
            fundamental_only   = ("fundamental_crash", lambda x:
                                  (x & ~weekly.loc[x.index, "technical_crash"]).sum()),
            technical_only     = ("technical_crash",   lambda x:
                                  (x & ~weekly.loc[x.index, "fundamental_crash"]).sum()),
            both_triggers      = ("crash_regime",      lambda x:
                                  (weekly.loc[x.index, "fundamental_crash"] &
                                   weekly.loc[x.index, "technical_crash"]).sum()),
            avg_altman_z       = ("altman_z",           "mean"),
            avg_piotroski_f    = ("piotroski_f",        "mean"),
        )
    )
    annual["crash_pct"] = (annual["crash_fridays"] / annual["total_fridays"] * 100).round(1)
    return annual
