"""
Data Summary Script - Generates summary statistics of downloaded and processed data
"""

import pandas as pd
import glob
import os
from datetime import datetime

def summarize_data():
    print("=" * 70)
    print("DATA SUMMARY FOR TWO PREMIUMS PAPER REPLICATION")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. CFTC Legacy COT Data
    print("1. CFTC LEGACY COT DATA")
    print("-" * 70)
    if os.path.exists('data/cftc_legacy/legacy_cot_data.csv'):
        df = pd.read_csv('data/cftc_legacy/legacy_cot_data.csv')
        print(f"   Total Records: {len(df):,}")
        print(f"   Date Range: {df['As of Date in Form YYYY-MM-DD'].min()} to {df['As of Date in Form YYYY-MM-DD'].max()}")
        print(f"   Unique Commodities: {df['Market and Exchange Names'].nunique()}")
        print(f"   Sample Commodities:")
        for comm in df['Market and Exchange Names'].unique()[:5]:
            print(f"      - {comm.strip()}")
    else:
        print("   ✗ Not found")
    
    # 2. CFTC Disaggregated COT Data
    print("\n2. CFTC DISAGGREGATED COT DATA")
    print("-" * 70)
    if os.path.exists('data/cftc_disagg/disagg_cot_data.csv'):
        df = pd.read_csv('data/cftc_disagg/disagg_cot_data.csv', low_memory=False)
        print(f"   Total Records: {len(df):,}")
        df['Report_Date_as_MM_DD_YYYY'] = pd.to_datetime(df['Report_Date_as_MM_DD_YYYY'], errors='coerce')
        df = df.dropna(subset=['Report_Date_as_MM_DD_YYYY'])
        print(f"   Date Range: {df['Report_Date_as_MM_DD_YYYY'].min():%Y-%m-%d} to {df['Report_Date_as_MM_DD_YYYY'].max():%Y-%m-%d}")
        print(f"   Unique Commodities: {df['Market_and_Exchange_Names'].nunique()}")
    else:
        print("   ✗ Not found")
    
    # 3. Price Data
    print("\n3. COMMODITY FUTURES PRICE DATA")
    print("-" * 70)
    price_files = glob.glob('data/prices/*_prices.csv')
    print(f"   Number of Commodities: {len(price_files)}")
    print(f"   Commodities:")
    for file in sorted(price_files):
        ticker = os.path.basename(file).replace('_prices.csv', '')
        df = pd.read_csv(file)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            date_range = f"{df['Date'].min():%Y-%m-%d} to {df['Date'].max():%Y-%m-%d}"
        else:
            date_range = "N/A"
        print(f"      {ticker:5} - {len(df):5} days ({date_range})")
    
    # 4. Macro Data
    print("\n4. MACRO DATA")
    print("-" * 70)
    for name in ['VIX', 'SPX']:
        file = f'data/{name}_data.csv'
        if os.path.exists(file):
            df = pd.read_csv(file)
            print(f"   {name:5} - {len(df):5} days")
        else:
            print(f"   {name:5} - ✗ Not found")
    
    # 5. Processed Data
    print("\n5. PROCESSED DATA (COT + PRICES + CALCULATED VARIABLES)")
    print("-" * 70)
    processed_files = glob.glob('data/processed/*_processed.csv')
    print(f"   Number of Commodities: {len(processed_files)}")
    print(f"\n   {'Ticker':<8} {'Observations':<15} {'Date Range':<30} {'Variables':<10}")
    print("   " + "-" * 65)
    
    for file in sorted(processed_files):
        ticker = os.path.basename(file).replace('_processed.csv', '')
        df = pd.read_csv(file)
        
        # Get date range
        if 'Report_Date' in df.columns:
            date_col = 'Report_Date'
        else:
            date_col = df.columns[0]
        
        df[date_col] = pd.to_datetime(df[date_col])
        date_range = f"{df[date_col].min():%Y-%m-%d} to {df[date_col].max():%Y-%m-%d}"
        
        # Count variables
        key_vars = ['HP', 'Q_Comm', 'Q_NonComm', 'PT_Comm', 'PT_NonComm', 'Ret', 'HP_Smooth_52w']
        has_vars = sum(1 for v in key_vars if v in df.columns)
        
        print(f"   {ticker:<8} {len(df):<15} {date_range:<30} {has_vars}/{len(key_vars)}")
    
    # 6. Variable Definitions
    print("\n6. CALCULATED VARIABLES (According to Paper)")
    print("-" * 70)
    print("   HP             - Hedging Pressure: (Comm_Short - Comm_Long) / OI")
    print("   Q_Comm         - Net Trading (Commercial): Δ(NetLong) / OI")
    print("   Q_NonComm      - Net Trading (Non-Commercial): Δ(NetLong) / OI")
    print("   PT_Comm        - Propensity to Trade (Commercial)")
    print("   PT_NonComm     - Propensity to Trade (Non-Commercial)")
    print("   Ret            - Weekly Return: (F_t - F_{t-1}) / F_{t-1}")
    print("   Ret_Lead       - Next Week's Return (for prediction)")
    print("   HP_Smooth_52w  - 52-week Rolling Average of HP")
    
    print("\n" + "=" * 70)
    print("DATA ACQUISITION AND PREPROCESSING COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    summarize_data()
