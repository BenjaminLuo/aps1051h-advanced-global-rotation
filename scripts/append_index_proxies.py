import pandas as pd
import yfinance as yf
import os

UNIVERSE_FILE = "data/processed/df_etf_universe.parquet"

def append_proxies():
    print("[INFO] Appending QQQ and DIA to research universe...")
    
    if not os.path.exists(UNIVERSE_FILE):
        print("[ERROR] Universe file missing.")
        return

    df_existing = pd.read_parquet(UNIVERSE_FILE)
    df_existing['date'] = pd.to_datetime(df_existing['date'])
    
    # Fetch QQQ and DIA
    tickers = ['QQQ', 'DIA']
    proxy_data = []
    
    for t in tickers:
        print(f"  -> Fetching {t}...")
        df = yf.download(t, start="1999-01-01", end="2025-01-01")
        if df.empty: continue
        
        # [FIX] Handle yfinance MultiIndex and Missing 'Adj Close'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        # Rename columns to match CRSP format used in pipeline
        df_clean = pd.DataFrame()
        df_clean['date'] = df['Date']
        df_clean['ticker'] = t
        # Use 'Close' if 'Adj Close' is missing
        price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df_clean['prc'] = df[price_col]
        # Calculate daily return
        df_clean['ret'] = df[price_col].pct_change().fillna(0)
        df_clean['vol'] = df['Volume']
        
        proxy_data.append(df_clean)
        
    df_proxies = pd.concat(proxy_data)
    
    # Merge and Deduplicate
    df_final = pd.concat([df_existing, df_proxies])
    # Ensure date is consistent
    df_final['date'] = pd.to_datetime(df_final['date'])
    # Optional: Filter out any overlap if they existed partially
    df_final = df_final.drop_duplicates(subset=['date', 'ticker'], keep='last')
    
    df_final.sort_values(['ticker', 'date'], inplace=True)
    df_final.to_parquet(UNIVERSE_FILE)
    print(f"[SUCCESS] Appended {tickers} to {UNIVERSE_FILE}")
    print(f"Total Rows: {len(df_final)}")
    print(f"Tickers in Universe: {df_final['ticker'].unique()}")

if __name__ == "__main__":
    append_proxies()
