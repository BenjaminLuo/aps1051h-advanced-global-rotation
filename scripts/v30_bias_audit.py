import pandas as pd
import numpy as np
from scripts.gamf_engine import backtest, HedgeMode

def bias_free_audit():
    print("[INFO] Initializing V30-ALGO-PURE Bias-Free Audit...")
    
    results = []
    regimes = [
        ("Dot-com Cycle", "1999-01-01", "2002-12-31"),
        ("Post-9/11 Recovery", "2003-01-01", "2007-12-31"),
        ("Global Financial Crisis", "2008-01-01", "2009-12-31"),
        ("Post-GFC Expansion", "2010-01-01", "2019-12-31"),
        ("COVID-19 Shock & Rally", "2020-01-01", "2021-12-31"),
        ("Modern Inflation Cycle", "2022-01-01", "2024-12-31")
    ]

    for mode in [HedgeMode.OPTIONS, HedgeMode.BOND_ROTATION]:
        print(f"  -> Auditing Mode: {mode.value.upper()} (Dynamic Signals Only)...")
        s_rets, b_rets, w, r = backtest(hedge_mode=mode)
        
        for name, start, end in regimes:
            sl_s = s_rets.loc[start:end]
            sl_b = b_rets.loc[start:end]
            if sl_s.empty: continue
            
            s_cagr = (1 + sl_s).prod()**(252/len(sl_s)) - 1
            b_cagr = (1 + sl_b).prod()**(252/len(sl_b)) - 1
            alpha = s_cagr - b_cagr
            vol = sl_s.std() * np.sqrt(252)
            mdd = (sl_s.add(1).cumprod() / sl_s.add(1).cumprod().cummax() - 1).min()
            
            results.append({
                "Strategy": mode.value.upper(),
                "Regime": name,
                "GAMF CAGR": f"{s_cagr:.1%}",
                "SPY CAGR": f"{b_cagr:.1%}",
                "Alpha": f"{alpha:.1%}",
                "Vol": f"{vol:.1%}",
                "Max DD": f"{mdd:.1%}"
            })
            
    df = pd.DataFrame(results)
    print("\n--- V30-ALGO-PURE BIAS-FREE AUDIT ---")
    print(df.to_string(index=False))
    df.to_csv("data/processed/v30_bias_audit.csv", index=False)

if __name__ == "__main__":
    bias_free_audit()
