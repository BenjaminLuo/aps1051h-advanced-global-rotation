"""
Janus Rotational System — Benchmark Equity Curves
==================================================
Two benchmarks for the academic comparison:

  1. SPY (100%)   — passive large-cap US equity, the canonical equity benchmark.
  2. 60/40        — 60% ACWI (global equity) + 40% BND (US aggregate bond).
                    Represents a classic balanced portfolio.
                    Return blended daily at constant weights (no rebalancing
                    friction), which is standard practice for benchmark reporting.

Both are initialised to the same starting capital as the Janus system and
held from the first OOS trading day to the last.
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def build_spy_benchmark(
    prices:          pd.DataFrame,
    initial_capital: float,
    start:           str,
    end:             str,
) -> pd.Series:
    """
    100% SPY buy-and-hold from *start* to *end*.

    Uses the same adjusted-close prices already in *prices* to avoid
    a second download and guarantee identical adjustment factors.
    """
    spy = prices.loc[start:end, "SPY"].dropna()
    curve = initial_capital * spy / spy.iloc[0]
    curve.name = "SPY (100%)"
    return curve


def build_6040_benchmark(
    initial_capital: float,
    start:           str,
    end:             str,
) -> pd.Series:
    """
    60% SPY + 40% BIL (Risk-Free) daily-weighted buy-and-hold.

    This provides a cleaner 'Capital Markets Line' benchmark.
    Returns are blended at constant 60/40 weight each day.

    SPY: S&P 500 ETF (Full history)
    BIL: 1-3 Month T-Bill ETF (Launched 2007, proxy with SHY before)
    """
    logger.info("Fetching SPY, BIL, SHY for 60/40 benchmark [%s → %s]", start, end)
    raw = yf.download(
        ["SPY", "BIL", "SHY"],
        start=start, end=end,
        auto_adjust=True,
        progress=False,
    )
    prices_bm = raw["Close"].copy()
    prices_bm.columns = prices_bm.columns.get_level_values(-1) if hasattr(
        prices_bm.columns, "levels"
    ) else prices_bm.columns
    prices_bm = prices_bm.ffill()

    # ── Calculate returns and stitch at the return level ───────────────
    spy_rets = prices_bm["SPY"].pct_change()
    shy_rets = prices_bm["SHY"].pct_change()
    
    if "BIL" in prices_bm.columns:
        # Use BIL if available, otherwise SHY
        rf_rets = prices_bm["BIL"].pct_change().fillna(shy_rets)
    else:
        rf_rets = shy_rets

    # Blend at 60/40
    port_rets = 0.60 * spy_rets + 0.40 * rf_rets
    port_rets = port_rets.dropna()

    curve = initial_capital * (1.0 + port_rets).cumprod()
    # Prepend initial capital on the first valid index day
    t0 = pd.Series([initial_capital], index=[port_rets.index[0] - pd.Timedelta(days=1)], name=curve.name)
    curve = pd.concat([t0, curve])
    curve.name = "60/40 SPY/RiskFree"
    return curve
