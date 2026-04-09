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
    60% ACWI + 40% BND daily-weighted buy-and-hold.

    Fetches ACWI and BND from yfinance (auto_adjust=True for total return).
    Returns are blended at constant 60/40 weight each day — this is
    mathematically equivalent to continuous rebalancing and is the standard
    methodology for balanced benchmark reporting.

    ACWI: iShares MSCI ACWI ETF  (launched 2008-01-08)
    BND:  Vanguard Total Bond ETF (launched 2007-04-10)
    """
    logger.info("Fetching ACWI and BND for 60/40 benchmark [%s → %s]", start, end)
    raw = yf.download(
        ["ACWI", "BND"],
        start=start, end=end,
        auto_adjust=True,
        progress=False,
    )
    prices_bm = raw["Close"].copy()
    prices_bm.columns = prices_bm.columns.get_level_values(-1) if hasattr(
        prices_bm.columns, "levels"
    ) else prices_bm.columns
    prices_bm = prices_bm.ffill().dropna()

    rets = prices_bm.pct_change().dropna()
    port_rets = 0.60 * rets["ACWI"] + 0.40 * rets["BND"]

    curve = initial_capital * (1.0 + port_rets).cumprod()
    # Prepend the initial capital on the day before the first return
    t0 = pd.Series([initial_capital], index=[prices_bm.index[0]], name=curve.name)
    curve = pd.concat([t0, curve])
    curve.name = "60/40 ACWI/BND"
    return curve
