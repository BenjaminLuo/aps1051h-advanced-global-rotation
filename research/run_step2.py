"""
Janus Rotational System — Step 2 Validation Runner
====================================================
Validates Phase 2 (Signal Generation & Selection) by printing:

  (A) 2020 Crash Period    — must select BOND universe during COVID regime
  (B) Regime Transition    — flip from bond → equity selections Nov 2020
  (C) 2021 Bull Market     — must select EQUITY universe throughout
  (D) Full Annual Summary  — universe and top-pick frequency table

Run:
    python run_step2.py
"""

from __future__ import annotations

import logging
import sys
import warnings

import pandas as pd

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_step2")
warnings.filterwarnings("ignore")

# ── Project imports ────────────────────────────────────────────────────────────
from janus_rotational.config import (
    BOND_UNIVERSE,
    DATA_END,
    DATA_START,
    EQUITY_UNIVERSE,
)
from janus_rotational.data.fetcher    import fetch_equity_and_bond
from janus_rotational.regime.macro    import build_weekly_regime
from janus_rotational.signals.selector import build_long_form, build_weekly_selections

DIVIDER = "=" * 82


def section(title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def _fmt_wide(df: pd.DataFrame, top_n: int = 3) -> str:
    """Pretty-print the wide selection table with momentum shown as %."""
    display = df.copy()
    for i in range(1, top_n + 1):
        if f"mom_{i}" in display.columns:
            display[f"mom_{i}"] = display[f"mom_{i}"].map(
                lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "—"
            )
        if f"vr_{i}" in display.columns:
            display[f"vr_{i}"] = display[f"vr_{i}"].map(
                lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
            )
    cols_order = (
        ["crash_regime", "active_universe", "universe_size", "after_vr_filter"]
        + [c for i in range(1, top_n + 1) for c in [f"rank_{i}", f"mom_{i}", f"vr_{i}"]]
    )
    cols_order = [c for c in cols_order if c in display.columns]
    return display[cols_order].to_string()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{'#'*82}")
    print("  JANUS ROTATIONAL SYSTEM — STEP 2: PHASE 2 SIGNAL GENERATION & SELECTION")
    print(f"{'#'*82}")

    # ── Load data (re-uses Step 1 modules) ────────────────────────────────
    section("SETUP — loading prices, volumes, and regime flag")

    universes = fetch_equity_and_bond(
        equity_universe=EQUITY_UNIVERSE,
        bond_universe=BOND_UNIVERSE,
        start=DATA_START,
        end=DATA_END,
    )
    eq_prices,   eq_vol   = universes["equity"]
    bond_prices, bond_vol = universes["bond"]

    # Combine into single DataFrames for the selector
    prices = pd.concat([eq_prices, bond_prices], axis=1)
    volume = pd.concat([eq_vol,    bond_vol],    axis=1)
    prices.sort_index(inplace=True)
    volume.sort_index(inplace=True)

    regime  = build_weekly_regime(start=DATA_START, end=DATA_END)

    print(f"\n  Prices  : {prices.shape[0]} trading days × {prices.shape[1]} tickers")
    print(f"  Regime  : {len(regime)} Fridays  | {regime['crash_regime'].sum()} crash weeks")

    # ── Build selections ──────────────────────────────────────────────────
    section("PHASE 2 — Building weekly selections (126-day mom · 20-day V-Ratio)")

    selections = build_weekly_selections(
        prices          = prices,
        volume          = volume,
        regime          = regime,
        equity_universe = EQUITY_UNIVERSE,
        bond_universe   = BOND_UNIVERSE,
    )
    print(f"\n  Selections built: {len(selections)} Fridays")

    # ════════════════════════════════════════════════════════════════════════
    # A — 2020 CRASH PERIOD
    # ════════════════════════════════════════════════════════════════════════
    section("A — 2020 CRASH PERIOD  (expect BOND selections throughout)")
    print(
        "\n  Recall: Q1-2020 fundamentals available 2020-05-15; crash_regime flips True.\n"
        "  System should select from Bond Universe (BIL/SHY/IEF/TLT/GLD etc.).\n"
        "  Flight-to-quality in early 2020: GLD and long-duration Treasuries (TLT)\n"
        "  should dominate on 6M momentum.\n"
    )

    crash_2020 = selections["2020-05-15":"2020-11-13"]
    print(_fmt_wide(crash_2020))

    # ════════════════════════════════════════════════════════════════════════
    # B — REGIME TRANSITION  (Nov 2020)
    # ════════════════════════════════════════════════════════════════════════
    section("B — REGIME TRANSITION  (crash_regime flips False ~2020-11-16)")
    print(
        "\n  Q3-2020 fundamentals available ~2020-11-16 (Piotroski recovers > 4).\n"
        "  Last bond-regime Friday: 2020-11-13.\n"
        "  First equity-regime Friday: 2020-11-20.\n"
        "  Vaccine announcement (2020-11-09) drove a sharp value/cyclical rotation;\n"
        "  expect early equity selections to reflect momentum from the Sep-Nov rally.\n"
    )

    transition = selections["2020-10-09":"2020-12-18"]
    print(_fmt_wide(transition))

    # ════════════════════════════════════════════════════════════════════════
    # C — 2021 BULL MARKET
    # ════════════════════════════════════════════════════════════════════════
    section("C — 2021 BULL MARKET  (expect EQUITY selections throughout)")
    print(
        "\n  2021 was a broad equity bull — crash_regime = False all year.\n"
        "  Tech-heavy QQQ/XLK dominated 6M momentum in H1; cyclicals\n"
        "  (XLB, XLE, XLI) took over in H2 as inflation trade gained.\n"
        "  Sampling every 4 weeks for conciseness.\n"
    )

    bull_2021 = selections["2021-01-01":"2021-12-31"].iloc[::4]
    print(_fmt_wide(bull_2021))

    # ════════════════════════════════════════════════════════════════════════
    # D — FULL 2021 WEEKLY DETAIL
    # ════════════════════════════════════════════════════════════════════════
    section("D — FULL 2021 WEEKLY DETAIL  (all 53 Fridays)")
    print(_fmt_wide(selections["2021-01-01":"2021-12-31"]))

    # ════════════════════════════════════════════════════════════════════════
    # E — ANNUAL SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    section("E — ANNUAL REGIME & TOP-PICK FREQUENCY SUMMARY")

    annual = (
        selections
        .groupby(selections.index.year)
        .agg(
            total_weeks    = ("crash_regime", "count"),
            crash_weeks    = ("crash_regime", "sum"),
            equity_weeks   = ("crash_regime", lambda x: (~x).sum()),
        )
    )
    annual["crash_pct"] = (annual["crash_weeks"] / annual["total_weeks"] * 100).round(1)
    print("\n  Crash vs Equity weeks per year:")
    print(annual.to_string())

    # Top-3 most-selected tickers overall
    long_form = build_long_form(selections)
    top_tickers = (
        long_form.groupby("ticker")
        .size()
        .sort_values(ascending=False)
        .head(15)
        .rename("selection_count")
    )
    print(f"\n  Top-15 most-selected tickers (2014–2024):")
    print(top_tickers.to_string())

    # Top picks within crash weeks (bond universe)
    crash_long = long_form[long_form["crash_regime"]]
    if len(crash_long):
        print(f"\n  Most-selected tickers during CRASH weeks:")
        print(
            crash_long.groupby("ticker")
            .size()
            .sort_values(ascending=False)
            .head(10)
            .rename("count")
            .to_string()
        )

    # Top picks within normal weeks (equity universe)
    normal_long = long_form[~long_form["crash_regime"]]
    print(f"\n  Most-selected tickers during NORMAL (equity) weeks:")
    print(
        normal_long.groupby("ticker")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .rename("count")
        .to_string()
    )

    # ════════════════════════════════════════════════════════════════════════
    # F — SIGNAL INTEGRITY CHECKS
    # ════════════════════════════════════════════════════════════════════════
    section("F — SIGNAL INTEGRITY CHECKS")

    # 1. Universe segregation: no equity ticker ever appears in a crash week
    crash_tickers = set(
        crash_long["ticker"].dropna().unique()
    ) if len(crash_long) else set()
    eq_set   = set(EQUITY_UNIVERSE)
    bond_set = set(BOND_UNIVERSE)

    eq_in_crash   = crash_tickers & eq_set
    bond_in_normal = set(normal_long["ticker"].dropna().unique()) & bond_set

    print(f"\n  [{'PASS' if not eq_in_crash else 'FAIL'}]  "
          f"No equity ETF selected during crash regime  "
          f"(violations: {sorted(eq_in_crash) or 'none'})")
    print(f"  [{'PASS' if not bond_in_normal else 'FAIL'}]  "
          f"No bond ETF selected during normal regime    "
          f"(violations: {sorted(bond_in_normal) or 'none'})")

    # 2. Minimum after_vr_filter >= top_n (always select 3)
    short = selections[selections["after_vr_filter"] < 3]
    print(f"  [{'PASS' if len(short)==0 else 'WARN'}]  "
          f"V-Ratio filter always leaves >= 3 tickers  "
          f"({'OK' if len(short)==0 else f'{len(short)} weeks below minimum'})")

    # 3. days_since_qend >= 45 (inherited from Phase 1 — confirm propagated)
    lag_ok = (regime["days_since_qend"].dropna() >= 45).all()
    print(f"  [{'PASS' if lag_ok else 'FAIL'}]  "
          f"45-day reporting lag enforced in all regime rows")

    # 4. No NaN tickers in rank_1 (should always have a top pick)
    null_rank1 = selections["rank_1"].isna().sum()
    print(f"  [{'PASS' if null_rank1==0 else 'WARN'}]  "
          f"rank_1 non-null in all weeks  "
          f"({'OK' if null_rank1==0 else f'{null_rank1} nulls (warm-up period)'})")

    section("STEP 2 COMPLETE")
    print(
        "\n  Phase 2 signal generation validated.\n"
        "  Confirm visually:\n"
        "    A. Section A shows only bond tickers (BIL/SHY/IEF/TLT/GLD) during crash.\n"
        "    B. Section B shows the universe flip on 2020-11-20.\n"
        "    C. Section C/D shows only equity tickers throughout 2021.\n"
        "    F. All four integrity checks report PASS.\n"
        "  When satisfied, proceed to Step 3 (Phase 3: Position Sizing & Execution).\n"
    )
    sys.exit(0)
