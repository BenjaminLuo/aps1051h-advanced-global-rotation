"""
Janus Rotational System — Central Configuration
================================================
All universe definitions, thresholds, and global constants live here.
No business logic; downstream modules import from this file only.
"""

# ── Asset Universes ────────────────────────────────────────────────────────────
EQUITY_UNIVERSE: list[str] = [
    # US Broad Market
    "SPY", "QQQ", "DIA", "IWM", "MDY",
    # Developed International
    "EWC", "EFA", "EZU", "EWJ", "EWU", "EWG", "EWA",
    # Emerging Markets
    "EEM", "EWZ",
    # US Sector ETFs (GICS Level-1)
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLV",
]

BOND_UNIVERSE: list[str] = [
    # Treasuries — short to long duration
    "BIL", "SHY", "IEI", "IEF", "TLH", "TLT",
    # Credit
    "LQD", "HYG",
    # International Fixed Income
    "BNDX",
    # Safe-Haven Commodity (treated as bond-universe member per proposal)
    "GLD",
]

# ── SPY Macro Proxy ────────────────────────────────────────────────────────────
# Largest S&P 500 constituents used as fundamental proxy for the index.
# Ticker list is stable across the 2014–2024 back-test window at the
# mega-cap level.  BRK-B and JPM represent financials; JNJ/UNH represent
# healthcare — sectors with distinct Z-score behaviour from pure tech.
SPY_TOP10: list[str] = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META",
    "NVDA", "BRK-B", "JPM", "JNJ", "UNH",
]

# ── Data Window ────────────────────────────────────────────────────────────────
DATA_START: str = "2014-01-01"   # includes 1-year buffer for lookback warmup
DATA_END:   str = "2024-12-31"

# ── Phase 1 — Macro Regime Switch ─────────────────────────────────────────────
# Altman Z-Score: < 1.81 = distress zone; 1.81–2.99 = grey zone.
# We use 1.87 (mid grey-zone) as the conservative crash trigger.
ALTMAN_CRASH_THRESHOLD:    float = 1.87

# Piotroski F-Score: 0–9 integer scale.  < 4 indicates deteriorating
# profitability / leverage / liquidity signals in aggregate.
PIOTROSKI_CRASH_THRESHOLD: int   = 4

# SEC mandates 10-Q filing within 40 days of quarter-end for large
# accelerated filers.  We use 45 days to be conservative.
REPORTING_LAG_DAYS: int = 45

# ── Janus 2.0 — Upgraded Signal Parameters ───────────────────────────────────
# Dual momentum windows (average of 3-month + 6-month returns)
MOMENTUM_SHORT_WINDOW: int = 63     # ≈ 3 calendar months
MOMENTUM_LONG_WINDOW:  int = 126    # ≈ 6 calendar months

# Top-N selections per week (increased from 3 → 5 for diversification)
TOP_N_SELECTIONS: int = 5

# Technical crash filter: SPY below its 200-day SMA triggers crash regime
SMA_CRASH_WINDOW: int = 200

# ── Reproducibility ───────────────────────────────────────────────────────────
RANDOM_SEED: int = 42
