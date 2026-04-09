"""
Janus Rotational System — Price & Volume Data Fetcher
======================================================
Fetches daily Total-Return-proxy prices (auto-adjusted close) and volume
for both ETF universes via yfinance.

`auto_adjust=True` in yfinance applies the CRSP total-return adjustment:
    adjusted_close = close × cumulative_adjustment_factor
where the factor reflects dividends and splits.  This is the correct input
for any momentum or return calculation.

Usage
-----
    from janus_rotational.data.fetcher import fetch_price_volume
    prices, volume = fetch_price_volume(EQUITY_UNIVERSE + BOND_UNIVERSE,
                                        DATA_START, DATA_END)
"""

from __future__ import annotations

import logging
from typing import Sequence

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_price_volume(
    tickers: Sequence[str],
    start: str,
    end: str,
    missing_data_threshold: float = 0.80,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Download daily adjusted-close prices and volume for *tickers*.

    Parameters
    ----------
    tickers : sequence of str
        ETF symbols to fetch.
    start, end : str
        ISO-8601 date strings (inclusive on both ends via yfinance convention).
    missing_data_threshold : float
        Drop a ticker if it has fewer than this fraction of non-NaN rows.
        Default 0.80 keeps ETFs that launched mid-window (e.g. BNDX 2013).

    Returns
    -------
    prices : pd.DataFrame
        Daily adjusted close; index=DatetimeIndex, columns=ticker symbols.
    volume : pd.DataFrame
        Daily volume; same shape as prices.
    """
    tickers = list(tickers)
    logger.info("Fetching %d tickers  [%s → %s]", len(tickers), start, end)

    raw: pd.DataFrame = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=True,     # total-return adjusted close
        actions=False,
        progress=False,
        threads=True,
        # Note: default layout in yfinance >=0.2 is MultiIndex (field, ticker).
        # Do NOT pass group_by="ticker" — that inverts the hierarchy.
    )

    # ── Normalise multi-ticker vs single-ticker output ─────────────────────
    # Multi-ticker: columns = MultiIndex[(field, ticker)] → raw["Close"] gives
    #               a DataFrame with ticker columns.
    # Single-ticker: columns = flat [Open, High, Low, Close, Volume].
    if len(tickers) == 1:
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]})
        volume = raw[["Volume"]].rename(columns={"Volume": tickers[0]})
    else:
        # raw["Close"] yields DataFrame(index=date, columns=tickers)
        prices_raw = raw["Close"]
        volume_raw = raw["Volume"]
        # yfinance 1.2 wraps columns in a "Ticker" name level — flatten
        prices = prices_raw.copy()
        volume = volume_raw.copy()
        prices.columns = prices.columns.get_level_values(-1) if hasattr(prices.columns, "levels") else prices.columns
        volume.columns = volume.columns.get_level_values(-1) if hasattr(volume.columns, "levels") else volume.columns

    prices.index = pd.to_datetime(prices.index)
    volume.index = pd.to_datetime(volume.index)

    # ── Drop tickers below data-coverage threshold ─────────────────────────
    min_rows = int(missing_data_threshold * len(prices))
    before = set(prices.columns)
    prices = prices.dropna(axis=1, thresh=min_rows)
    volume = volume[prices.columns]

    dropped = before - set(prices.columns)
    if dropped:
        logger.warning("Dropped tickers (insufficient history): %s", sorted(dropped))

    # ── Forward-fill stale prices (e.g. holidays in international ETFs) ────
    prices = prices.ffill()
    volume = volume.fillna(0)

    logger.info(
        "Data ready: %d tickers × %d trading days",
        prices.shape[1], prices.shape[0],
    )
    return prices, volume


def fetch_equity_and_bond(
    equity_universe: Sequence[str],
    bond_universe: Sequence[str],
    start: str,
    end: str,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Convenience wrapper: fetches the two strictly-segregated universes
    in a single call and returns them in a labelled dict.

    Returns
    -------
    {
        "equity": (equity_prices, equity_volume),
        "bond":   (bond_prices,   bond_volume),
    }
    """
    all_tickers = list(equity_universe) + list(bond_universe)
    prices, volume = fetch_price_volume(all_tickers, start, end)

    eq_cols   = [t for t in equity_universe if t in prices.columns]
    bond_cols = [t for t in bond_universe   if t in prices.columns]

    return {
        "equity": (prices[eq_cols],   volume[eq_cols]),
        "bond":   (prices[bond_cols], volume[bond_cols]),
    }
