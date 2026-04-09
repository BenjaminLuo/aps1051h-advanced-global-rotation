"""
Janus Rotational System — Performance Metrics
==============================================
All metrics are computed from a daily equity-curve Series.
No look-ahead; every function is a pure transform of historical data.

Conventions
-----------
CAGR          : geometric annualisation  (final/initial)^(252/n_days) − 1
Sharpe        : (μ_excess × 252) / (σ_daily × √252)  where μ_excess = μ − rf/252
Sortino       : (μ_excess × 252) / σ_downside  — downside deviation counts only
                  days where return < rf/252  (semi-variance denominator)
Max Drawdown  : min over all dates of (price − running_max) / running_max
Ann. Vol      : σ_daily × √252
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(
    equity_curve: pd.Series,
    rf: float = 0.02,
) -> dict[str, float]:
    """
    Full performance metric suite for a daily equity curve.

    Parameters
    ----------
    equity_curve : pd.Series
        Daily portfolio value (NOT returns).  Index = DatetimeIndex.
    rf : float
        Annual risk-free rate.  Default 0.02 (2%).

    Returns
    -------
    dict with keys: total_return, cagr, ann_vol, sharpe, sortino,
                    max_drawdown, calmar (cagr / abs(max_drawdown))
    """
    curve  = equity_curve.dropna()
    rets   = curve.pct_change().dropna()
    n_days = len(rets)

    if n_days < 2:
        return {k: np.nan for k in
                ["total_return","cagr","ann_vol","sharpe","sortino","max_drawdown","calmar"]}

    years        = n_days / 252.0
    total_return = curve.iloc[-1] / curve.iloc[0] - 1.0
    cagr         = (1.0 + total_return) ** (1.0 / years) - 1.0
    ann_vol      = rets.std() * np.sqrt(252)

    daily_rf     = rf / 252.0
    excess       = rets - daily_rf
    sharpe       = (excess.mean() * 252.0) / (rets.std() * np.sqrt(252.0))

    # Sortino: downside deviation uses only returns below the daily target
    below_target = np.minimum(excess.values, 0.0)
    downside_vol = np.sqrt(np.mean(below_target ** 2)) * np.sqrt(252.0)
    sortino      = (excess.mean() * 252.0) / downside_vol if downside_vol > 0 else np.nan

    # Max drawdown
    roll_max  = curve.cummax()
    dd_series = (curve - roll_max) / roll_max
    max_dd    = dd_series.min()

    calmar = cagr / abs(max_dd) if max_dd != 0 else np.nan

    return {
        "total_return": round(total_return, 6),
        "cagr":         round(cagr,         6),
        "ann_vol":      round(ann_vol,       6),
        "sharpe":       round(sharpe,        4),
        "sortino":      round(sortino,       4),
        "max_drawdown": round(max_dd,        6),
        "calmar":       round(calmar,        4),
    }


def drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """
    Running drawdown from peak, as a decimal (e.g. −0.35 = −35% drawdown).
    """
    curve    = equity_curve.dropna()
    roll_max = curve.cummax()
    return (curve - roll_max) / roll_max
