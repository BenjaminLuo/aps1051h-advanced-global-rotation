"""
Janus Rotational System — Phase 3: Laddered Execution Engine
=============================================================
Implements the 4-tranche overlapping ladder that keeps the portfolio
~100% invested at all times while staggering rebalance events.

The "75% cash drag" anti-pattern and its fix
--------------------------------------------
The naive mistake is to deploy only ONE tranche per week at launch:

    Week 1 → only Tranche A buys in  →  25% invested, 75% cash
    Week 2 → Tranche B buys in       →  50% invested, 50% cash
    Week 3 → Tranche C buys in       →  75% invested, 25% cash
    Week 4 → Tranche D buys in       → 100% invested,  0% cash

For a system designed to capture momentum, sitting in 75% cash for three
weeks is catastrophic and negates the whole point of the strategy.

The fix: Initialization Sweep
------------------------------
On the VERY FIRST Friday of the out-of-sample period, ALL four tranches
simultaneously buy the current week's top-3 ETFs.  From that moment,
100% of capital is deployed.  The rotating weekly rebalance then begins
from the *second* Friday, rotating A → B → C → D → A → …

This means:
  - All four tranches hold the same 3 ETFs after the initialization sweep.
  - Each week, ONE tranche sells its current ETFs and buys the NEW top-3.
  - The other three tranches remain in their previous selections.
  - As weeks pass, each tranche gradually diverges to its own signal.

The result is a 4-week "rolling average" of the signal — excellent for
smoothing momentum whipsaws — with essentially zero cash drag.

Ladder rotation schedule
------------------------
    Init Friday      → ALL tranches buy (no sell, cash → positions)
    Init + 1 week    → Tranche A rotates
    Init + 2 weeks   → Tranche B rotates
    Init + 3 weeks   → Tranche C rotates
    Init + 4 weeks   → Tranche D rotates
    Init + 5 weeks   → Tranche A rotates (4-week cycle repeats)
    ...

Execution model
---------------
All trades execute as market orders at the Friday adjusted close:
  - Buy  price = close × (1 + 0.0002) + $0.005/share  (slippage + commission)
  - Sell price = close × (1 − 0.0002) − $0.005/share

Integer share lots only.  Fractional-share residual stays as cash in
each tranche (typically < 0.3% of tranche capital).

Outputs
-------
LadderResult namedtuple containing:
  daily   — pd.DataFrame  one row per trading day (M2M snapshot)
  weekly  — pd.DataFrame  one row per rebalance Friday (holdings detail)
  trades  — pd.DataFrame  one row per individual trade (full audit log)
"""

from __future__ import annotations

import logging
from collections import namedtuple

import numpy as np
import pandas as pd

from janus_rotational.execution.costs import DEFAULT_COMMISSION, DEFAULT_SLIPPAGE
from janus_rotational.execution.tranche import TrancheLedger

logger = logging.getLogger(__name__)

LadderResult = namedtuple("LadderResult", ["daily", "weekly", "trades"])


class LadderEngine:
    """
    Stateless engine: call `run()` to execute the back-test ladder.

    Parameters
    ----------
    initial_capital : float
        Total starting portfolio value in USD.
    n_tranches : int
        Number of independent overlapping tranches.  Default 4.
    slippage : float
        One-way market-impact rate applied to every trade.  Default 2 bps.
    commission : float
        Commission per share in USD.  Default $0.005.
    """

    def __init__(
        self,
        initial_capital:  float         = 1_000_000.0,
        n_tranches:        int           = 4,
        slippage:          float         = DEFAULT_SLIPPAGE,
        commission:        float         = DEFAULT_COMMISSION,
        execution_lag:     int           = 0,
        asset_classes:     dict[str, list[str]] | None = None,
    ) -> None:
        self.initial_capital = initial_capital
        self.n_tranches      = n_tranches
        self.slippage        = slippage
        self.commission      = commission
        self.execution_lag   = execution_lag
        self.labels          = [f"T{i+1}" for i in range(n_tranches)]
        # Track arbitrary asset categories (e.g., US Equities, Bonds, etc.)
        self._asset_classes = {
            name: set(tickers) for name, tickers in (asset_classes or {}).items()
        }

    # ── Public API ────────────────────────────────────────────────────────

    def run(
        self,
        prices:     pd.DataFrame,
        selections: pd.DataFrame,
        start:      str,
        end:        str,
    ) -> LadderResult:
        """
        Execute the full ladder over the out-of-sample window [start, end].

        Parameters
        ----------
        prices : pd.DataFrame
            Daily total-return-adjusted close for all tickers.
            Index = DatetimeIndex (business days), columns = tickers.
        selections : pd.DataFrame
            Output of `signals.selector.build_weekly_selections()`.
            Must contain columns rank_1, rank_2, rank_3.
        start, end : str
            ISO-8601 dates for the OOS window.

        Returns
        -------
        LadderResult(daily, weekly, trades)
        """
        # ── Validate and slice ─────────────────────────────────────────
        oos_prices = prices.loc[start:end]
        oos_sel    = selections.loc[start:end].dropna(subset=["rank_1"])

        if oos_sel.empty:
            raise ValueError(f"No valid selections in [{start}, {end}].")
        if oos_prices.empty:
            raise ValueError(f"No price data in [{start}, {end}].")

        # ── Create tranches ────────────────────────────────────────────
        tranche_cash = self.initial_capital / self.n_tranches
        tranches: dict[str, TrancheLedger] = {
            lbl: TrancheLedger(label=lbl, cash=tranche_cash)
            for lbl in self.labels
        }

        all_trades:   list[dict] = []
        weekly_rows:  list[dict] = []
        daily_rows:   list[dict] = []

        # ── Pre-build the rebalance schedule ───────────────────────────
        #    Signal is generated on signal_friday.
        #    Trade occurs on execution_date (signal_friday + lag).
        sel_dates    = oos_sel.index.tolist()
        bday_index   = oos_prices.index.tolist()

        # Map execution_date → {tranche_label, signal_date}
        exec_map: dict[pd.Timestamp, dict] = {}
        
        for i, signal_dt in enumerate(sel_dates):
            # Find the execution date (current or next N business days)
            try:
                sig_idx  = bday_index.index(signal_dt)
                exec_idx = sig_idx + self.execution_lag
                if exec_idx >= len(bday_index):
                    continue
                exec_dt = bday_index[exec_idx]
                
                # First Friday (init) vs subsequent rotations
                if i == 0:
                    exec_map[exec_dt] = {"type": "INIT", "sig_date": signal_dt}
                else:
                    lbl = self.labels[(i-1) % self.n_tranches] # (i-1) because i=0 was init
                    exec_map[exec_dt] = {"type": "REBAL", "sig_date": signal_dt, "tranche": lbl}
            except ValueError:
                continue

        logger.info(
            "Ladder configured: capital=$%s  tranches=%d  lag=%d  OOS Fridays=%d",
            f"{self.initial_capital:,.0f}", self.n_tranches, self.execution_lag, len(sel_dates),
        )

        # ── Main loop: iterate every trading day ──────────────────────
        for date in oos_prices.index:

            close_row = oos_prices.loc[date].to_dict()

            # ── Rebalance logic ────────────────────────────────────────
            if date in exec_map:
                event = exec_map[date]
                sig_dt = event["sig_date"]
                tickers = self._tickers(oos_sel.loc[sig_dt])
                
                if event["type"] == "INIT":
                    # INITIALIZATION SWEEP — all tranches buy
                    for lbl in self.labels:
                        buys = tranches[lbl].invest_equal_weight(
                            tickers, close_row, self.slippage, self.commission
                        )
                        for t in buys:
                            all_trades.append({"date": date, "event": "INIT", **t})
                    weekly_rows.append(
                        self._weekly_row(tranches, close_row, date, "INIT", tickers)
                    )
                else:
                    # REGULAR REBALANCE — active tranche rotates
                    active_lbl = event["tranche"]
                    active = tranches[active_lbl]
                    
                    sells = active.liquidate(close_row, self.slippage, self.commission)
                    for t in sells:
                        all_trades.append({"date": date, "event": "REBAL", **t})
                        
                    buys = active.invest_equal_weight(
                        tickers, close_row, self.slippage, self.commission
                    )
                    for t in buys:
                        all_trades.append({"date": date, "event": "REBAL", **t})
                        
                    weekly_rows.append(
                        self._weekly_row(tranches, close_row, date, active_lbl, tickers)
                    )

            # ── Daily M2M snapshot (taken AFTER any trades) ────────────
            daily_rows.append(self._daily_row(tranches, close_row, date))

        # ── Assemble output DataFrames ─────────────────────────────────
        daily_df  = pd.DataFrame(daily_rows).set_index("date")
        weekly_df = pd.DataFrame(weekly_rows).set_index("friday_date")
        trades_df = pd.DataFrame(all_trades)
        if not trades_df.empty:
            trades_df = trades_df.set_index("date")

        logger.info(
            "Ladder complete: %d trading days | %d rebalance events | "
            "%d individual trades",
            len(daily_df), len(weekly_df), len(trades_df),
        )
        return LadderResult(daily=daily_df, weekly=weekly_df, trades=trades_df)

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _tickers(sel_row: pd.Series) -> list[str]:
        """Extract all non-null rank_i tickers from a selection row."""
        tickers = []
        i = 1
        while True:
            col = f"rank_{i}"
            if col not in sel_row.index:
                break
            tkr = sel_row[col]
            if pd.notna(tkr):
                tickers.append(tkr)
            i += 1
        return tickers

    def _daily_row(
        self,
        tranches:  dict[str, TrancheLedger],
        close_row: dict[str, float],
        date:      pd.Timestamp,
    ) -> dict:
        """Snapshot of all tranche values at end-of-day close prices."""
        total_cash = sum(t.cash for t in tranches.values())
        total_hold = sum(t.holding_value(close_row) for t in tranches.values())
        total_val  = total_cash + total_hold

        row: dict = {
            "date":           date,
            "portfolio_value": round(total_val,  2),
            "invested_value":  round(total_hold, 2),
            "cash":            round(total_cash, 2),
            "pct_invested":    round(total_hold / total_val, 6) if total_val > 0 else 0.0,
        }
        for lbl, t in tranches.items():
            tv = t.cash + t.holding_value(close_row)
            row[f"T{lbl}_value"] = round(tv, 2)
            row[f"T{lbl}_cash"]  = round(t.cash, 2)

        # Optional: granular asset class allocation tracking
        for name, tkr_set in self._asset_classes.items():
            cat_val = sum(
                n * close_row.get(tkr, 0.0)
                for t in tranches.values()
                for tkr, n in t.holdings.items()
                if tkr in tkr_set
            )
            row[f"{name}_value"] = round(cat_val, 2)

        return row

    def _weekly_row(
        self,
        tranches:   dict[str, TrancheLedger],
        close_row:  dict[str, float],
        date:       pd.Timestamp,
        active_lbl: str,
        new_signal: list[str],
    ) -> dict:
        """Rich summary for each rebalance Friday (used for audit/validation)."""
        total_cash = sum(t.cash for t in tranches.values())
        total_hold = sum(t.holding_value(close_row) for t in tranches.values())
        total_val  = total_cash + total_hold

        row: dict = {
            "friday_date":      date,
            "active_tranche":   active_lbl,
            "new_signal":       " / ".join(new_signal),
            "portfolio_value":  round(total_val, 2),
            "invested_value":   round(total_hold, 2),
            "cash":             round(total_cash, 2),
            "pct_invested":     round(total_hold / total_val, 4) if total_val > 0 else 0.0,
        }
        for lbl, t in tranches.items():
            row[f"T{lbl}_holdings"] = t.holdings_str()
            row[f"T{lbl}_value"]    = round(t.total_value(close_row), 2)

        return row
