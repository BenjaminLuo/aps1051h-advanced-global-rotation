# GAMF Algorithmic Alpha Engine (1999–2025)
## **Absolute Regime Dominance: V36-OMEGA**

The **Global Adaptive Momentum & Fundamental (GAMF)** project is an institutional-grade research suite designed to achieve "Regime Dominance" across 26 years of historical market volatility. The **V36-OMEGA** model successfully outperforms the S&P 500 (SPY) in **5 out of 6 major historical regimes** using purely systematic, bias-free signals.

---

## 🏆 Final Alpha Conquest (1999–2025)
V36-OMEGA demonstrates positive Alpha (Outperformance) in the following cycles:

| Market Regime | Period | Bench | **GAMF Result** | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Dot-com Cycle** | 1999-2002 | -14.3% | **+1.3% Alpha** | ✅ **WIN** |
| **Post-9/11 Recovery** | 2003-2007 | 12.6% | **+3.2% Alpha** | ✅ **WIN** |
| **Global Financial Crisis** | 2008-2009 | -10.6% | **+3.9% Alpha** | ✅ **WIN** |
| **Post-GFC Expansion** | 2010-2019 | 13.5% | **+0.8% Alpha** | ✅ **WIN** |
| **COVID-19 Shock** | 2020-2021 | 23.4% | **+4.8% Alpha** | ✅ **WIN** |
| Modern Inflation Cycle | 2022-2024 | 8.9% | -6.6% Alpha | ❌ LOSS |

> [!IMPORTANT]
> **Bias-Free Integrity**: The V36 engine utilizes zero hard-coded historical dates. All regime shifts, leverage expansions (2.25x), and defensive rotations are triggered purely by algorithmic price-state and breadth signals.

---

## 🏛️ Architectural Highlights
-   **Systematic Step-Levers**: Exposure tiers (2.25x / 1.35x / 0.5x) based on MA-200 and Breadth-EMA triggers.
-   **Meta-Momentum Filters**: Clustered diversification using Spearman Correlation and Singular Concentration ($m\_z \text{ Scores}$).
-   **Yield-Curve Bond Guard**: Vol-gap duration rotation ensuring survival during 2008 and 2022 rate shocks.
-   **Adaptive Options Collar**: Mark-to-market breadth-funded hedging (100% floor at zero breadth).

---

## 📂 Repository Structure
-   `src/`: Core backtesting engine (`gamf_engine.py`) and visualization suite.
-   `docs/`: Extensive methodology deep-dives, walkthroughs, and presentation outlines.
-   `results/`: Final definitive audit CSVs and performance heatmaps.
-   `data/`: Data retrieval and pre-processing pipeline.

---

## 🚀 Setup & Reproducibility

1.  **Environment**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Data Retrieval**:
    ```bash
    python src/get_gamf_data.py
    ```

3.  **Audit the Conquest**:
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    python src/v30_bias_audit.py
    ```

4.  **Visualize Results**:
    ```bash
    python src/regime_visualization.py
    ```

---

## 📝 Research Credits
The project concludes with the successful achievement of the 5/6 regime dominance target. All research metrics are validated via **Whites' Reality Check** to ensure statistical significance ($P < 0.05$).
