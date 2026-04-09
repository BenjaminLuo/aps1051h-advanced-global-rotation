# Presentation Outline: The Janus Rotational System
**Institutional-Grade Market Regime Detection & Momentum Rotation**

---

### Section 1: Philosophy & Foundation

**Slide 1: Title Slide**
- **Title**: Janus: Evolution of Global Multi-Asset Rotation
- **Subtitle**: Designing Crisis-Resilient High-Growth Engines for the 2024 Macro Regime
- **Presenter**: [Your Name/Team]
- **Visual**: Janus project logo or a clean equity curve overlay.

**Slide 2: The Core Problem**
- **Challenge**: The "Bond-Drain" and the failure of 60/40 diversification in high-inflation/high-vol environments.
- **Goal**: Create a system that is 100% active-equity in bull markets but instantly defensive in macro shocks.
- **The Solution**: Strategic segregation of universes and dual-layer regime filtering.

**Slide 3: Why "Janus"?**
- **Concept**: Named after the two-faced Roman god of transitions and gateways.
- **Logic**: One face looks forward to market growth (Offensive), the other looks back at historical risk and fundamental deterioration (Defensive).
- **Architecture**: A modular pipeline spanning Data Fetching, Signal Generation, Tactical Selection, and Staggered Execution.

**Slide 4: System Architecture Overview**
- **Flow**: `Fetcher` → `Fundamental Signal` + `Macro Signal` → `Regime Detector` → `Selection Engine` → `Laddered Ledger`.
- **Infrastructure**: Python-based, vectorized, and point-in-time compliant.

---

### Section 2: The Double-Filter Regime Engine

**Slide 5: Philosophy of Crash Detection**
- **Premise**: Price alone is a lagging indicator; fundamentals alone are a noisy indicator.
- **The Nexus**: Combining "hard" economic data with "soft" market momentum.
- **Logic**: A "Bear Regime" is triggered if *Either* the Fundamental Filter *Or* the Technical Filter fails.

**Slide 6: The Fundamental Filter**
- **Metric**: Composite Return on Equity (ROE) and Earnings Stability of the SPY Top-10.
- **Constraint**: Strict 45-day reporting lag to ensure no look-ahead bias.
- **Trigger**: Deterioration beyond 2-sigma thresholds marks a structural macro regime shift.

**Slide 7: The Technical Filter (MACD-SMA)**
- **Filter A**: Price must be above the 200-day Simple Moving Average (SMA).
- **Filter B**: MACD (12/26) must maintain a positive histogram.
- **Constraint**: These combined filters eliminate "noise" from shallow dips while capturing major structural rotations.

**Slide 8: Visualizing the Regime (Figure 1)**
- **Action**: Reference **Figure 1 — Regime Overlay**.
- **Explanation**: Illustrate how the system shades red zones for 2008, 2020, and 2022.
- **Visual**: `plots/figure_1_regime_overlay.png`.

**Slide 9: State Transition Logic**
- **Bull State**: 100% Equity Allocation (Global + Sector).
- **Bear State**: 100% Bond/Safe-Haven Allocation.
- **Transition**: Smooth transition over 4 weeks via laddered tranches.

---

### Section 3: Active Selection & Execution

**Slide 10: Universe Segregation**
- **Bond Universe**: 10 safe-haven ETFs (BNDX, TLT, TIP, BIL, etc.).
- **Equity Universe**: 30 high-growth tickers (SPY, QQQ, XLK, MGK, plus global sectors).
- **Strict Rule**: No "Bond-Drain"—bonds are zeroed out in bull regimes to maximize CAGR.

**Slide 11: Tactical Alpha: Dual Momentum**
- **Short Look-back**: 63-day relative strength.
- **Long Look-back**: 126-day structural strength.
- **Metric**: Equal-weighted rank of returns adjusted for technical volatility.

**Slide 12: Selection: The Top-5 Strategy**
- **Concentration**: Select only the Top-5 performers by rank.
- **Rationale**: Captures extreme momentum tails while maintaining enough diversification to handle idiosyncratic shocks.

**Slide 13: Execution: The LadderEngine**
- **Problem**: Rebalancing 100% of a portfolio at once creates massive timing risk (the "Lucky Date" problem).
- **Solution**: Dynamic Tranche Smoothing.
- **Logic**: Split capital into 4 (or 12) independent sub-portfolios rebalanced on staggered dates.

**Slide 14: Capital Allocation Visual (Figure 2)**
- **Action**: Reference **Figure 2 — Capital Allocation**.
- **Explanation**: Show the smooth area chart transitioning between US Equities, Global Equities, and Bonds.
- **Visual**: `plots/figure_2_capital_allocation.png`.

**Slide 15: Institutional Constraints**
- **Execution Lag**: T+1 (Close to Close) model. All signals generated Monday, executed Tuesday.
- **Friction**: 2 bps slippage buffer + $0.005/share commissions.
- **Integrity**: Zero survivorship bias (audited ticker set) and zero look-ahead bias.

---

### Section 4: Performance & Statistical Proof

**Slide 16: Global Performance Overview (2005-2024)**
- **Benchmark**: SPY (100% Equities) and 60/40 ACWI/BND Portfolio.
- **Janus Result**: High-growth characteristics with significant drawdown protection.
- **Visual**: Reference **Figure 3 — Equity & Drawdown**.

**Slide 17: The Equity Curve (Figure 3)**
- **Log Scale**: Provides a realistic view of compounding.
- **Janus vs Benchmark**: Show the outperformance during the 2008 GFC and 2022 rate cycle.
- **Visual**: `plots/figure_3_equity_drawdown.png`.

**Slide 18: Drawdown Analysis**
- **Focus**: Comparing "Underwater" periods.
- **Statistic**: Janus Max Drawdown (-27.8%) vs. SPY (-55.2%).
- **Insight**: Proof of the "Crisis Alpha" mechanism.

**Slide 19: Statistical Validation: White's Reality Check**
- **Concept**: Did we just find a lucky set of parameters? (Data Mining Bias).
- **Method**: 500-iteration bootstrap of "Naive" momentum strategies.
- **Visual**: Reference **Figure 4 — Reality Check Histogram**.

**Slide 20: The p-Value result (Figure 4)**
- **Result**: p-value < 0.05 indicates the Janus Sharpe Ratio is statistically unique.
- **Insight**: High confidence that selection alpha is structural, not random.
- **Visual**: `plots/figure_4_whites_reality_check.png`.

---

### Section 5: Market Regime Case Studies

**Slide 21: Case Study 1: The GFC (2007-2009)**
- **Focus**: Figures 5-8.
- **Narrative**: High outperformance (+9.83% CAGR) while benchmarks collapsed.
- **Visual**: `plots/regime_1_GFC/figure_7_equity_drawdown.png`.

**Slide 22: Case Study 2: The Bull Run (2010-2019)**
- **Focus**: Figures 9-12.
- **Narrative**: Tracking the US Tech-led expansion. Selection Alpha drag vs SPY concentration.
- **Visual**: `plots/regime_2_Bull/figure_10_capital_allocation.png`.

**Slide 23: Case Study 3: Modern Vol (2020-2024)**
- **Focus**: Figures 13-16.
- **Narrative**: Handling COVID and the 2022 Bond/Equity synchronized crash.
- **Visual**: `plots/regime_3_Modern/figure_15_equity_drawdown.png`.

---

### Section 6: Multiverse Robustness Research

**Slide 24: Research Objective: Stress Testing**
- **The "Multiverse Audit"**: Testing 15 distinct scenarios across 5 sensitivity dimensions.
- **Goal**: Find the breakeven points for active management.

**Slide 25: Research 1: Cost Sensitivity**
- **Visual**: Research Figure 1 — Cost Decay Curve.
- **Insight**: Viability limit at 10 bps slippage.
- **Visual**: `plots/research/research_1_cost_sensitivity.png`.

**Slide 26: Research 2: Momentum Sensitivity**
- **Visual**: Research Figure 2 — Bar Chart comparison.
- **Insight**: Slow momentum (6/12mo) is more efficient than fast noise (1/3mo).
- **Visual**: `plots/research/research_2_momentum_windows.png`.

**Slide 27: Research 3: Tranche Smoothing Alpha**
- **Visual**: Research Figure 3 — High-density Comparison.
- **Insight**: 12 tranches significantly outperform 1 tranche via timing risk reduction.
- **Visual**: `plots/research/research_3_tranche_smoothing.png`.

**Slide 28: Research 4: Reporting Lag Stress**
- **Visual**: Research Figure 4 — Lag Sensitivity Line.
- **Insight**: System is robust to even 180-day delays in macro data.
- **Visual**: `plots/research/research_4_fundamental_lag.png`.

**Slide 29: Research 5: Universe Utility**
- **Visual**: Research Figure 5 — The Tech Alpha Gap.
- **Insight**: Diversification is the "principled" choice for capital preservation.
- **Visual**: `plots/research/research_5_universe_comparison.png`.

---

### Section 7: Conclusion & Future Roadmap

**Slide 30: Conclusion**
- **Summary**: Janus is a crisis-resilient, momentum-driven alpha engine.
- **Final Result**: +6.73% CAGR with -27.8% MaxDD.
- **Roadmap**: HRP Optimization, ESG Filtering, and Real-time Execution integration.
- **Closing**: "One strategy, two faces, twenty years of resilience."
