"""
Janus Rotational System — TrancheLedger
========================================
Tracks the state of a single 25%-of-capital slice: its cash balance and
integer share positions.  All trade execution is delegated to this class so
the ladder engine stays free of cost-model details.

A TrancheLedger only knows about its OWN capital.  It never communicates
with other tranches and has no concept of total portfolio value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from janus_rotational.execution.costs import (
    DEFAULT_COMMISSION,
    DEFAULT_SLIPPAGE,
    buy_exec_price,
    sell_exec_price,
    shares_buyable,
    total_buy_cost,
    total_sell_proceeds,
)


@dataclass
class TrancheLedger:
    """
    State container for one tranche.

    Attributes
    ----------
    label : str
        Human-readable label (e.g. 'A', 'B', 'C', 'D').
    cash  : float
        Uninvested cash, in USD.
    holdings : dict[str, int]
        Mapping of ticker → integer share count.
    """

    label:    str
    cash:     float
    holdings: dict[str, int] = field(default_factory=dict)

    # ── Valuation ─────────────────────────────────────────────────────────

    def holding_value(self, prices: dict[str, float]) -> float:
        """Mark-to-market value of all open positions."""
        return sum(
            n * prices.get(ticker, np.nan)
            for ticker, n in self.holdings.items()
        )

    def total_value(self, prices: dict[str, float]) -> float:
        """Total tranche capital = cash + mark-to-market holdings."""
        return self.cash + self.holding_value(prices)

    # ── Execution ─────────────────────────────────────────────────────────

    def liquidate(
        self,
        prices:     dict[str, float],
        slippage:   float = DEFAULT_SLIPPAGE,
        commission: float = DEFAULT_COMMISSION,
    ) -> list[dict]:
        """
        Sell ALL open positions at Friday close.

        Proceeds (net of slippage + commission) are added to `self.cash`.
        After this call `self.holdings` is empty.

        Returns
        -------
        list of trade-record dicts (one per ticker sold).
        """
        trade_records: list[dict] = []

        for ticker, n_shares in list(self.holdings.items()):
            if n_shares <= 0:
                continue

            close    = prices[ticker]
            proceeds = total_sell_proceeds(n_shares, close, slippage, commission)

            slip_cost = n_shares * close * slippage
            comm_cost = n_shares * commission

            self.cash += proceeds

            trade_records.append({
                "action":           "SELL",
                "tranche":          self.label,
                "ticker":           ticker,
                "shares":           n_shares,
                "close":            round(close, 4),
                "exec_price":       round(sell_exec_price(close, slippage), 4),
                "slippage_cost":    round(slip_cost, 4),
                "commission_cost":  round(comm_cost, 4),
                "net_proceeds":     round(proceeds, 4),
            })

        self.holdings.clear()
        return trade_records

    def invest_equal_weight(
        self,
        tickers:    list[str],
        prices:     dict[str, float],
        slippage:   float = DEFAULT_SLIPPAGE,
        commission: float = DEFAULT_COMMISSION,
    ) -> list[dict]:
        """
        Buy *tickers* at strict equal weight using ALL available cash.

        Each ticker receives 1/len(tickers) of current cash.
        Fractional share residual stays as cash (no re-allocation of
        remainders to avoid second-order rounding loops).

        Returns
        -------
        list of trade-record dicts (one per ticker bought).
        """
        n_legs = len(tickers)
        if n_legs == 0:
            return []

        per_etf_cash = self.cash / n_legs
        trade_records: list[dict] = []

        for ticker in tickers:
            close   = prices[ticker]
            n       = shares_buyable(per_etf_cash, close, slippage, commission)

            if n <= 0:
                continue

            cost       = total_buy_cost(n, close, slippage, commission)
            slip_cost  = n * close * slippage
            comm_cost  = n * commission

            self.cash -= cost
            self.holdings[ticker] = self.holdings.get(ticker, 0) + n

            trade_records.append({
                "action":           "BUY",
                "tranche":          self.label,
                "ticker":           ticker,
                "shares":           n,
                "close":            round(close, 4),
                "exec_price":       round(buy_exec_price(close, slippage), 4),
                "slippage_cost":    round(slip_cost, 4),
                "commission_cost":  round(comm_cost, 4),
                "net_cost":         round(cost, 4),
            })

        return trade_records

    # ── Display ───────────────────────────────────────────────────────────

    def holdings_str(self) -> str:
        """Compact display: 'QQQ·247 / XLK·318 / SPY·52'."""
        if not self.holdings:
            return "CASH"
        return " / ".join(
            f"{t}·{n}" for t, n in sorted(self.holdings.items())
        )
