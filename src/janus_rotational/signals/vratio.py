"""
Janus Rotational System — V-Ratio (Volume/Volatility) Filter Signal
====================================================================
Computes the V-Ratio for every ETF as a composite liquidity-quality filter.

Definition
----------
    V-Ratio(t, n) = RollingMean(Volume, n) / RollingStd(DailyReturn, n)

Interpretation
--------------
Numerator:   Average daily dollar-volume proxy — larger → easier to execute.
Denominator: Realised volatility — larger → choppier, mean-reversion-prone price.

A *high* V-Ratio means the ETF is trading heavily relative to how erratic it is
— the combination of liquidity and stability we want.  A *low* V-Ratio flags
either thinly-traded ETFs (e.g. EWZ in emerging-market stress) or excessively
volatile ones (e.g. NVDA during 2022 drawdown).

Usage in the system
-------------------
On each Friday the bottom 25th-percentile of V-Ratio within the *active
universe* is discarded.  The momentum ranking then applies only to the
surviving tickers.  This prevents the system from selecting a trending-but-
illiquid ticker that would gap on execution.

Design notes
------------
- `min_periods=window` enforces strict data coverage; partial-window values
  would otherwise distort the percentile cutoff at series start.
- Division-by-zero (zero-volatility period) replaced with NaN to prevent
  infinite V-Ratios from distorting the percentile cut.
- Computed on the full daily universe so the Friday sampler only needs a
  single .reindex call.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_vratio(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    window: int = 20,
) -> pd.DataFrame:
    """
    Rolling `window`-day V-Ratio for every column of *prices* / *volume*.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily adjusted-close prices.  Index = DatetimeIndex, columns = tickers.
    volume : pd.DataFrame
        Daily volume (share count).  Same shape as *prices*.
    window : int
        Look-back in trading days.  Default 20 ≈ 1 calendar month.

    Returns
    -------
    pd.DataFrame
        Same shape as *prices*.  First `window` rows are NaN.
    """
    daily_ret = prices.pct_change()

    avg_volume = volume.rolling(window, min_periods=window).mean()
    std_return = daily_ret.rolling(window, min_periods=window).std()

    vratio = avg_volume.div(std_return)
    # Suppress inf/-inf that arise from near-zero volatility windows
    vratio = vratio.replace([np.inf, -np.inf], np.nan)
    return vratio
