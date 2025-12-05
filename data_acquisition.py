"""
Data Acquisition Script for "A Tale of Two Premiums" Paper Replication
Downloads CFTC position data, commodity futures prices, and macro data
"""

import pandas as pd
import requests
import zipfile
import io
import os
from datetime import datetime, timedelta
import yfinance as yf
import time

# Create data directory
os.makedirs('data', exist_ok=True)
os.makedirs('data/cftc_legacy', exist_ok=True)
os.makedirs('data/cftc_disagg', exist_ok=True)
os.makedirs('data/prices', exist_ok=True)

def download_cftc_legacy(start_year=1994, end_year=2017):
    """
    Download CFTC Legacy (COT) Reports - Futures Only
    """
    print("=" * 60)
    print("Downloading CFTC Legacy COT Data...")
    print("=" * 60)
    
    base_url = "https://www.cftc.gov/files/dea/history/"
    all_data = []
    
    for year in range(start_year, end_year + 1):
        try:
            # Legacy format: deacotYYYY.zip containing annual.txt or c_year.txt
            file_name = f"deacot{year}.zip"
            url = f"{base_url}{file_name}"
            
            print(f"Downloading Legacy COT {year}... ", end='')
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(response.content))
                
                # Try different file name patterns
                txt_files = [f for f in z.namelist() if f.endswith('.txt')]
                
                for txt_file in txt_files:
                    if 'annual' in txt_file.lower() or 'c_year' in txt_file.lower() or f'{year}' in txt_file:
                        with z.open(txt_file) as f:
                            df = pd.read_csv(f, low_memory=False)
                            
                            # Filter for Futures Only
                            if 'Market_and_Exchange_Names' in df.columns:
                                df = df[df['Market_and_Exchange_Names'].str.contains('FUTURES ONLY', case=False, na=False)]
                            
                            all_data.append(df)
                            print(f"✓ ({len(df)} records)")
                            break
                else:
                    # If no annual file found, try the first txt file
                    if txt_files:
                        with z.open(txt_files[0]) as f:
                            df = pd.read_csv(f, low_memory=False)
                            if 'Market_and_Exchange_Names' in df.columns:
                                df = df[df['Market_and_Exchange_Names'].str.contains('FUTURES ONLY', case=False, na=False)]
                            all_data.append(df)
                            print(f"✓ ({len(df)} records)")
            else:
                print(f"✗ (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"✗ (Error: {str(e)[:50]})")
            continue
        
        time.sleep(0.5)  # Be polite to the server
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        output_file = 'data/cftc_legacy/legacy_cot_data.csv'
        combined.to_csv(output_file, index=False)
        print(f"\n✓ Legacy COT data saved: {len(combined)} records -> {output_file}")
        return combined
    else:
        print("\n✗ No Legacy COT data downloaded")
        return None

def download_cftc_disaggregated(start_year=2006, end_year=2017):
    """
    Download CFTC Disaggregated (DCOT) Reports - Futures Only
    Note: Disaggregated data only available from 2006 onwards
    """
    print("\n" + "=" * 60)
    print("Downloading CFTC Disaggregated COT Data...")
    print("=" * 60)
    
    base_url = "https://www.cftc.gov/files/dea/history/"
    all_data = []
    
    for year in range(start_year, end_year + 1):
        try:
            # Disaggregated format: f_year.zip
            file_name = f"fut_disagg_txt_{year}.zip"
            url = f"{base_url}{file_name}"
            
            print(f"Downloading Disaggregated COT {year}... ", end='')
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(response.content))
                
                # Find txt files
                txt_files = [f for f in z.namelist() if f.endswith('.txt')]
                
                for txt_file in txt_files:
                    with z.open(txt_file) as f:
                        df = pd.read_csv(f, low_memory=False)
                        all_data.append(df)
                        print(f"✓ ({len(df)} records)")
                        break
            else:
                print(f"✗ (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"✗ (Error: {str(e)[:50]})")
            continue
        
        time.sleep(0.5)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        output_file = 'data/cftc_disagg/disagg_cot_data.csv'
        combined.to_csv(output_file, index=False)
        print(f"\n✓ Disaggregated COT data saved: {len(combined)} records -> {output_file}")
        return combined
    else:
        print("\n✗ No Disaggregated COT data downloaded")
        return None

def download_commodity_prices(start_date='1994-01-01', end_date='2017-12-31'):
    """
    Download commodity futures prices from Yahoo Finance
    """
    print("\n" + "=" * 60)
    print("Downloading Commodity Futures Prices...")
    print("=" * 60)
    
    # Ticker mapping for Yahoo Finance
    tickers = {
        # Energy
        'CL': 'CL=F',  # Crude Oil
        'HO': 'HO=F',  # Heating Oil
        'NG': 'NG=F',  # Natural Gas

        # Metals
        'PL': 'PL=F',  # Platinum
        'PA': 'PA=F',  # Palladium
        'SI': 'SI=F',  # Silver
        'HG': 'HG=F',  # Copper
        'GC': 'GC=F',  # Gold

        # Grains
        'ZW': 'ZW=F',  # Wheat (Chicago)
        'KE': 'KE=F',  # KC Wheat (Kansas City)
        'ZC': 'ZC=F',  # Corn
        'ZO': 'ZO=F',  # Oats
        'ZS': 'ZS=F',  # Soybean
        'ZL': 'ZL=F',  # Soybean Oil
        'ZM': 'ZM=F',  # Soybean Meal
        'RR': 'ZR=F',  # Rough Rice (use ZR=F instead of RR=F)

        # Softs
        'CT': 'CT=F',  # Cotton
        'OJ': 'OJ=F',  # Orange Juice
        'LB': 'LBS=F',  # Lumber (use LBS=F instead of LB=F)
        'CC': 'CC=F',  # Cocoa
        'SB': 'SB=F',  # Sugar
        'KC': 'KC=F',  # Coffee

        # Livestock
        'HE': 'HE=F',  # Lean Hogs
        'LE': 'LE=F',  # Live Cattle
        'GF': 'GF=F',  # Feeder Cattle
    }
    
    price_data = {}
    
    for name, ticker in tickers.items():
        try:
            print(f"Downloading {name:12} ({ticker:8})... ", end='')
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
            
            if not df.empty:
                # Reset index to have Date as column
                df = df.reset_index()
                # Select only needed columns
                if 'Date' in df.columns and 'Close' in df.columns:
                    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                    df['Ticker'] = name
                    price_data[name] = df
                    print(f"✓ ({len(df)} days)")
                else:
                    print("✗ (Missing columns)")
            else:
                print("✗ (No data)")
                
        except Exception as e:
            print(f"✗ (Error: {str(e)[:40]})")
            continue
        
        time.sleep(0.3)
    
    # Save individual commodity files
    for name, df in price_data.items():
        df.to_csv(f'data/prices/{name}_prices.csv', index=False)
    
    print(f"\n✓ Downloaded prices for {len(price_data)} commodities")
    return price_data

def download_macro_data(start_date='1994-01-01', end_date='2017-12-31'):
    """
    Download macro data: VIX and S&P 500
    """
    print("\n" + "=" * 60)
    print("Downloading Macro Data...")
    print("=" * 60)
    
    macro_tickers = {
        'VIX': '^VIX',
        'SPX': '^GSPC'
    }
    
    macro_data = {}
    
    for name, ticker in macro_tickers.items():
        try:
            print(f"Downloading {name}... ", end='')
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if not df.empty:
                macro_data[name] = df
                df.to_csv(f'data/{name}_data.csv')
                print(f"✓ ({len(df)} days)")
            else:
                print("✗ (No data)")
                
        except Exception as e:
            print(f"✗ (Error: {str(e)[:40]})")
            continue
    
    print(f"\n✓ Downloaded {len(macro_data)} macro datasets")
    return macro_data

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DATA ACQUISITION FOR TWO PREMIUMS PAPER REPLICATION")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Download CFTC Legacy COT data
    legacy_data = download_cftc_legacy(start_year=1994, end_year=2017)
    
    # 2. Download CFTC Disaggregated COT data (from 2006)
    disagg_data = download_cftc_disaggregated(start_year=2006, end_year=2017)
    
    # 3. Download commodity futures prices
    price_data = download_commodity_prices(start_date='1994-01-01', end_date='2017-12-31')
    
    # 4. Download macro data
    macro_data = download_macro_data(start_date='1994-01-01', end_date='2017-12-31')
    
    print("\n" + "=" * 60)
    print("DATA ACQUISITION COMPLETED")
    print("=" * 60)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nData saved in ./data/ directory")
    print("Next step: Run data_preprocessing.py")
