# Janus Rotational System: Advanced Multi-Asset Momentum Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

The **Janus Rotational System** is a high-performance algorithmic trading engine designed to integrate **Rotational Momentum**, **Fundamental Macro Regime Filtering**, and **Time-Laddered Risk Management**. It provides an "All-Weather" investment framework that captures equity upside during bull markets while systematically rotating to safe-haven bonds and gold during macroeconomic downturns.

---

## 🚀 Key Features

- **Double-Filter Macro Regime Switch**: Combines fundamental health (Altman Z-Score & Piotroski F-Score) with technical trend-following (200-day SMA).
- **Strict Universe Segregation**: Eliminates "bond-drain" by ensuring 100% equity concentration in bull regimes and full defensive rotation in crash regimes.
- **Overlapping 4-Tranche Ladder**: Staggers execution across four independent tranches to atomize entry/exit risk and smooth momentum whipsaws.
- **Statistical Validation**: Built-in **White's Reality Check** (bootstrap test) to ensure Alpha is statistically significant against random selection benchmarks.

---

## 🏗 System Architecture

The system operates as a 4-Phase automated pipeline:

1.  **Phase 1: Macro Regime Switch**: Evaluates fundamental proxy health (SPY Top 10) with a 45-day reporting lag to ensure point-in-time accuracy.
2.  **Phase 2: Signal Generation**: Ranks the active universe (Equity vs. Bonds) using Dual Momentum (63/126-day) weighted by trend stability (V-Ratio percentile rank).
3.  **Phase 3: Laddered Execution**: Deploys capital into 4 tranches, with only one tranche rotating per week to minimize temporal impact.
4.  **Phase 4: Analytics & Benchmarking**: Compares cumulative returns, drawdowns, and risk parameters against SPY and 60/40 benchmarks.

---

## 📊 Visual Results (2015–2024 OOS)

### Figure 1: Macro Regime Overlay
Visualizes the macro switch points. Periods shaded in red indicate where the system rotated to defensive assets.
![Macro Regime](plots/figure_1_regime_overlay.png)

### Figure 2: Dynamic Capital Allocation
Demonstrates the staggered 4-week transition between Equities and Bonds during regime switches.
![Capital Allocation](plots/figure_2_capital_allocation.png)

### Figure 3: Equity Curves & Drawdown
Cumulative performance comparison on a log scale (Janus vs. SPY vs. 60/40).
![Equity Curve](plots/figure_3_equity_drawdown.png)

---

## 🛠 Installation & Usage

### 1. Clone & Setup
```bash
git clone https://github.com/BenjaminLuo/aps1051h-advanced-global-rotation.git
cd aps1051h-advanced-global-rotation
pip install -r requirements.txt
```

### 2. Implementation Workflow
The system is modularized into steps for transparency:

- **Step 1: Data Acquisition**: Fetches total-return adjusted price and volume data.
  ```bash
  python run_step1.py
  ```
- **Step 2: Selection Audit**: Generates the weekly top-asset selections.
  ```bash
  python run_step2.py
  ```
- **Step 3: Execution Simulation**: Runs the laddered engine simulation.
  ```bash
  python run_step3.py
  ```
- **Step 4: Benchmarking & Validation**: Final validation, White's Reality Check, and Plot generation.
  ```bash
  python run_step4.py
  ```

---

## 📝 Statistical Validation

The strategy is validated using **White's Reality Check** to control for data-mining bias. We generate 500+ naive strategy permutations to prove that the Janus Sharpe Ratio is structurally superior to random asset selection.

| Metric | Janus System | SPY (100%) | 60/40 Bench |
| :--- | :---: | :---: | :---: |
| **CAGR** | **+9.94%** | +13.08% | +6.54% |
| **Sharpe Ratio** | **0.4863** | 0.6726 | 0.4593 |
| **Max Drawdown** | **-32.09%** | -33.72% | -21.98% |

---

## ⚖️ License

Distributed under the **MIT License**. See `LICENSE` for more information.
