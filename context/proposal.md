Project Proposal: The Global Adaptive Momentum & Fundamental (GAMF) Overlay
The GAMF Overlay is an algorithmic portfolio management system that manages a global rotation of country and sector ETFs. It uses Relative Rotational Momentum to select assets, filters them through Fundamental Value Scores (Altman, Piotroski, Beneish) of their underlying components, and applies a Dynamic Options Hedge (Credit Spreads) when systemic risk indicators or "broken" fundamentals are detected.

Technical Components
- Selection (Hierarchical Clustering): A global country-rotation algorithm that ranks international ETFs alongside US Sector ETFs. Selection is based on hierarchical clustering
- Fundamental Filtering (Value): For the top-ranked momentum ETFs, the system automatically pulls financial data for their top 10 holdings to calculate a consolidated Altman Z-Score and Piotroski F-Score. Assets with "at-risk" scores trigger defensive actions.
- Risk Management (Laddering): Implementation of the "Laddering" system where the portfolio is split into four 25% portions, rebalanced weekly on a staggered 4-week cycle to atomize entry risk without losing momentum.
- Hedging (Options):
    - The "Flotation Line" Trigger: If the Global Breadth Momentum falls below a certain threshold, the system initiates a Bearish Credit Spread or buys ITM Puts on the SPX.
    - The "Broken Company" Trigger: If a top-momentum ETF contains components with Altman < 1.81, the system overlays a Covered Call or Bearish Spread to mitigate downside volatility while maintaining the position.
- Validation (Statistical): Application of White’s Reality Check to the back-testing results
