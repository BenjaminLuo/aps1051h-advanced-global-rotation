FINAL PROJECT PROPOSAL: APS1051

The "Janus" Rotational System: Integrating Value, Momentum, and Laddered Risk

1. Executive Summary

This project proposes the development of a streamlined, multi-asset algorithmic trading system that integrates Rotational Momentum, Value-based Macro Regime filtering, and Laddered Risk Management. The objective is to engineer an "All-Weather" portfolio that captures equity bull markets through momentum, while systematically rotating into safe-haven bonds during macroeconomic downturns.

To ensure mathematical robustness and avoid the pitfalls of over-optimization (e.g., conflicting risk-parity weights or execution blockage), this system utilizes a strict equal-weighting methodology and weekly market-on-close execution. The final architecture will be validated against historical data using White’s Reality Check (evaluating the Sharpe Ratio) to prove statistical significance.

This proposal directly fulfills the requirements of Development Projects 2, 3, 5, 9, and the Value-Based Crash Indicator projects from the course syllabus.

2. System Architecture & Defined Asset Universe

The system operates as a 4-Phase pipeline executed on a weekly basis (Friday close) across two strictly segregated universes.

2.1 The Defined Asset Universe

The strategy restricts its analysis to highly liquid, mega-cap ETFs to ensure realistic execution capability.

Global Equity Universe (20 ETFs): SPY, QQQ, DIA, IWM, MDY, EWC, EFA, EZU, EWJ, EWU, EWG, EWA, EEM, EWZ, XLB, XLE, XLF, XLI, XLK, XLV.

Bond & Safe Haven Universe (10 ETFs): BIL, SHY, IEI, IEF, TLH, TLT, LQD, HYG, BNDX, GLD.

3. Phase-by-Phase Operational Logic

Phase 1: The Global Macro Regime Switch (Value Projects 1-3)

Instead of scraping fundamental data for every stock in every ETF (which is computationally prohibitive and prone to data errors), the system uses the S&P 500 (SPY) as a global macroeconomic proxy.

The Logic: Every week, the system evaluates the aggregate Altman Z-Score and Piotroski F-Score of the SPY's top 10 holdings.

Data Integrity Constraint: Fundamental data points are strictly subject to a 45-day reporting lag following the end of a calendar quarter to entirely eliminate look-ahead bias.

Regime Definition:

Crash Regime: Triggered if Altman Z-Score < 1.87 OR Piotroski F-Score < 4. (System rotates entirely to the Bond Universe).

Normal/Bull Regime: Triggered if Altman Z-Score >= 1.87 AND Piotroski F-Score >= 4. (System rotates entirely to the Equity Universe).

Phase 2: Signal Generation (Project 5 & Lecture 6)

Every Friday, the system ranks the ETFs within the active universe (Equities if Normal Regime, Bonds if Crash Regime).

Rotational Momentum Score: Calculated using a 126-trading-day (6-month) lookback cumulative return.

The V-Ratio Filter: Calculated as 20-day Average Daily Volume / 20-day Standard Deviation of Returns.

Selection: The system filters out the bottom 25% of ETFs based on the V-Ratio (eliminating weak/unsupported trends). It then selects the Top 3 ETFs with the highest Rotational Momentum Score.

Phase 3: Laddered Execution (Projects 2 & 3)

To atomize temporal risk, total portfolio capital is permanently divided into four independent, overlapping tranches (25% of total capital each).

The Ladder Loop: * Only one tranche is rebalanced per week.

When a tranche is active, it liquidates its previous holdings and buys the current week's "Top 3 ETFs" (from Phase 2) using an Equal-Weight allocation (33.3% of the tranche's capital per ETF).

Because the 4 tranches overlap, the total portfolio stays ~100% invested at all times, but capital is staggered across 4 distinct holding periods (4 weeks per tranche), smoothing out the volatility of entry/exit timing.

Execution Constraint: All trades are simulated as Market Orders at the Friday Close. Limit orders are explicitly avoided to ensure the system does not "miss" strong momentum breakouts.

Transaction Costs: A commission of $0.005 per share and a slippage penalty of 2 basis points (0.0002) are applied to every executed trade.

4. Implementation & Backtesting Framework

Data Source: yfinance for daily Total Return (adjusted close) and Volume data.

Out-of-Sample Period: January 1, 2015 – December 31, 2024.

Benchmarks: The strategy will be benchmarked against a 100% S&P 500 portfolio (SPY) and a 60/40 Global Portfolio (60% ACWI / 40% BND).

5. Evaluation & Statistical Validation (Project 9)

To prove the system's Alpha is not the result of data snooping or the natural upward drift of a secular bull market, the system will undergo rigorous statistical testing.

Key Performance Indicators (KPIs): CAGR, Sharpe Ratio (using a 2% risk-free rate), Sortino Ratio, and Maximum Drawdown.

White’s Reality Check (Corrected Methodology):

The backtester will generate a null distribution of 500+ "naive" strategy permutations (e.g., selecting 3 random ETFs every week regardless of momentum or fundamentals).

The evaluation metric bootstrapped will be the Annualized Sharpe Ratio (not raw mean returns) to accurately assess risk-adjusted superiority.

A p-value of < 0.05 will be required to reject the null hypothesis and confirm the Janus system's structural edge.

6. Proposed Deliverables & Figures

The final project report will include the commented Python codebase and the following specific visualizations:

Macro Regime Overlay Chart: A time-series chart of the S&P 500 with shaded background regions indicating exact periods where the Altman/Piotroski Crash Regime was active (e.g., 2020, 2022).

Dynamic Capital Allocation Area Plot: A 100% stacked area chart showing the portfolio's shifting exposure between Equities and Bonds over time based on the macro switch.

Cumulative Equity & Drawdown Curves: The finalized out-of-sample equity curve of the Janus System plotted against the SPY and 60/40 benchmarks, featuring an underwater drawdown plot.

White's Reality Check Histogram: A statistical distribution plot of the bootstrapped naive Sharpe Ratios, with a vertical red line explicitly marking the Janus strategy's achieved Sharpe Ratio to visualize the p-value.

7. Conclusion

By returning to the core fundamentals of Rotational Momentum, SPY-based Macro Regime filtering, and Time-Laddered risk atomization, this streamlined approach removes mathematical conflicts (such as Risk Parity bond-drain) while fulfilling the rigorous requirements of APS1051. The result will be a statistically significant, highly executable quantitative portfolio.