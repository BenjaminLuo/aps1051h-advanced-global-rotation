import wrds
import pandas as pd
import numpy as np
import warnings
import os
from datetime import datetime

# Suppress warnings for cleaner production output
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

print("\n" + "="*50)
print("EXECUTING: GAMF DATA PIPELINE V3.60 (FINAL COMPLETE)")
print("LOCATION : " + os.path.abspath(__file__))
print("="*50 + "\n")

# ==============================================================================
# CONFIGURATION & PARAMETERS
# ==============================================================================
# ULTRA_PILOT: Extremely restricted run to bypass resource limits (2 ETFs, 1 Month)
ULTRA_PILOT = False

if ULTRA_PILOT:
    print("[INFO] !!! ULTRA-PILOT MODE ACTIVE (SPY/XLK, Jan 2024) !!!")
    ETF_UNIVERSE = ['SPY', 'XLK']
    START_DATE = '2024-01-01'
    END_DATE = '2024-02-01'
else:
    # Full universe
    US_SECTORS = ['XLK', 'XLF', 'XLV', 'XLY', 'XLC', 'XLI', 'XLE', 'XLP', 'XLB', 'XLU', 'XLRE']
    GLOBAL_ETFS = ['SPY', 'EFA', 'EEM', 'EWJ', 'EWG', 'EWU', 'EWC', 'MCHI', 'FXI', 'INDA', 'EWZ', 'EWT', 'TLT', 'SHY']
    ETF_UNIVERSE = US_SECTORS + GLOBAL_ETFS
    START_DATE = '1999-01-01'
    END_DATE = '2025-01-01' # Adjusted to Jan 2025 for final data
REBALANCE_FREQ = 'W-FRI' 

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================
def run_query(db, sql, date_cols=None):
    """Pure DBAPI query engine using standard cursor to bypass SQLAlchemy conflicts."""
    try:
        # WRDS db.connection is a SQLAlchemy Connection; 
        # its .connection attribute is a ConnectionFairy with a raw cursor()
        conn_fairy = db.connection.connection
        with conn_fairy.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            df = pd.DataFrame(rows, columns=cols)
            
            # Type and Date conversion
            if date_cols and not df.empty:
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                        
            # Numeric conversion (from Decimal to float)
            num_cols = ['weight', 'prc', 'ret', 'vol', 'shrout', 
                        'atq', 'ltq', 'actq', 'lctq', 'req', 'oiadpq', 'saleq', 
                        'prccq', 'cshoq', 'niq', 'oancfy', 'dlttq', 'seqq', 
                        'cogsq', 'cheq', 'dlcq', 'rectq', 'xsgaq', 'dpq', 'ppegtq',
                        'permno', 'crsp_permno', 'recovered_permno', 'securityid',
                        'secid', 'strike_price', 'best_bid', 'best_offer', 'impl_volatility',
                        'delta', 'open_interest', 'volume']
            for col in df.columns:
                if col in num_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
    except Exception as e:
        print(f"  [ERROR] DBAPI execution failed: {e}")
        return pd.DataFrame()

def connect_wrds():
    """Connect to WRDS as 'b33luo' utilizing existing credentials."""
    print("[INFO] Connecting to WRDS...")
    try:
        db = wrds.Connection(wrds_username='b33luo')
        return db
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return None

def fetch_etf_portnos(db, tickers):
    """Exhaustive search to map ETF Tickers to Portfolio IDs across WRDS versions."""
    print(f"[INFO] Mapping {len(tickers)} tickers to Portfolio IDs...")
    
    # Candidate Libraries and Tables (Corrected for psycopg2 underscore schemas)
    candidates = [
        ('crsp_m_mutualfunds', 'fund_names'),
        ('crsp_m_mutualfunds', 'fund_hdr'),
        ('crsp_q_mutualfunds', 'fund_names'),
        ('crsp', 'fund_names'),
        ('crsp', 'fund_header')
    ]
    
    for lib, table in candidates:
        try:
            full_table = f"{lib}.{table}"
            # Construct condition: search for SPY with wildcard, others as exact matches
            conds = []
            for t in tickers:
                if t == 'SPY':
                    conds.append(f"UPPER(TRIM(ticker)) LIKE '{t}%'")
                else:
                    conds.append(f"UPPER(TRIM(ticker)) = '{t}'")
            
            sql = f"SELECT ticker, crsp_portno FROM {full_table} WHERE ({' OR '.join(conds)})"
            df = run_query(db, sql)
            if not df.empty:
                print(f"  [SUCCESS] Found mapping in {full_table}")
                df['source_lib'] = lib
                # [FIXED] Keep ALL identifiers (Legacy + Modern)
                for t in tickers:
                    mask = df['ticker'].astype(str).str.upper().str.strip().str.startswith(t)
                    df.loc[mask, 'ticker'] = t
                return df # Return all mappings found
        except:
            continue
            
    print("[ERROR] Could not map tickers to Portnos.")
    return pd.DataFrame()

def fetch_etf_universe_data(db, tickers, start_date, end_date):
    """Fetch daily return data for ETFs from crsp.dsf."""
    print(f"[INFO] Fetching daily prices for {len(tickers)} ETFs...")
    ticker_str = "','".join(tickers)
    
    sql = f"""
        SELECT a.date, b.ticker, a.permno, a.prc, a.ret, a.vol, a.shrout
        FROM crsp.dsf AS a
        INNER JOIN crsp.msenames AS b
        ON a.permno = b.permno
        WHERE b.ticker IN ('{ticker_str}')
        AND a.date >= '{start_date}'
        AND a.date <= '{end_date}'
        AND a.date >= b.namedt AND a.date <= b.nameendt
    """
    df = run_query(db, sql, date_cols=['date'])
    if not df.empty:
        df['prc'] = df['prc'].abs() # Handle negative prices (CRSP convention)
    return df

def fetch_etf_holdings(db, port_ids, date_list):
    """Fetch Top 10 holdings for ETFs using portfolio IDs and multiple schema discovery."""
    if port_ids.empty: return pd.DataFrame()
    
    print(f"[INFO] Fetching underlying holdings for {len(port_ids)} Portfolio IDs...")
    port_ids['crsp_portno'] = port_ids['crsp_portno'].astype(str)
    port_str = "','".join(port_ids['crsp_portno'].unique())
    
    dates_df = pd.DataFrame({'date': date_list})
    dates_df['year'] = dates_df['date'].dt.year
    holdings_dfs = []
    
    # [FIXED] Pre-verify existing holdings tables to prevent UNION ALL failures
    known_holdings = []
    libs_to_check = ['crsp', 'crsp_q_mutualfunds']
    for lib in libs_to_check:
        try:
            tables = db.list_tables(library=lib)
            if 'holdings' in tables:
                known_holdings.append(f"{lib}.holdings")
        except: continue
    
    print(f"  [INFO] Using verified holdings sources: {known_holdings}")
    
    for year in dates_df['year'].unique():
        group = dates_df[dates_df['year'] == year]
        min_date = group['date'].min().strftime('%Y-%m-%d')
        max_date = group['date'].max().strftime('%Y-%m-%d')
        
        # [REFACTORED] Multi-Source Holdings Capture
        # We query both modern and legacy tables simultaneously to maximize depth.
        queries = []
        for source in known_holdings:
            sql = f"SELECT report_dt, crsp_portno, permno as crsp_permno, ticker as asset_ticker, percent_tna as weight FROM {source} WHERE crsp_portno IN ('{port_str}') AND report_dt >= '{min_date}'::date - interval '6 months' AND report_dt <= '{max_date}'"
            queries.append(sql)
        
        if not queries: continue
        
        # Execute Union of verified sources
        union_sql = " UNION ALL ".join(queries).replace("SELECT", "SELECT DISTINCT", 1)
        yearly_raw = run_query(db, union_sql, date_cols=['report_dt'])
        
        if yearly_raw.empty: continue
        
        # [NEW] Identifier Recovery logic: if crsp_permno is missing, try looking up via asset_ticker
        missing_permno_mask = yearly_raw['crsp_permno'].isna()
        if missing_permno_mask.any():
            unique_assets = yearly_raw.loc[missing_permno_mask, 'asset_ticker'].dropna().unique()
            if len(unique_assets) > 0:
                asset_str = "','".join(unique_assets)
                recovery_sql = f"SELECT DISTINCT ticker as asset_ticker, permno as recovered_permno FROM crsp.msenames WHERE ticker IN ('{asset_str}')"
                recovery_map = run_query(db, recovery_sql)
                if not recovery_map.empty:
                    yearly_raw = pd.merge(yearly_raw, recovery_map, on='asset_ticker', how='left')
                    yearly_raw['crsp_permno'] = yearly_raw['crsp_permno'].fillna(yearly_raw['recovered_permno'])
        
        # Merge back the original ETF ticker for identification
        yearly_raw['crsp_portno'] = yearly_raw['crsp_portno'].astype(str)
        port_ids['crsp_portno'] = port_ids['crsp_portno'].astype(str)
        yearly_raw = pd.merge(yearly_raw, port_ids, on='crsp_portno')
        yearly_raw['weight'] = pd.to_numeric(yearly_raw['weight'], errors='coerce').fillna(0)
        
        # Match each rebalance date in the year to the nearest prior report_dt
        for rebalance_date in group['date']:
            mask = (yearly_raw['report_dt'] <= rebalance_date) & \
                   (yearly_raw['report_dt'] > rebalance_date - pd.Timedelta(days=180))
            
            snapshot = yearly_raw[mask].copy()
            if snapshot.empty: continue
            
            # [FIXED] Deduplication logic for overlapping IDs in transition quarters
            # Group by ticker to ensure we don't double count if 2 IDs exist for 1 ticker
            snapshot = snapshot.sort_values(['ticker', 'weight'], ascending=[True, False])
            # Keep top 10 unique asset permnos per ticker
            top_holdings = snapshot.drop_duplicates(subset=['ticker', 'crsp_permno']).groupby('ticker').head(10).copy()
            top_holdings['rebalance_date'] = rebalance_date
            holdings_dfs.append(top_holdings)
            
    if not holdings_dfs: 
        print("  [WARNING] No holdings snapshots found for the given rebalance dates.")
        return pd.DataFrame()
    
    res = pd.concat(holdings_dfs, ignore_index=True)
    print(f"  [INFO] Total raw holdings rows: {len(res)}")
    if not res.empty:
        print(f"  [INFO] Sample PERMNOs from holdings: {res['crsp_permno'].unique()[:10]}")
    return res

def fetch_quarterly_fundamentals(db, gvkeys, start_date, end_date):
    """Fetch quarterly data from comp.fundq (using oiadpq for EBIT)."""
    if not gvkeys: return pd.DataFrame()
    
    print(f"[INFO] Fetching fundamentals for {len(gvkeys)} keys...")
    # Chunking for efficiency
    chunk_size = 500
    gvkey_chunks = [gvkeys[i:i + chunk_size] for i in range(0, len(gvkeys), chunk_size)]
    
    df_list = []
    for chunk in gvkey_chunks:
        gvkey_str = "','".join(chunk)
        # oiadpq is the standard EBIT field in Compustat Quarterly
        # Increased lookback and COALESCE to ensure rdq exists for merge_asof
        sql = f"""
            SELECT gvkey, datadate, COALESCE(rdq, datadate + interval '2 months') as rdq, fyearq, fqtr, 
                   atq, ltq, actq, lctq, req, oiadpq, saleq, prccq, cshoq,
                   niq, COALESCE(oancfy, niq + dpq) as oancfy, dlttq, seqq, cogsq,
                   cheq, dlcq, rectq, xsgaq, dpq, ppegtq 
            FROM comp.fundq
            WHERE gvkey IN ('{gvkey_str}')
            AND datadate >= '{start_date}'::date - interval '2 years' AND datadate <= '{end_date}'
            AND indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D' AND consol = 'C'
        """
        df_list.append(run_query(db, sql, date_cols=['datadate', 'rdq']))
        
    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

def fetch_ccm_links(db):
    """Fetch CRSP-Compustat Link Table."""
    print("[INFO] Fetching CCM link table...")
    sql = f"""
        SELECT gvkey, lpermno AS permno, linkdt, COALESCE(linkenddt, '2099-12-31') as linkenddt
        FROM crsp.ccmxpf_lnkhist
        WHERE linktype IN ('LU', 'LC') AND linkprim IN ('P', 'C')
    """
    df = run_query(db, sql, date_cols=['linkdt', 'linkenddt'])
    if not df.empty:
        df['permno'] = pd.to_numeric(df['permno'], errors='coerce')
    return df

def fetch_options_data(db, tickers, start_date, end_date):
    """Fetch Full Options Chains for US ETFs and SPY using Annual Tables (bypass global view)."""
    us_sectors = ['XLK', 'XLF', 'XLV', 'XLY', 'XLC', 'XLI', 'XLE', 'XLP', 'XLB', 'XLU', 'XLRE']
    us_tickers = [t for t in tickers if t in us_sectors or t == 'SPY']
    
    print(f"[INFO] Fetching Annual Options data for {len(us_tickers)} US ETFs...")
    ticker_str = "','".join(us_tickers)
    
    # 1. Map Tickers to SecurityIDs
    secid_sql = f"SELECT ticker, securityid FROM optionm.ticker WHERE ticker IN ('{ticker_str}')"
    secids = run_query(db, secid_sql)
    if secids.empty: return pd.DataFrame()
    
    secid_list = "','".join(secids['securityid'].astype(str).unique())
    
    # 2. Iterate through years and fetch from annual tables (opprcdYYYY)
    start_year = pd.to_datetime(start_date).year
    end_year = pd.to_datetime(end_date).year
    
    all_years = []
    for year in range(start_year, end_year + 1):
        year_table = f"optionm.opprcd{year}"
        print(f"  -> Querying {year_table}...")
        # Note: Annual tables in OptionMetrics US use 'secid' whereas 'ticker' table uses 'securityid'
        sql = f"""
            SELECT date, secid, cp_flag, strike_price, exdate, best_bid, best_offer, impl_volatility, delta, open_interest, volume
            FROM {year_table}
            WHERE secid IN ({secid_list})
            AND ABS(delta) BETWEEN 0.2 AND 0.8
        """
        try:
            df_year = run_query(db, sql, date_cols=['date', 'exdate'])
            if not df_year.empty:
                # Standardize identifier for merging
                df_year.rename(columns={'secid': 'securityid'}, inplace=True)
                all_years.append(df_year)
        except Exception as e:
            print(f"  [WARNING] Failed to fetch {year_table}: {e}")
            
    if not all_years: return pd.DataFrame()
    
    df = pd.concat(all_years, ignore_index=True)
    return pd.merge(df, secids, on='securityid', how='left') if not df.empty else df

# ==============================================================================
# CALCULATIONS
# ==============================================================================
def calculate_altman_z(df):
    """Calculate Altman Z-Score with zero-division protection."""
    atq_safe = df['atq'].replace(0, np.nan)
    ltq_safe = df['ltq'].replace(0, np.nan)
    
    x1 = (df['actq'] - df['lctq']) / atq_safe
    x2 = df['req'] / atq_safe
    x3 = df['oiadpq'] / atq_safe # Using oiadpq for EBIT
    x4 = (df['prccq'] * df['cshoq']) / ltq_safe
    x5 = df['saleq'] / atq_safe
    return 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5

def calculate_piotroski_f(df):
    """Calculate 9-point Piotroski F-Score (Quarterly version)."""
    # 1. ROA (Profitability)
    df = df.sort_values(['gvkey', 'datadate'])
    atq_lag = df.groupby('gvkey')['atq'].shift(1).replace(0, np.nan)
    roa = df['niq'] / atq_lag
    f1 = (roa > 0).astype(int)              # Positive ROA
    
    # 2. Operating Cash Flow (CFO)
    # Adjustment for YTD OANCFY
    niq_lag = df.groupby('gvkey')['niq'].shift(1)
    oancfy_lag = df.groupby('gvkey')['oancfy'].shift(1)
    oancfq = np.where(df['fqtr'] == 1, df['oancfy'], df['oancfy'] - oancfy_lag)
    f2 = (oancfq > 0).astype(int)            # Positive CFO
    
    # 3. Change in ROA
    roa_lag = df.groupby('gvkey')['niq'].shift(2) / df.groupby('gvkey')['atq'].shift(2).replace(0, np.nan)
    f3 = (roa > roa_lag).astype(int)        # Increasing ROA
    
    # 4. Accruals
    f4 = (oancfq / atq_lag > roa).astype(int) # CFO > ROA
    
    # 5. Change in Leverage (Long-term debt)
    lev = df['dlttq'] / atq_lag
    lev_lag = df.groupby('gvkey')['dlttq'].shift(1) / df.groupby('gvkey')['atq'].shift(2).replace(0, np.nan)
    f5 = (lev < lev_lag).astype(int)        # Decreasing Leverage
    
    # 6. Change in Liquidity (Current Ratio)
    curr = df['actq'] / df['lctq'].replace(0, np.nan)
    curr_lag = df.groupby('gvkey')['actq'].shift(1) / df.groupby('gvkey')['lctq'].shift(1).replace(0, np.nan)
    f6 = (curr > curr_lag).astype(int)      # Increasing Liquidity
    
    # 7. No New Equity (Issuance)
    csho_lag = df.groupby('gvkey')['cshoq'].shift(1)
    f7 = (df['cshoq'] <= csho_lag).astype(int)
    
    # 8. Change in Gross Margin
    margin = (df['saleq'] - df['cogsq']) / df['saleq'].replace(0, np.nan)
    margin_lag = (df.groupby('gvkey')['saleq'].shift(1) - df.groupby('gvkey')['cogsq'].shift(1)) / df.groupby('gvkey')['saleq'].shift(1).replace(0, np.nan)
    f8 = (margin > margin_lag).astype(int)  # Increasing Margin
    
    # 9. Change in Asset Turnover
    turn = df['saleq'] / atq_lag
    turn_lag = df.groupby('gvkey')['saleq'].shift(1) / df.groupby('gvkey')['atq'].shift(2).replace(0, np.nan)
    f9 = (turn > turn_lag).astype(int)      # Increasing Turnover
    
    return f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9

def calculate_beneish_m(df):
    """Calculate 8-factor Beneish M-Score for fraud/manipulation detection."""
    df = df.sort_values(['gvkey', 'datadate'])
    l = df.groupby('gvkey')
    
    # Ratios (Current / Lag)
    dsri = (df['rectq'] / df['saleq'].replace(0, np.nan)) / (l['rectq'].shift(1) / l['saleq'].shift(1).replace(0, np.nan))
    gmi = ( (l['saleq'].shift(1) - l['cogsq'].shift(1)) / l['saleq'].shift(1).replace(0, np.nan) ) / \
          ( (df['saleq'] - df['cogsq']) / df['saleq'].replace(0, np.nan) )
    aqi = ( 1 - (df['actq'] + df['ppegtq']) / df['atq'].replace(0, np.nan) ) / \
          ( 1 - (l['actq'].shift(1) + l['ppegtq'].shift(1)) / l['atq'].shift(1).replace(0, np.nan) )
    sgi = df['saleq'] / l['saleq'].shift(1).replace(0, np.nan)
    depi = ( l['dpq'].shift(1) / (l['ppegtq'].shift(1) + l['dpq'].shift(1)).replace(0, np.nan) ) / \
           ( df['dpq'] / (df['ppegtq'] + df['dpq']).replace(0, np.nan) )
    sgai = (df['xsgaq'] / df['saleq'].replace(0, np.nan)) / (l['xsgaq'].shift(1) / l['saleq'].shift(1).replace(0, np.nan))
    tata = (df['niq'] - df['oancfy']) / df['atq'].replace(0, np.nan) # Using YTD for simplicity here
    lvgi = ( (df['dlcq'] + df['dlttq']) / df['atq'].replace(0, np.nan) ) / \
           ( (l['dlcq'].shift(1) + l['dlttq'].shift(1)) / l['atq'].shift(1).replace(0, np.nan) )
    
    # Beneish M-Score Formula
    m_score = -4.84 + 0.92*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi + 0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi
    return m_score

# ==============================================================================
# MAIN PIPELINE
# ==============================================================================
def main(force_refresh=False):
    # Ensure directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    # 0. Cache Check
    universe_path = 'data/processed/df_etf_universe.parquet'
    scoring_path = f"data/processed/gamf_scoring_{START_DATE}_to_{END_DATE}.parquet"
    options_path = f"data/processed/options_chains_{START_DATE}_to_{END_DATE}.parquet"
    
    # Check for legacy file in root and move it
    if os.path.exists('df_etf_universe.parquet') and not os.path.exists(universe_path):
        print("[INFO] Moving legacy pricing data from root to data/processed/...")
        os.rename('df_etf_universe.parquet', universe_path)

    db = None
    
    # 1. ETF Universe Pricing
    if os.path.exists(universe_path) and not force_refresh:
        print(f"[INFO] Loading ETF Prices from cache: {universe_path}")
        df_etf_universe = pd.read_parquet(universe_path)
    else:
        db = connect_wrds() if not db else db
        df_etf_universe = fetch_etf_universe_data(db, ETF_UNIVERSE, START_DATE, END_DATE)
        
        # [NEW] Synthetic Interpolation for TLT/SHY (Pre-2002 Gap)
        # Bond ETFs launched in 2002. Backfill with flat return proxy for 1999-2002.
        unique_dates = df_etf_universe['date'].unique()
        start_ts = pd.to_datetime(START_DATE)
        for ticker in ['TLT', 'SHY']:
            if ticker in ETF_UNIVERSE:
                t_data = df_etf_universe[df_etf_universe['ticker'] == ticker]
                if t_data.empty or t_data['date'].min() > start_ts + pd.Timedelta(days=5):
                    print(f"  [INFO] Backfilling {ticker} with synthetic yields (Pre-2002)...")
                    min_existing = t_data['date'].min() if not t_data.empty else pd.to_datetime('2099-01-01')
                    missing_dates = [d for d in unique_dates if d < min_existing]
                    # Synthetic daily return: ~2.5% Annualized / 252 days
                    synthetic = pd.DataFrame({
                        'date': missing_dates,
                        'ticker': ticker,
                        'prc': 100.0,
                        'ret': 0.0001, 
                        'vol': 0, 'permno': 0, 'shrout': 0
                    })
                    df_etf_universe = pd.concat([df_etf_universe, synthetic], ignore_index=True)

        df_etf_universe.to_parquet(universe_path)
        print(f"[SUCCESS] Saved ETF Prices to {universe_path}")

    # 2. Fundamental Scoring (Altman Z, F, M)
    if os.path.exists(scoring_path) and not force_refresh:
        print(f"[INFO] Loading Fundamental Scores from cache: {scoring_path}")
    else:
        db = connect_wrds() if not db else db
        df_portnos = fetch_etf_portnos(db, ETF_UNIVERSE)
        rebalance_dates = pd.date_range(start=START_DATE, end=END_DATE, freq=REBALANCE_FREQ)
        df_holdings = fetch_etf_holdings(db, df_portnos, rebalance_dates)
        
        if not df_holdings.empty:
            ccm = fetch_ccm_links(db)
            holdings_linked = pd.merge(df_holdings, ccm, left_on='crsp_permno', right_on='permno')
            unique_gvkeys = holdings_linked['gvkey'].dropna().unique().tolist()
            df_fundamentals = fetch_quarterly_fundamentals(db, unique_gvkeys, START_DATE, END_DATE)
            
            if not df_fundamentals.empty:
                df_fundamentals['altman_z'] = calculate_altman_z(df_fundamentals)
                df_fundamentals['piotroski_f'] = calculate_piotroski_f(df_fundamentals)
                df_fundamentals['beneish_m'] = calculate_beneish_m(df_fundamentals)
                
                final_df = pd.merge_asof(
                    holdings_linked.sort_values('rebalance_date'),
                    df_fundamentals.sort_values('rdq'),
                    left_on='rebalance_date',
                    right_on='rdq',
                    by='gvkey',
                    direction='backward'
                )
                final_df.to_parquet(scoring_path)
                print(f"[SUCCESS] Saved Fundamental Scores to {scoring_path}")

    # 3. Options Data
    if os.path.exists(options_path) and not force_refresh:
        print(f"[INFO] Loading Options Chains from cache: {options_path}")
    else:
        db = connect_wrds() if not db else db
        df_options = fetch_options_data(db, ETF_UNIVERSE, START_DATE, END_DATE)
        if not df_options.empty:
            df_options.to_parquet(options_path)
            print(f"[SUCCESS] Saved Options Chains to {options_path}")
        else:
            print("[WARNING] No options data fetched (Check permissions). Synthetic simulation will be used by backtester.")

    if db:
        db.close()
    print("\n[COMPLETE] Data pipeline in synchronized state.")

if __name__ == "__main__":
    main()