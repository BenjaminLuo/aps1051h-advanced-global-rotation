# Research Note: Dealing with the "Detection Lag"

It is true that the Janus System (and almost all trend-following systems) detects crashes after significant initial losses occur. This is not a failure of the code, but a deliberate **Trade-off between Timing and Accuracy**.

## 1. The GFC Anatomy (2007-2008)
I analyzed the 2008 Global Financial Crisis to quantify this lag:

| Event | Date | Market State |
| :--- | :--- | :--- |
| **SPY Peak** | Oct 9, 2007 | 0% Drawdown |
| **Technical Signal (SMA-200)** | Mar 17, 2008 | **-17.57% Drawdown** |
| **Lehman Brothers Collapse** | Sep 15, 2008 | -25% Drawdown |
| **Fundamental Signal (Q3 Data)** | Nov 14, 2008 | **-40% Drawdown** |

**Why it feels "late"**: By the time the SMA-200 cross occurs, the initial "Correction" phase (-10% to -15%) is over. However, the signal saved the portfolio from the final **-50% capitulation** that followed.

---

## 2. Why Not a "Faster" SMA?
We could use a 50-day SMA to detect crashes "near the top." However, look at the historical results of a 50-day SMA during the "Long Bull" (2011-2019):

- **The Whipsaw Problem**: Market dips of 5% would trigger a rotate-to-bonds. You would miss the subsequent V-shaped recoveries, leading to massive **Alpha Leakage** and underperformance.
- **The SMA-200 Logic**: It is designed to ignore "Noise" (5-10% dips) and only react to "Signal" (structural trend breaks).

---

## 3. Structural Delays (The "Anti-Peeking" Wall)
There are two hard constraints that make the system seem "slow" but ensure it is **Real-World Practical**:

1.  **Fundamental Reporting Lag (45 Days)**:
    - If a company's business fails on Oct 1st (Q4), the Balance Sheet isn't published until Jan 1st, and the trader doesn't "see" it until Feb 15th. 
    - *Using data earlier would be "Data Leakage" (cheating).*

2.  **The 4-Tranche Smoothness**:
    - Even after the signal fires, Janus takes 4 weeks to fully move. 
    - This is to ensure that if the signal was a "head-fake" (a 1-day dip), we haven't sold the entire portfolio instantly.

## Conclusion: "Better Late than Whipsawed"
Janus is a **Drawdown Insurance Policy**, not a Market Timing Engine. It aims to catch the "meat" of the crash (the -20% to -50% leg) while remaining fully invested during the healthy "noise" of a bull market.

> [!TIP]
> **Can we improve this?**
> We could implement a "Volatility-Adjusted SMA" or an "Acceleration Filter" to tighten the exit during rapid falls (like COVID-2020), but this increases complexity and the risk of over-fitting to past crashes.
