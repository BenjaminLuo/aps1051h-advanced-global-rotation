"""
Janus Rotational System — Trade Cost Model
==========================================
Pure functions for computing execution costs.  No state.

Slippage model:
    Buy  exec price = close × (1 + slippage)    — we pay above mid
    Sell exec price = close × (1 − slippage)    — we receive below mid

This is a symmetric, linear market-impact model.  2 bps one-way is
conservative for the highly liquid ETFs in our universe (typical
bid-ask spread on SPY is ~0.5 bps; we add implementation slack).

Commission model:
    $0.005 per share (fixed dollar, modelled after Interactive Brokers
    base-rate tier).  This is price-agnostic — it penalises low-priced
    ETFs (BIL ≈ $91) proportionally more than high-priced ones.

All functions are vectorisable — they accept either scalars or arrays.
"""

from __future__ import annotations

DEFAULT_SLIPPAGE:   float = 0.0002   # 2 basis points per side
DEFAULT_COMMISSION: float = 0.005    # USD per share


def buy_exec_price(close: float, slippage: float = DEFAULT_SLIPPAGE) -> float:
    """Execution price to purchase: close × (1 + slippage)."""
    return close * (1.0 + slippage)


def sell_exec_price(close: float, slippage: float = DEFAULT_SLIPPAGE) -> float:
    """Execution price on sale: close × (1 − slippage)."""
    return close * (1.0 - slippage)


def shares_buyable(
    cash:       float,
    close:      float,
    slippage:   float = DEFAULT_SLIPPAGE,
    commission: float = DEFAULT_COMMISSION,
) -> int:
    """
    Maximum whole shares purchasable with *cash* at *close*.

    Total all-in cost per share = buy_exec_price + commission_per_share.
    We floor-divide to enforce integer share lots.
    """
    cost_per_share = buy_exec_price(close, slippage) + commission
    if cost_per_share <= 0:
        return 0
    return int(cash // cost_per_share)


def total_buy_cost(
    n_shares:   int,
    close:      float,
    slippage:   float = DEFAULT_SLIPPAGE,
    commission: float = DEFAULT_COMMISSION,
) -> float:
    """Cash outflow to purchase *n_shares*: exec_price × shares + commission × shares."""
    return n_shares * buy_exec_price(close, slippage) + n_shares * commission


def total_sell_proceeds(
    n_shares:   int,
    close:      float,
    slippage:   float = DEFAULT_SLIPPAGE,
    commission: float = DEFAULT_COMMISSION,
) -> float:
    """Cash inflow from selling *n_shares*: exec_price × shares − commission × shares."""
    return n_shares * sell_exec_price(close, slippage) - n_shares * commission
