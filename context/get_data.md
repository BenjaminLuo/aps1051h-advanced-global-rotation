Context Document: WRDS Data Acquisition for GAMF Overlay Project

1. Project Overview

This document provides the data requirements to build the Global Adaptive Momentum & Fundamental (GAMF) Overlay.
The system relies on algorithmic portfolio management using:

Relative Rotational Momentum (via Hierarchical Clustering) of global country and US sector ETFs.

Fundamental Filtering of the top 10 underlying equities within the highest-ranked ETFs using Altman Z-Score, Piotroski F-Score, and Beneish M-Score.

Dynamic Options Hedging (Credit Spreads/Puts) triggered by "broken" fundamentals or deteriorating global market breadth.

Goal for AI: Generate Python code using the wrds library (and standard pandas/SQL workflows) to fetch, clean, and merge this data without look-ahead or survivorship bias.

2. Target Asset Universe (ETFs)

The pipeline must pull historical daily data for the following ETFs:

US Sectors: XLK, XLF, XLV, XLY, XLC, XLI, XLE, XLP, XLB, XLU, XLRE

Global/Country: SPY (Benchmark), EFA, EEM, EWJ, EWG, EWU, EWC, MCHI, FXI, INDA, EWZ, EWT

3. WRDS Database Mapping & Requirements

A. ETF Pricing & Returns

Source: CRSP (crsp.dsf - Daily Stock File)

Required Fields: date, permno, prc (Closing Price), vol (Volume), ret (Daily Return), shrout (Shares Outstanding).

Objective: Calculate momentum and perform hierarchical clustering on the ETF universe.

B. Point-in-Time ETF Holdings (The "Look-Through")

Source: CRSP Mutual Fund Database (crsp.holdings) OR Thomson Reuters s12 (tfn.s12).

Required Fields: report_dt, fundno, ticker, crsp_permno (or cusip of the underlying asset), percent_tna (Weight in portfolio).

Objective: For any given rebalance date, identify the exact Top 10 holdings of an ETF as they were reported at that time.

C. Fundamental Corporate Data (For Filtering)

Source: Compustat North America / Global (comp.fundq - Fundamentals Quarterly).

Required Fields:

Identifiers/Dates: gvkey, datadate (Fiscal period end), rdq (Report Date of Quarter - CRITICAL for avoiding look-ahead bias).

Altman Z-Score Components: actq (Current Assets), lctq (Current Liab), req (Retained Earnings), ebitq (EBIT), atq (Total Assets), saleq (Sales), ltq (Total Liab), prccq * cshoq (Market Value of Equity).

Piotroski F-Score Components: ibq (Net Income), oancfy (Operating Cash Flow), dlttq (Long Term Debt), seqq (Shareholder Equity), cogsq (COGS).

Beneish M-Score Components: cheq (Cash & Equivalents), dlcq (Debt in Current Liab), rectq (Receivables), xsgaq (SG&A), dpq (Depreciation), ppegtq (Gross PPE).

Objective: Calculate the Z, F, and M scores for the underlying equities of the selected ETFs.

D. Options Data (For Hedging Triggers)

Source: OptionMetrics Ivy DB US (optionm.opprcd - Daily Price).

Required Fields: date, secid, cp_flag (Call/Put), strike_price, exdate (Expiration), best_bid, best_offer, impl_volatility, delta, open_interest.

Objective: Price bearish credit spreads and ITM SPY puts historically based on fundamental/momentum trigger dates.

4. Critical Data Engineering Guidelines for Code Generation

When writing the Python/SQL data extraction code, the AI must adhere to these quantitative backtesting standards:

The CRSP-Compustat Link (CCM): ETFs and underlying stocks in CRSP use PERMNO identifiers, while Compustat uses GVKEY. The code must use the crsp.ccmxpf_linktable to accurately map PERMNOs to GVKEYs based on the linkdt and linkenddt (effective dates of the link).

Point-in-Time Fundamentals:
Accounting data must be joined to pricing/portfolio data using Compustat's rdq (Report Date of Quarter), NOT datadate. If rdq is used, the algorithm only "sees" fundamental data that was actually publicly available to the market on that specific trading day.

Missing Data Handling:
Specify how to handle nulls in Compustat (e.g., standardizing OANCF if missing by approximating from net income and depreciation, or dropping the equity from the Top 10 calculation).

Date Filtering:
Implement a unified historical date range (e.g., 2010-01-01 to present) across all SQL queries to limit memory usage when pulling from OptionMetrics and CRSP.

5. Expected Output DataFrames

The resulting Python code should ideally output three clean Pandas DataFrames:

df_etf_universe: Daily prices and returns for the target ETFs.

df_etf_holdings_fundamentals: A combined panel dataset indexed by [Date, ETF_Ticker, Underlying_GVKEY] containing the Top 10 underlying components and their calculated Altman/Piotroski/Beneish scores for that specific date.

df_options_chain: Filtered daily options chains for SPY and the target ETFs to simulate the hedging ladder.