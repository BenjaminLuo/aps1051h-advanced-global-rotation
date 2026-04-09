# Janus Rotational System: Technical Strategy Specification

The Janus Rotational System is an institutional-grade algorithmic strategy that integrates **Macro Regime Detection**, **Cross-Sectional Momentum Selection**, and **Staggered Execution** to deliver high risk-adjusted returns across multiple market cycles.

---

## 1. Investment Philosophy: "The Dual-Pivot"
The system is built on the premise that market regimes are not binary, but rather a transition of liquidity and fundamental health.
- **Offense (Bull Regime)**: Maximize Alpha through concentrated momentum in the most stable, high-volume growth ETFs.
- **Defense (Crash Regime)**: Preserve capital by rotating to high-convexity safe-havens (Long Bonds, Gold) when macro thresholds are breached.

---

## 2. Core Algorithmic Logic

### Phase 1: Macro Regime Switch
The system maintains a "Regime Flag" updated every Friday based on an **OR-Logic Double Filter**:

1.  **Fundamental Filter**: Aggregated health of SPY Top-10 constituents.
    - **Altman Z-Score < 1.87** (Financial distress) OR **Piotroski F-Score < 4** (Operational rot).
    - **Constraint**: Strict 45-day reporting lag to prevent look-ahead bias.
2.  **Technical Filter**: Broad market trend.
    - **SPY Close < 200-day SMA**. Provides immediate reaction to rapid crashes (e.g., COVID 2020) before fundamentals reflect the damage.

**Regime Exit**: To re-enter the bull market, BOTH signals must be clear, preventing "false start" whipsaws during volatile bottoms.

### Phase 2: Signal Generation (Selection)
Every Friday, the system ranks the active universe (Equity or Bond) using:

1.  **Dual Momentum**: An average of 63-day and 126-day total returns. This captures both recent acceleration and medium-term persistence.
2.  **V-Ratio Normalization**: Momentum scores are multiplied by the asset's V-Ratio percentile rank (Volume / Volatility). 
    - This penalizes "thin" or "choppy" ETFs and prioritizes those with institutional-grade liquidity and smooth trend stability.

### Phase 3: Laddered Execution
The system manages capital via a **4-Tranche Overlapping Ladder**:
- **Staggered Rotation**: Only 25% of the portfolio (one tranche) is eligible for rebalance in any given week.
- **Execution Lag**: Signals generated at Friday close are executed at **Monday Close**. This ensures zero peeking into intra-day Friday prices.
- **Cost Model**: Every trade accounts for 2bps slippage and $0.005/share commission.

---

## 3. Backtesting Methodology

### Horizon and Data
- **Window**: 20 Years (2005–2024).
- **Stitching/Proxies**: For the early 2000s where certain ETFs (like ACWI or BND) were unavailable, the system utilizes high-correlation proxies (SPY, AGG) to ensure a continuous, valid historical record.
- **Financial Rigor**: Data is total-return adjusted (dividends/splits handled) and reindexed to ensure point-in-time compliance.

### Validation Tiers
1.  **Stress Testing (GFC Experiment)**: Comparison of 'Aggressive' vs 'Recovery' fundamental paths during the 2008 crisis to test regime sensitivity.
2.  **Regime Partitioning**: Categorization of results into Historical Epochs (**GFC, Long Bull, Modern Vol**) to identify where the strategy generates its primary Alpha.
3.  **White's Reality Check (Bootstrap)**: A rigorous statistical test that compares Janus performance against 100+ "Randomized Janus" clones to ensure the results are not a product of luck or "data mining."

---

## 4. Evaluation Framework

The system is evaluated on four primary vectors:

| Metric | Target | Rationale |
| :--- | :--- | :--- |
| **CAGR** | > SPY / 60-40 | Demonstrating capital appreciation capability. |
| **Max Drawdown** | < -30% (in GFC) | Validating the effectiveness of the defensive rotation. |
| **Sharpe Ratio** | > 0.40 | Efficiency of returns relative to volatility. |
| **p-value** | < 0.05 | Statistical proof of strategy robustness (Target level). |

## 📐 Current Design Constraints
- **Survivorship Bias**: Fixed universe of 2024-active tickers (documented limitation).
- **Execution**: Market-on-Monday-Close assumption.
