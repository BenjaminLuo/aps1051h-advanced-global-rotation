"""
Janus Rotational System — Step 1 Validation Runner
====================================================
Executes and validates:
  (A) Data Acquisition  — ETF price & volume download via yfinance
  (B) Phase 1           — Weekly macro regime flag with 45-day lag

Run:
    python run_step1.py

Output is written to stdout in formatted tables designed for manual
inspection of look-ahead-bias prevention.
"""

from __future__ import annotations

import logging
import sys
import warnings

import pandas as pd

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_step1")
warnings.filterwarnings("ignore")   # suppress yfinance deprecation noise

# ── Project imports ────────────────────────────────────────────────────────────
from janus_rotational.config import (
    BOND_UNIVERSE,
    DATA_END,
    DATA_START,
    EQUITY_UNIVERSE,
    SPY_TOP10,
)
from janus_rotational.data.fetcher import fetch_equity_and_bond
from janus_rotational.data.fundamentals import (
    build_daily_fundamental_series,
    get_per_ticker_scores,
)
from janus_rotational.regime.macro import build_weekly_regime, regime_summary

DIVIDER = "=" * 78


def section(title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


# ══════════════════════════════════════════════════════════════════════════════
# A — DATA ACQUISITION
# ══════════════════════════════════════════════════════════════════════════════
def run_data_acquisition() -> dict:
    section("A — DATA ACQUISITION  (yfinance · auto_adjust=True · total return)")

    universes = fetch_equity_and_bond(
        equity_universe=EQUITY_UNIVERSE,
        bond_universe=BOND_UNIVERSE,
        start=DATA_START,
        end=DATA_END,
    )

    eq_prices, eq_vol   = universes["equity"]
    bond_prices, bond_vol = universes["bond"]

    print(f"\n{'─'*38} EQUITY UNIVERSE {'─'*22}")
    print(f"  Tickers loaded : {sorted(eq_prices.columns.tolist())}")
    print(f"  Shape          : {eq_prices.shape[0]} trading days × {eq_prices.shape[1]} ETFs")
    print(f"  Date range     : {eq_prices.index[0].date()} → {eq_prices.index[-1].date()}")
    print(f"\n  Adjusted Close — first 5 rows (SPY, QQQ, DIA):")
    print(
        eq_prices[["SPY", "QQQ", "DIA"]].head()
        .to_string(float_format="{:.2f}".format)
    )

    print(f"\n{'─'*38} BOND UNIVERSE {'─'*24}")
    print(f"  Tickers loaded : {sorted(bond_prices.columns.tolist())}")
    print(f"  Shape          : {bond_prices.shape[0]} trading days × {bond_prices.shape[1]} ETFs")
    print(f"  Date range     : {bond_prices.index[0].date()} → {bond_prices.index[-1].date()}")
    print(f"\n  Adjusted Close — first 5 rows (BIL, IEF, TLT, GLD):")
    print(
        bond_prices[["BIL", "IEF", "TLT", "GLD"]].head()
        .to_string(float_format="{:.2f}".format)
    )

    return universes


# ══════════════════════════════════════════════════════════════════════════════
# B — PHASE 1: MACRO REGIME SWITCH
# ══════════════════════════════════════════════════════════════════════════════
def run_phase1() -> pd.DataFrame:
    section("B — PHASE 1  ·  Global Macro Regime Switch")

    # ── B.1  Per-ticker quarterly scores (raw, pre-lag) ───────────────────
    print(f"\n{'─'*38} B.1  RAW QUARTERLY SCORES (pre-lag, per ticker) {'─'*4}")
    print(f"  SPY Top-10 holdings: {SPY_TOP10}")
    per_ticker = get_per_ticker_scores()
    # Show Q1 2020 and Q2 2020 — the COVID stress quarters
    covid_qs = per_ticker.loc[
        per_ticker.index.get_level_values("quarter_end").isin([
            pd.Timestamp("2019-12-31"),
            pd.Timestamp("2020-03-31"),
            pd.Timestamp("2020-06-30"),
            pd.Timestamp("2020-09-30"),
        ])
    ]
    print("\n  Quarterly scores around COVID shock (raw, no lag applied):")
    print(covid_qs.to_string())

    # ── B.2  Daily lagged fundamental series (aggregate) ──────────────────
    print(f"\n{'─'*38} B.2  DAILY LAGGED FUNDAMENTAL SERIES (aggregate) {'─'*3}")
    daily_fund = build_daily_fundamental_series(start=DATA_START, end=DATA_END)

    # Show the transition windows around Q1 and Q2 2020
    print("\n  45-day lag in action — transition from Q4-2019 → Q1-2020 data:")
    print("  (Q1-2020 ends 2020-03-31; available from 2020-05-15)")
    window_1 = daily_fund["2020-05-10":"2020-05-20"]
    print(
        window_1[["quarter_end", "altman_z_raw", "piotroski_f_raw"]]
        .to_string(float_format="{:.3f}".format)
    )

    print("\n  Transition from Q1-2020 → Q2-2020 data:")
    print("  (Q2-2020 ends 2020-06-30; available from 2020-08-14)")
    window_2 = daily_fund["2020-08-10":"2020-08-20"]
    print(
        window_2[["quarter_end", "altman_z_raw", "piotroski_f_raw"]]
        .to_string(float_format="{:.3f}".format)
    )

    # ── B.3  Weekly regime flag ────────────────────────────────────────────
    print(f"\n{'─'*38} B.3  WEEKLY FRIDAY REGIME FLAG {'─'*16}")
    weekly = build_weekly_regime(start=DATA_START, end=DATA_END)

    print("\n  Full weekly regime — CRASH REGIME = True rows only:")
    crash_weeks = weekly[weekly["crash_regime"]]
    print(
        crash_weeks.to_string(
            float_format="{:.3f}".format,
        )
    )

    # ── B.4  Lag-validation snippets ──────────────────────────────────────
    print(f"\n{'─'*38} B.4  LAG VALIDATION SNIPPETS {'─'*18}")

    # Snippet 1: Around Q1-2020 release (expect switch from Q4-2019 → Q1-2020
    #            data on the first Friday on or after 2020-05-15)
    print("\n  [Snippet 1]  Fridays straddling Q1-2020 release date (2020-05-15)")
    print("  Expect: quarter_end flips from 2019-12-31 → 2020-03-31 on or after 2020-05-15")
    snap1 = weekly["2020-04-24":"2020-06-05"]
    print(snap1.to_string(float_format="{:.3f}".format))

    # Snippet 2: Confirm look-ahead prevention — on 2020-04-24 (a Friday
    #            BEFORE Q1-2020 is released), system must still use Q4-2019 data.
    print("\n  [Snippet 2]  Friday 2020-04-24 — Q1-2020 data NOT yet available")
    print("  Expect: quarter_end = 2019-12-31 (45-day lag not yet elapsed)")
    april24 = weekly.loc["2020-04-24":"2020-04-24"]
    print(april24.to_string(float_format="{:.3f}".format))

    # Snippet 3: Friday 2020-05-15 — exact release date
    print("\n  [Snippet 3]  Friday 2020-05-15 — Q1-2020 data becomes available")
    print("  Expect: quarter_end = 2020-03-31; crash_regime = True")
    may15 = weekly.loc["2020-05-15":"2020-05-15"]
    print(may15.to_string(float_format="{:.3f}".format))

    # Snippet 4: Normal period for contrast
    print("\n  [Snippet 4]  Normal period sample (2021, full year, every 4 weeks)")
    normal_2021 = weekly["2021-01-01":"2021-12-31"].iloc[::4]
    print(normal_2021.to_string(float_format="{:.3f}".format))

    # ── B.5  Annual summary ────────────────────────────────────────────────
    print(f"\n{'─'*38} B.5  ANNUAL REGIME SUMMARY {'─'*20}")
    print(regime_summary(weekly).to_string())

    # ── B.6  Key statistics ───────────────────────────────────────────────
    print(f"\n{'─'*38} B.6  KEY STATISTICS {'─'*28}")
    total_fridays = len(weekly)
    crash_count   = weekly["crash_regime"].sum()
    altman_only   = (weekly["altman_trigger"] & ~weekly["piotroski_trigger"]).sum()
    piotr_only    = (~weekly["altman_trigger"] & weekly["piotroski_trigger"]).sum()
    both          = (weekly["altman_trigger"] & weekly["piotroski_trigger"]).sum()

    print(f"  Total Friday observations : {total_fridays}")
    print(f"  Crash regime weeks        : {crash_count}  ({100*crash_count/total_fridays:.1f}%)")
    print(f"    ↳ Altman trigger only   : {altman_only}")
    print(f"    ↳ Piotroski trigger only: {piotr_only}")
    print(f"    ↳ Both triggers         : {both}")
    print(f"  Min Altman Z (aggregate)  : {weekly['altman_z'].min():.3f}")
    print(f"  Min Piotroski F (agg.)    : {weekly['piotroski_f'].min():.3f}")
    print(f"  Max days_since_qend       : {weekly['days_since_qend'].max()}")
    print(f"  Min days_since_qend       : {weekly['days_since_qend'].min()}")
    valid_lag = weekly["days_since_qend"].dropna()
    lag_ok = (valid_lag >= 45).all() and len(valid_lag) == len(weekly)
    print(f"  [PASS] days_since_qend >= 45 always: "
          f"{'YES' if lag_ok else 'FAIL — LOOK-AHEAD DETECTED'} "
          f"(checked {len(valid_lag)}/{len(weekly)} non-null rows)")

    return weekly


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{'#'*78}")
    print("  JANUS ROTATIONAL SYSTEM — STEP 1: DATA ACQUISITION & PHASE 1 VALIDATION")
    print(f"{'#'*78}")

    universes = run_data_acquisition()
    weekly    = run_phase1()

    section("STEP 1 COMPLETE")
    print(
        "\n  All modules executed without error.\n"
        "  Review the lag-validation snippets above to confirm:\n"
        "    1. quarter_end transitions occur >= 45 days after the quarter closes.\n"
        "    2. days_since_qend is always >= 45  (no look-ahead bias).\n"
        "    3. crash_regime = True during COVID (2020 Q1/Q2) and other stress periods.\n"
        "  When satisfied, proceed to Step 2 (Phase 2: Momentum Ranking).\n"
    )
    sys.exit(0)
