"""
Janus Rotational System — Rotational Momentum Signal
=====================================================
Computes the N-day (default 126 trading days ≈ 6 calendar months) cumulative
total return for every ETF in the combined universe on a rolling daily basis.

Definition
----------
    momentum(t, n) = price(t) / price(t - n) − 1

where `price` is the *total-return-adjusted* close fetched by the data layer.
Using adjusted close means dividend distributions are embedded in the return —
a critical requirement for fixed-income ETFs (LQD, HYG, BIL) where coupon
income is the primary source of return.

Design notes
------------
- Returns NaN for the first `window` rows; the caller must handle this
  by checking coverage before using the signal.
- No winsorisation applied here.  Outlier handling (if any) belongs in
  the caller so behaviour is explicit at the selection layer.
- Computing on the full daily index and *sampling* on Fridays (rather than
  computing only on Fridays) prevents look-ahead from the sampling choice
  and gives a cleaner reindex path.
"""

from __future__ import annotations

import pandas as pd


def compute_momentum(
    prices: pd.DataFrame,
    window: int = 126,
) -> pd.DataFrame:
    """
    Rolling `window`-day cumulative return for every column of *prices*.

    Parameters
    ----------
    prices : pd.DataFrame
        Daily adjusted-close prices.  Index = DatetimeIndex, columns = tickers.
    window : int
        Look-back in trading days.  Default 126 ≈ 6 calendar months.

    Returns
    -------
    pd.DataFrame
        Same shape as *prices*.  Values are decimal returns (e.g. 0.12 = +12%).
        First `window` rows are NaN.
    """
    return prices.pct_change(periods=window)


def compute_dual_momentum(
    prices:       pd.DataFrame,
    window_short: int = 63,
    window_long:  int = 126,
) -> pd.DataFrame:
    """
    Dual Momentum score = simple average of the short-term and long-term
    cumulative returns (Janus 2.0 upgrade).

    Using two look-back windows simultaneously:
      • 63-day  (≈ 3 months) captures recent trend acceleration / reversal.
      • 126-day (≈ 6 months) provides medium-term trend confirmation.

    Averaging them gives a composite that is more responsive than the pure
    126-day signal (less lag on new trends) while remaining more stable than
    a pure 63-day signal (less whipsaw noise).

    Parameters
    ----------
    prices       : pd.DataFrame  Daily adjusted-close prices.
    window_short : int            Short look-back.  Default 63 (≈ 3 months).
    window_long  : int            Long look-back.   Default 126 (≈ 6 months).

    Returns
    -------
    pd.DataFrame  Same shape as *prices*.  NaN until the long window is filled.
    """
    mom_short = prices.pct_change(periods=window_short)
    mom_long  = prices.pct_change(periods=window_long)
    return (mom_short + mom_long) / 2.0
