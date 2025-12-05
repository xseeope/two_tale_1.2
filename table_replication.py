"""
Table Replication for "A Tale of Two Premiums" Paper
Generates all tables according to the paper's methodology
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
import statsmodels.api as sm
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Create output directory
os.makedirs('output/tables', exist_ok=True)

def load_all_processed_data():
    """Load all processed commodity data into a single DataFrame"""
    print("=" * 70)
    print("LOADING PROCESSED DATA")
    print("=" * 70)
    
    all_data = []
    files = glob.glob('data/processed/*_processed.csv')
    
    for file in files:
        ticker = os.path.basename(file).replace('_processed.csv', '')
        df = pd.read_csv(file)
        
        # Handle different column name formats
        if 'Unnamed: 0' in df.columns:
            df = df.rename(columns={'Unnamed: 0': 'Report_Date'})
        elif 'Report_Date' not in df.columns:
            # If neither, try to reset index
            df = df.reset_index()
            if 'index' in df.columns:
                df = df.rename(columns={'index': 'Report_Date'})
        
        df['Ticker'] = ticker
        df['Report_Date'] = pd.to_datetime(df['Report_Date'])
        all_data.append(df)
        print(f"✓ Loaded {ticker:5} - {len(df)} observations")
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\n✓ Total: {len(combined):,} observations across {len(files)} commodities")
    
    return combined

def calculate_additional_variables(df):
    """Calculate additional variables needed for analysis"""
    print("\n" + "=" * 70)
    print("CALCULATING ADDITIONAL VARIABLES")
    print("=" * 70)
    
    # |Q| - Absolute value of net trading
    df['abs_Q_Comm'] = df['Q_Comm'].abs()
    df['abs_Q_NonComm'] = df['Q_NonComm'].abs()
    print("✓ Calculated |Q| variables")
    
    # Calculate position changes for Table II
    for ticker in df['Ticker'].unique():
        mask = df['Ticker'] == ticker
        # Delta positions (changes)
        df.loc[mask, 'Delta_NetLong_Comm'] = df.loc[mask, 'NetLong_Comm'].diff()
        df.loc[mask, 'Delta_NetLong_NonComm'] = df.loc[mask, 'NetLong_NonComm'].diff()
        # Calculate non-reportable positions
        df.loc[mask, 'NonReport_Long'] = df.loc[mask, 'Open_Interest_All'] - df.loc[mask, 'Comm_Positions_Long_All'] - df.loc[mask, 'NonComm_Positions_Long_All']
        df.loc[mask, 'NonReport_Short'] = df.loc[mask, 'Open_Interest_All'] - df.loc[mask, 'Comm_Positions_Short_All'] - df.loc[mask, 'NonComm_Positions_Short_All']
        df.loc[mask, 'NetLong_NonReport'] = df.loc[mask, 'NonReport_Long'] - df.loc[mask, 'NonReport_Short']
        df.loc[mask, 'Delta_NetLong_NonReport'] = df.loc[mask, 'NetLong_NonReport'].diff()
        # Lag Q for Table II
        df.loc[mask, 'Q_Comm_lag1'] = df.loc[mask, 'Q_Comm'].shift(1)
        df.loc[mask, 'Q_NonComm_lag1'] = df.loc[mask, 'Q_NonComm'].shift(1)
    print("✓ Calculated position changes")
    
    # Return lags for momentum analysis
    for ticker in df['Ticker'].unique():
        mask = df['Ticker'] == ticker
        df.loc[mask, 'Ret_lag1'] = df.loc[mask, 'Ret'].shift(1)
        df.loc[mask, 'Ret_lag2'] = df.loc[mask, 'Ret'].shift(2)
        df.loc[mask, 'Ret_Lead2'] = df.loc[mask, 'Ret'].shift(-2)
    print("✓ Calculated lagged returns")
    
    # Historical volatility (52-week rolling)
    for ticker in df['Ticker'].unique():
        mask = df['Ticker'] == ticker
        df.loc[mask, 'HistVol'] = df.loc[mask, 'Ret'].rolling(52, min_periods=26).std()
    print("✓ Calculated historical volatility")
    
    # Calculate Basis and S*v_t for Table III
    for ticker in df['Ticker'].unique():
        mask = df['Ticker'] == ticker
        # Basis: simplified as return autocorrelation proxy (since we don't have multiple contract maturities)
        df.loc[mask, 'Basis'] = df.loc[mask, 'Ret'].rolling(4, min_periods=2).mean()
        # S: sign variable for noncommercial net position
        df.loc[mask, 'S'] = np.where(df.loc[mask, 'NetLong_NonComm'] > 0, 1, -1)
        # v_t: volatility estimate (use historical volatility)
        df.loc[mask, 'v_t'] = df.loc[mask, 'HistVol']
        df.loc[mask, 'S_v'] = df.loc[mask, 'S'] * df.loc[mask, 'v_t']
    print("✓ Calculated Basis and S*v_t")
    
    # Commodity-specific return (remove market effect)
    # Load S&P 500 for market returns
    if os.path.exists('data/SPX_data.csv'):
        try:
            spx = pd.read_csv('data/SPX_data.csv', index_col=0, parse_dates=True)
            spx_weekly = spx['Close'].resample('W-TUE').last()
            spx_ret = spx_weekly.pct_change()
            
            # Merge with commodity data
            df['SPX_Ret'] = df['Report_Date'].map(spx_ret.to_dict())
            print("✓ Added S&P 500 returns")
        except Exception as e:
            print(f"⚠ Could not load SPX data: {str(e)[:50]}")
    
    # Load VIX
    if os.path.exists('data/VIX_data.csv'):
        try:
            vix = pd.read_csv('data/VIX_data.csv', index_col=0, parse_dates=True)
            vix_weekly = vix['Close'].resample('W-TUE').last()
            
            # Merge with commodity data
            df['VIX'] = df['Report_Date'].map(vix_weekly.to_dict())
            print("✓ Added VIX data")
        except Exception as e:
            print(f"⚠ Could not load VIX data: {str(e)[:50]}")
    
    return df

# ============================================================================
# TABLE I: Summary Statistics
# ============================================================================
def table_I_summary_statistics(df):
    """Generate Table I: Summary Statistics
    Panel A: Excess Return (Mean, Std), HP (Mean, Std, Prob(HP>0))
    Panel B: |Q| and PT for Commercials and NonCommercials
    """
    print("\n" + "=" * 70)
    print("TABLE I: SUMMARY STATISTICS")
    print("=" * 70)
    
    results = []
    
    for ticker in sorted(df['Ticker'].unique()):
        ticker_data = df[df['Ticker'] == ticker].copy()
        
        # Panel A: Excess Returns and HP (5 columns as specified)
        ret_mean = ticker_data['Ret'].mean() * 52  # Annualize: weekly return * 52 weeks
        ret_std = ticker_data['Ret'].std() * np.sqrt(52)  # Annualized std
        hp_mean = ticker_data['HP'].mean()
        hp_std = ticker_data['HP'].std()
        prob_hp_pos = (ticker_data['HP'] > 0).mean()
        
        # Panel B: |Q| and PT (4 columns as specified)
        abs_q_comm = ticker_data['abs_Q_Comm'].mean()
        abs_q_noncomm = ticker_data['abs_Q_NonComm'].mean()
        pt_comm = ticker_data['PT_Comm'].mean()
        pt_noncomm = ticker_data['PT_NonComm'].mean()
        
        results.append({
            'Ticker': ticker,
            'Excess_Ret_Mean': ret_mean,
            'Excess_Ret_Std': ret_std,
            'HP_Mean': hp_mean,
            'HP_Std': hp_std,
            'Prob_HP_Pos': prob_hp_pos,
            '|Q_Comm|_Mean': abs_q_comm,
            '|Q_NonComm|_Mean': abs_q_noncomm,
            'PT_Comm_Mean': pt_comm,
            'PT_NonComm_Mean': pt_noncomm
        })
    
    table = pd.DataFrame(results)
    
    # Add average row
    avg_row = {
        'Ticker': 'AVERAGE',
        'Excess_Ret_Mean': table['Excess_Ret_Mean'].mean(),
        'Excess_Ret_Std': table['Excess_Ret_Std'].mean(),
        'HP_Mean': table['HP_Mean'].mean(),
        'HP_Std': table['HP_Std'].mean(),
        'Prob_HP_Pos': table['Prob_HP_Pos'].mean(),
        '|Q_Comm|_Mean': table['|Q_Comm|_Mean'].mean(),
        '|Q_NonComm|_Mean': table['|Q_NonComm|_Mean'].mean(),
        'PT_Comm_Mean': table['PT_Comm_Mean'].mean(),
        'PT_NonComm_Mean': table['PT_NonComm_Mean'].mean()
    }
    table = pd.concat([table, pd.DataFrame([avg_row])], ignore_index=True)
    
    # Save
    table.to_csv('output/tables/table_I_summary_statistics.csv', index=False)
    print("\n✓ Table I saved to output/tables/table_I_summary_statistics.csv")
    
    # Display
    print("\nPanel A: Excess Returns and Hedging Pressure (5 columns)")
    print(table[['Ticker', 'Excess_Ret_Mean', 'Excess_Ret_Std', 'HP_Mean', 'HP_Std', 'Prob_HP_Pos']].to_string(index=False))
    
    print("\nPanel B: Trading Activity (4 columns)")
    print(table[['Ticker', '|Q_Comm|_Mean', '|Q_NonComm|_Mean', 'PT_Comm_Mean', 'PT_NonComm_Mean']].tail(10).to_string(index=False))
    
    return table

# ============================================================================
# Fama-MacBeth Regression Function
# ============================================================================
def fama_macbeth_regression(df, dependent_var, independent_vars, date_col='Report_Date'):
    """
    Perform Fama-MacBeth cross-sectional regression
    
    Returns: DataFrame with coefficients, t-stats, and p-values
    """
    # Prepare data
    df_clean = df[[date_col, 'Ticker', dependent_var] + independent_vars].dropna()
    
    # Get unique dates
    dates = sorted(df_clean[date_col].unique())
    
    coeffs_list = []
    
    for date in dates:
        # Cross-sectional slice
        slice_df = df_clean[df_clean[date_col] == date]
        
        # Need at least 10 commodities
        if len(slice_df) < 10:
            continue
        
        y = slice_df[dependent_var]
        X = slice_df[independent_vars]
        X = sm.add_constant(X)
        
        try:
            model = sm.OLS(y, X).fit()
            coeffs_list.append(model.params)
        except:
            continue
    
    # Convert to DataFrame
    coeffs_df = pd.DataFrame(coeffs_list)
    
    # Calculate means and t-statistics
    results = pd.DataFrame({
        'Variable': coeffs_df.columns,
        'Coefficient': coeffs_df.mean(),
        'Std_Error': coeffs_df.std() / np.sqrt(len(coeffs_df)),
        't_stat': coeffs_df.mean() / (coeffs_df.std() / np.sqrt(len(coeffs_df))),
        'N_months': len(coeffs_df)
    })
    
    results['p_value'] = 2 * (1 - stats.t.cdf(np.abs(results['t_stat']), len(coeffs_df) - 1))
    
    return results

# ============================================================================
# TABLE II: Weekly Position Changes and Returns
# ============================================================================
def table_II_position_changes_returns(df):
    """Generate Table II: Weekly Position Changes and Returns
    Cross-sectional regressions with position changes as dependent variable
    - Regression 1-2: Commercial traders
    - Regression 3-4: Non-commercial traders
    - Regression 5-6: Non-reportable traders
    """
    print("\n" + "=" * 70)
    print("TABLE II: WEEKLY POSITION CHANGES AND RETURNS")
    print("=" * 70)
    
    results = {}
    
    # Regression 1: Q_Comm on Ret (contemporaneous)
    print("\nRegression 1: Q_Commercial ~ Ret_t")
    res1 = fama_macbeth_regression(df, 'Q_Comm', ['Ret'])
    print(res1.to_string(index=False))
    results['Reg1_Comm_Ret'] = res1
    
    # Regression 2: Q_Comm on Ret_lag1 + Q_lag1
    print("\nRegression 2: Q_Commercial ~ Ret_{t-1} + Q_{t-1}")
    res2 = fama_macbeth_regression(df, 'Q_Comm', ['Ret_lag1', 'Q_Comm_lag1'])
    print(res2.to_string(index=False))
    results['Reg2_Comm_Lag'] = res2
    
    # Regression 3: Q_NonComm on Ret (contemporaneous)
    print("\nRegression 3: Q_NonCommercial ~ Ret_t")
    res3 = fama_macbeth_regression(df, 'Q_NonComm', ['Ret'])
    print(res3.to_string(index=False))
    results['Reg3_NonComm_Ret'] = res3
    
    # Regression 4: Q_NonComm on Ret_lag1 + Q_lag1
    print("\nRegression 4: Q_NonCommercial ~ Ret_{t-1} + Q_{t-1}")
    res4 = fama_macbeth_regression(df, 'Q_NonComm', ['Ret_lag1', 'Q_NonComm_lag1'])
    print(res4.to_string(index=False))
    results['Reg4_NonComm_Lag'] = res4
    
    # Regression 5: Delta_NonReport on Ret (contemporaneous)
    print("\nRegression 5: Delta_NonReportable ~ Ret_t")
    res5 = fama_macbeth_regression(df, 'Delta_NetLong_NonReport', ['Ret'])
    print(res5.to_string(index=False))
    results['Reg5_NonReport_Ret'] = res5
    
    # Regression 6: Delta_NonReport on Ret_lag1 (simplified, no Q for non-reportable)
    print("\nRegression 6: Delta_NonReportable ~ Ret_{t-1}")
    res6 = fama_macbeth_regression(df, 'Delta_NetLong_NonReport', ['Ret_lag1'])
    print(res6.to_string(index=False))
    results['Reg6_NonReport_Lag'] = res6
    
    # Save
    with pd.ExcelWriter('output/tables/table_II_position_changes.xlsx') as writer:
        for name, res in results.items():
            res.to_excel(writer, sheet_name=name, index=False)
    
    print("\n✓ Table II saved to output/tables/table_II_position_changes.xlsx")
    
    return results

# ============================================================================
# TABLE III: Return Predictability
# ============================================================================
def table_III_return_predictability(df):
    """Generate Table III: Return Predictability (Main Result)
    Equation (5): R_{t+j} = b0 + b1*Q_t + b2*Basis_t + b3*S*v_t + b4*R_t + error
    For j=1,2 and for each trader type (Commercial, NonCommercial)
    """
    print("\n" + "=" * 70)
    print("TABLE III: RETURN PREDICTABILITY")
    print("=" * 70)
    
    results = {}
    
    # For j=1 (one week ahead)
    print("\n=== PREDICTIONS FOR R_{t+1} ===")
    
    # Model 1: Commercial Q only
    print("\nModel 1a: R_{t+1} ~ Q_Comm")
    res1a = fama_macbeth_regression(df, 'Ret_Lead', ['Q_Comm'])
    print(res1a.to_string(index=False))
    results['R_t1_Q_Comm'] = res1a
    
    # Model 2: Commercial Q with controls (Equation 5)
    print("\nModel 1b: R_{t+1} ~ Q_Comm + Basis + S*v + Ret")
    res1b = fama_macbeth_regression(df, 'Ret_Lead', ['Q_Comm', 'Basis', 'S_v', 'Ret'])
    print(res1b.to_string(index=False))
    results['R_t1_Q_Comm_Full'] = res1b
    
    # Model 3: NonCommercial Q only
    print("\nModel 2a: R_{t+1} ~ Q_NonComm")
    res2a = fama_macbeth_regression(df, 'Ret_Lead', ['Q_NonComm'])
    print(res2a.to_string(index=False))
    results['R_t1_Q_NonComm'] = res2a
    
    # Model 4: NonCommercial Q with controls (Equation 5)
    print("\nModel 2b: R_{t+1} ~ Q_NonComm + Basis + S*v + Ret")
    res2b = fama_macbeth_regression(df, 'Ret_Lead', ['Q_NonComm', 'Basis', 'S_v', 'Ret'])
    print(res2b.to_string(index=False))
    results['R_t1_Q_NonComm_Full'] = res2b
    
    # For j=2 (two weeks ahead)
    print("\n=== PREDICTIONS FOR R_{t+2} ===")
    
    # Model 5: Commercial Q with controls for R_{t+2}
    print("\nModel 3: R_{t+2} ~ Q_Comm + Basis + S*v + Ret")
    res3 = fama_macbeth_regression(df, 'Ret_Lead2', ['Q_Comm', 'Basis', 'S_v', 'Ret'])
    print(res3.to_string(index=False))
    results['R_t2_Q_Comm_Full'] = res3
    
    # Model 6: NonCommercial Q with controls for R_{t+2}
    print("\nModel 4: R_{t+2} ~ Q_NonComm + Basis + S*v + Ret")
    res4 = fama_macbeth_regression(df, 'Ret_Lead2', ['Q_NonComm', 'Basis', 'S_v', 'Ret'])
    print(res4.to_string(index=False))
    results['R_t2_Q_NonComm_Full'] = res4
    
    # Save
    with pd.ExcelWriter('output/tables/table_III_return_predictability.xlsx') as writer:
        for name, res in results.items():
            res.to_excel(writer, sheet_name=name, index=False)
    
    print("\n✓ Table III saved to output/tables/table_III_return_predictability.xlsx")
    
    return results

# ============================================================================
# TABLE V: Portfolio Sorts
# ============================================================================
def table_V_portfolio_sorts(df):
    """Generate Table V: Portfolio Sorts based on Q_Comm"""
    print("\n" + "=" * 70)
    print("TABLE V: PORTFOLIO SORTS")
    print("=" * 70)
    
    # Get unique dates
    dates = sorted(df['Report_Date'].unique())
    
    horizons = [1, 5, 10, 20, 40]  # weeks
    results_dict = {h: [] for h in horizons}
    
    for date_idx, date in enumerate(dates):
        # Get current cross-section
        current = df[df['Report_Date'] == date].copy()
        
        if len(current) < 10:
            continue
        
        # Sort into quintiles based on Q_Comm
        current['Quintile'] = pd.qcut(current['Q_Comm'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
        
        # For each horizon, calculate forward returns
        for horizon in horizons:
            if date_idx + horizon >= len(dates):
                continue
            
            future_date = dates[date_idx + horizon]
            
            # Get returns at future date
            future_rets = df[df['Report_Date'] == future_date][['Ticker', 'Ret']].copy()
            
            # Merge
            merged = current[['Ticker', 'Quintile']].merge(future_rets, on='Ticker', how='inner')
            
            if len(merged) < 5:
                continue
            
            # Calculate portfolio returns
            portfolio_rets = merged.groupby('Quintile')['Ret'].mean()
            
            results_dict[horizon].append(portfolio_rets)
    
    # Aggregate results
    table_data = []
    for horizon in horizons:
        if len(results_dict[horizon]) == 0:
            continue
        
        # Convert to DataFrame
        all_rets = pd.DataFrame(results_dict[horizon])
        
        # Calculate means and t-stats
        mean_rets = all_rets.mean() * 52  # Annualize
        t_stats = (all_rets.mean() / all_rets.std()) * np.sqrt(len(all_rets))
        
        # Long-Short (Q5 - Q1)
        if 5 in all_rets.columns and 1 in all_rets.columns:
            ls_rets = all_rets[5] - all_rets[1]
            ls_mean = ls_rets.mean() * 52
            ls_tstat = (ls_rets.mean() / ls_rets.std()) * np.sqrt(len(ls_rets))
        else:
            ls_mean = np.nan
            ls_tstat = np.nan
        
        row = {
            'Horizon_Weeks': horizon,
            'Q1_Return': mean_rets.get(1, np.nan),
            'Q2_Return': mean_rets.get(2, np.nan),
            'Q3_Return': mean_rets.get(3, np.nan),
            'Q4_Return': mean_rets.get(4, np.nan),
            'Q5_Return': mean_rets.get(5, np.nan),
            'LS_Return': ls_mean,
            'LS_tstat': ls_tstat
        }
        table_data.append(row)
    
    table = pd.DataFrame(table_data)
    table.to_csv('output/tables/table_V_portfolio_sorts.csv', index=False)
    
    print("\n✓ Table V saved")
    print(table.to_string(index=False))
    
    return table

# ============================================================================
# TABLE IV: DCOT Data Analysis
# ============================================================================
def table_IV_dcot_analysis(df):
    """Generate Table IV: DCOT Data Analysis - Empty function as specified"""
    print("\n" + "=" * 70)
    print("TABLE IV: DCOT DATA ANALYSIS (NOT IMPLEMENTED)")
    print("=" * 70)
    print("⚠ DCOT data analysis skipped as specified in prompt")
    return None

# ============================================================================
# TABLE VI: Smoothed Hedging Pressure
# ============================================================================
def table_VI_smoothed_hp(df):
    """Generate Table VI: Smoothed Hedging Pressure Analysis
    Three regressions for j=1,2:
    1) R_{t+j} = b0 + b1*HP + controls
    2) R_{t+j} = b0 + b1*HP_Smooth + controls
    3) R_{t+j} = b0 + b1*HP_Smooth + b2*Q + controls
    """
    print("\n" + "=" * 70)
    print("TABLE VI: SMOOTHED HEDGING PRESSURE")
    print("=" * 70)
    
    results = {}
    
    # For j=1 (one week ahead)
    print("\n=== PREDICTIONS FOR R_{t+1} ===")
    
    # Regression 1: HP (not smoothed)
    print("\nRegression 1a: R_{t+1} ~ HP + Basis + S*v + Ret")
    res1a = fama_macbeth_regression(df, 'Ret_Lead', ['HP', 'Basis', 'S_v', 'Ret'])
    print(res1a.to_string(index=False))
    results['R_t1_HP'] = res1a
    
    # Regression 2: HP_Smooth
    print("\nRegression 2a: R_{t+1} ~ HP_Smooth + Basis + S*v + Ret")
    res2a = fama_macbeth_regression(df, 'Ret_Lead', ['HP_Smooth_52w', 'Basis', 'S_v', 'Ret'])
    print(res2a.to_string(index=False))
    results['R_t1_HP_Smooth'] = res2a
    
    # Regression 3: HP_Smooth + Q
    print("\nRegression 3a: R_{t+1} ~ HP_Smooth + Q_Comm + Basis + S*v + Ret")
    res3a = fama_macbeth_regression(df, 'Ret_Lead', ['HP_Smooth_52w', 'Q_Comm', 'Basis', 'S_v', 'Ret'])
    print(res3a.to_string(index=False))
    results['R_t1_HP_Smooth_Q'] = res3a
    
    # For j=2 (two weeks ahead)
    print("\n=== PREDICTIONS FOR R_{t+2} ===")
    
    # Regression 1: HP (not smoothed)
    print("\nRegression 1b: R_{t+2} ~ HP + Basis + S*v + Ret")
    res1b = fama_macbeth_regression(df, 'Ret_Lead2', ['HP', 'Basis', 'S_v', 'Ret'])
    print(res1b.to_string(index=False))
    results['R_t2_HP'] = res1b
    
    # Regression 2: HP_Smooth
    print("\nRegression 2b: R_{t+2} ~ HP_Smooth + Basis + S*v + Ret")
    res2b = fama_macbeth_regression(df, 'Ret_Lead2', ['HP_Smooth_52w', 'Basis', 'S_v', 'Ret'])
    print(res2b.to_string(index=False))
    results['R_t2_HP_Smooth'] = res2b
    
    # Regression 3: HP_Smooth + Q
    print("\nRegression 3b: R_{t+2} ~ HP_Smooth + Q_Comm + Basis + S*v + Ret")
    res3b = fama_macbeth_regression(df, 'Ret_Lead2', ['HP_Smooth_52w', 'Q_Comm', 'Basis', 'S_v', 'Ret'])
    print(res3b.to_string(index=False))
    results['R_t2_HP_Smooth_Q'] = res3b
    
    # Save
    with pd.ExcelWriter('output/tables/table_VI_smoothed_hp.xlsx') as writer:
        for name, res in results.items():
            res.to_excel(writer, sheet_name=name, index=False)
    
    print("\n✓ Table VI saved")
    
    return results

# ============================================================================
# TABLE VII: Hedging Pressure (DCOT)
# ============================================================================
def table_VII_hp_dcot(df):
    """Generate Table VII: Hedging Pressure with DCOT - Empty function as specified"""
    print("\n" + "=" * 70)
    print("TABLE VII: HEDGING PRESSURE (DCOT) (NOT IMPLEMENTED)")
    print("=" * 70)
    print("⚠ DCOT analysis skipped as specified in prompt")
    return None

# ============================================================================
# TABLE VIII: Double-Sorted Portfolios
# ============================================================================
def table_VIII_double_sorts(df):
    """Generate Table VIII: Double-Sorted Portfolios
    Sort by HP_Smooth first (High/Low), then by Q_Comm within each HP group
    Create 2x2 matrix showing returns for all combinations
    """
    print("\n" + "=" * 70)
    print("TABLE VIII: DOUBLE-SORTED PORTFOLIOS")
    print("=" * 70)
    
    # Get unique dates
    dates = sorted(df['Report_Date'].unique())
    
    portfolio_returns = {
        'LowHP_LowQ': [],
        'LowHP_HighQ': [],
        'HighHP_LowQ': [],
        'HighHP_HighQ': []
    }
    
    for date_idx, date in enumerate(dates):
        if date_idx + 1 >= len(dates):
            continue
            
        # Get current cross-section
        current = df[df['Report_Date'] == date].copy()
        
        if len(current) < 10:
            continue
        
        # First sort: HP_Smooth into 2 groups
        hp_median = current['HP_Smooth_52w'].median()
        current['HP_Group'] = np.where(current['HP_Smooth_52w'] > hp_median, 'High', 'Low')
        
        # Second sort: Q_Comm within each HP group
        for hp_group in ['Low', 'High']:
            group_data = current[current['HP_Group'] == hp_group].copy()
            if len(group_data) < 2:
                continue
            q_median = group_data['Q_Comm'].median()
            current.loc[(current['HP_Group'] == hp_group) & (current['Q_Comm'] <= q_median), 'Portfolio'] = f'{hp_group}HP_LowQ'
            current.loc[(current['HP_Group'] == hp_group) & (current['Q_Comm'] > q_median), 'Portfolio'] = f'{hp_group}HP_HighQ'
        
        # Get next week's returns
        future_date = dates[date_idx + 1]
        future_rets = df[df['Report_Date'] == future_date][['Ticker', 'Ret']].copy()
        
        # Merge
        merged = current[['Ticker', 'Portfolio']].merge(future_rets, on='Ticker', how='inner')
        
        # Calculate portfolio returns
        for portfolio_name in portfolio_returns.keys():
            portfolio_data = merged[merged['Portfolio'] == portfolio_name]
            if len(portfolio_data) > 0:
                portfolio_returns[portfolio_name].append(portfolio_data['Ret'].mean())
    
    # Calculate statistics
    results = []
    for portfolio_name, returns in portfolio_returns.items():
        if len(returns) > 0:
            returns_array = np.array(returns)
            mean_ret = returns_array.mean() * 52  # Annualize
            std_ret = returns_array.std() * np.sqrt(52)
            t_stat = (returns_array.mean() / returns_array.std()) * np.sqrt(len(returns_array))
            sharpe = mean_ret / std_ret if std_ret > 0 else np.nan
            
            results.append({
                'Portfolio': portfolio_name,
                'Mean_Return': mean_ret,
                'Std_Return': std_ret,
                't_stat': t_stat,
                'Sharpe': sharpe,
                'N_obs': len(returns)
            })
    
    table = pd.DataFrame(results)
    table.to_csv('output/tables/table_VIII_double_sorts.csv', index=False)
    
    print("\n✓ Table VIII saved")
    print(table.to_string(index=False))
    
    # Calculate Long-Short strategies
    print("\n=== Long-Short Strategies ===")
    if len(portfolio_returns['LowHP_HighQ']) > 0 and len(portfolio_returns['LowHP_LowQ']) > 0:
        min_len = min(len(portfolio_returns['LowHP_HighQ']), len(portfolio_returns['LowHP_LowQ']))
        ls_low_hp = np.array(portfolio_returns['LowHP_HighQ'][:min_len]) - np.array(portfolio_returns['LowHP_LowQ'][:min_len])
        print(f"Low HP: High Q - Low Q = {ls_low_hp.mean()*52:.4f} (t={ls_low_hp.mean()/(ls_low_hp.std()/np.sqrt(len(ls_low_hp))):.2f})")
    
    if len(portfolio_returns['HighHP_HighQ']) > 0 and len(portfolio_returns['HighHP_LowQ']) > 0:
        min_len = min(len(portfolio_returns['HighHP_HighQ']), len(portfolio_returns['HighHP_LowQ']))
        ls_high_hp = np.array(portfolio_returns['HighHP_HighQ'][:min_len]) - np.array(portfolio_returns['HighHP_LowQ'][:min_len])
        print(f"High HP: High Q - Low Q = {ls_high_hp.mean()*52:.4f} (t={ls_high_hp.mean()/(ls_high_hp.std()/np.sqrt(len(ls_high_hp))):.2f})")
    
    return table

# ============================================================================
# Main Execution
# ============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TABLE REPLICATION FOR 'A TALE OF TWO PREMIUMS'")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load data
    df = load_all_processed_data()
    
    # Calculate additional variables
    df = calculate_additional_variables(df)
    
    # Generate tables
    table_I = table_I_summary_statistics(df)
    table_II = table_II_position_changes_returns(df)
    table_III = table_III_return_predictability(df)
    table_IV = table_IV_dcot_analysis(df)
    table_V = table_V_portfolio_sorts(df)
    table_VI = table_VI_smoothed_hp(df)
    table_VII = table_VII_hp_dcot(df)
    table_VIII = table_VIII_double_sorts(df)
    
    print("\n" + "=" * 70)
    print("TABLE REPLICATION COMPLETED")
    print("=" * 70)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nAll tables saved to output/tables/")
    print("\nTables generated:")
    print("  ✓ Table I: Summary Statistics")
    print("  ✓ Table II: Weekly Position Changes and Returns")
    print("  ✓ Table III: Return Predictability")
    print("  ⚠ Table IV: DCOT Data Analysis (skipped)")
    print("  ✓ Table V: Portfolio Sorts")
    print("  ✓ Table VI: Smoothed Hedging Pressure")
    print("  ⚠ Table VII: Hedging Pressure DCOT (skipped)")
    print("  ✓ Table VIII: Double-Sorted Portfolios")
