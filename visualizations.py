"""
Visualization Script for "A Tale of Two Premiums" Results
Creates plots and charts for key findings
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

# Create output directory
os.makedirs('output/figures', exist_ok=True)

def plot_summary_statistics():
    """Plot summary statistics from Table I"""
    print("Creating summary statistics plots...")
    
    df = pd.read_csv('output/tables/table_I_summary_statistics.csv')
    df = df[df['Ticker'] != 'AVERAGE'].copy()
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Plot 1: Excess Returns
    ax = axes[0, 0]
    df_sorted = df.sort_values('Excess_Ret_Mean')
    ax.barh(df_sorted['Ticker'], df_sorted['Excess_Ret_Mean'])
    ax.set_xlabel('Annual Excess Return (%)')
    ax.set_title('Panel A: Excess Returns by Commodity')
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Hedging Pressure
    ax = axes[0, 1]
    df_sorted = df.sort_values('HP_Mean')
    colors = ['red' if x < 0 else 'green' for x in df_sorted['HP_Mean']]
    ax.barh(df_sorted['Ticker'], df_sorted['HP_Mean'], color=colors, alpha=0.6)
    ax.set_xlabel('Hedging Pressure (HP)')
    ax.set_title('Panel B: Hedging Pressure by Commodity')
    ax.axvline(x=0, color='black', linestyle='-', alpha=0.5)
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Risk-Return Scatter
    ax = axes[1, 0]
    ax.scatter(df['Excess_Ret_Std'], df['Excess_Ret_Mean'], s=100, alpha=0.6)
    for idx, row in df.iterrows():
        ax.annotate(row['Ticker'], (row['Excess_Ret_Std'], row['Excess_Ret_Mean']),
                   fontsize=8, alpha=0.7)
    ax.set_xlabel('Volatility (Std Dev)')
    ax.set_ylabel('Expected Return')
    ax.set_title('Risk-Return Trade-off')
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Trading Activity
    ax = axes[1, 1]
    x = np.arange(len(df))
    width = 0.35
    ax.bar(x - width/2, df['|Q_Comm|_Mean'], width, label='Commercial', alpha=0.7)
    ax.bar(x + width/2, df['|Q_NonComm|_Mean'], width, label='Non-Commercial', alpha=0.7)
    ax.set_xlabel('Commodity')
    ax.set_ylabel('|Q| Mean')
    ax.set_title('Trading Activity by Trader Type')
    ax.set_xticks(x)
    ax.set_xticklabels(df['Ticker'], rotation=90, fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/figures/fig1_summary_statistics.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig1_summary_statistics.png")
    plt.close()

def plot_return_predictability():
    """Plot return predictability results from Table III"""
    print("Creating return predictability plots...")
    
    # Read Table III
    df = pd.read_excel('output/tables/table_III_return_predictability.xlsx', sheet_name='Model_4')
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot coefficients
    ax = axes[0]
    vars = ['Q_Comm', 'Q_NonComm', 'HP', 'Ret']
    coeffs = [df[df['Variable'] == v]['Coefficient'].values[0] for v in vars]
    tstats = [df[df['Variable'] == v]['t_stat'].values[0] for v in vars]
    
    colors = ['red' if c < 0 else 'green' for c in coeffs]
    bars = ax.bar(vars, coeffs, color=colors, alpha=0.7)
    ax.set_ylabel('Coefficient')
    ax.set_title('Return Predictability: R_{t+1} = f(Q_Comm, Q_NonComm, HP, R_t)')
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax.grid(True, alpha=0.3)
    
    # Add t-stat labels
    for i, (bar, tstat) in enumerate(zip(bars, tstats)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f't={tstat:.2f}',
                ha='center', va='bottom' if height > 0 else 'top', fontsize=9)
    
    # Plot t-statistics
    ax = axes[1]
    colors = ['red' if abs(t) > 2.576 else 'orange' if abs(t) > 1.96 else 'yellow' if abs(t) > 1.645 else 'gray' 
              for t in tstats]
    bars = ax.bar(vars, tstats, color=colors, alpha=0.7)
    ax.set_ylabel('t-statistic')
    ax.set_title('Statistical Significance')
    ax.axhline(y=1.96, color='red', linestyle='--', alpha=0.5, label='p<0.05')
    ax.axhline(y=-1.96, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/figures/fig2_return_predictability.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig2_return_predictability.png")
    plt.close()

def plot_portfolio_sorts():
    """Plot portfolio sorts from Table V"""
    print("Creating portfolio sorts plots...")
    
    df = pd.read_csv('output/tables/table_V_portfolio_sorts.csv')
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot returns by quintile
    ax = axes[0]
    horizons = df['Horizon_Weeks'].values
    q1 = df['Q1_Return'].values
    q5 = df['Q5_Return'].values
    ls = df['LS_Return'].values
    
    ax.plot(horizons, q1, 'o-', label='Q1 (Low Q_Comm)', linewidth=2)
    ax.plot(horizons, q5, 's-', label='Q5 (High Q_Comm)', linewidth=2)
    ax.plot(horizons, ls, '^-', label='Long-Short (Q5-Q1)', linewidth=2, color='red')
    ax.set_xlabel('Horizon (Weeks)')
    ax.set_ylabel('Annualized Return (%)')
    ax.set_title('Portfolio Returns by Q_Comm Quintile')
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot t-statistics
    ax = axes[1]
    tstats = df['LS_tstat'].values
    colors = ['green' if abs(t) > 1.96 else 'orange' if abs(t) > 1.645 else 'gray' for t in tstats]
    bars = ax.bar(horizons, tstats, color=colors, alpha=0.7, width=3)
    ax.set_xlabel('Horizon (Weeks)')
    ax.set_ylabel('t-statistic')
    ax.set_title('Long-Short Strategy Significance')
    ax.axhline(y=1.96, color='red', linestyle='--', alpha=0.5, label='p<0.05')
    ax.axhline(y=-1.96, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/figures/fig3_portfolio_sorts.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig3_portfolio_sorts.png")
    plt.close()

def plot_profit_attribution():
    """Plot profit attribution from Table XI"""
    print("Creating profit attribution plots...")
    
    df = pd.read_csv('output/tables/table_XI_profit_attribution.csv')
    df = df[df['Ticker'] != 'AVERAGE'].copy()
    
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # Stack plot of profit components
    x = np.arange(len(df))
    width = 0.6
    
    hp_pct = df['HP_Pct'].fillna(0)
    mom_pct = df['MOM_Pct'].fillna(0)
    liq_pct = df['LIQ_Pct'].fillna(0)
    
    ax.bar(x, hp_pct, width, label='Hedging', alpha=0.7)
    ax.bar(x, mom_pct, width, bottom=hp_pct, label='Momentum', alpha=0.7)
    ax.bar(x, liq_pct, width, bottom=hp_pct+mom_pct, label='Liquidity', alpha=0.7)
    
    ax.set_ylabel('Profit Contribution (%)')
    ax.set_title('Profit Attribution by Source')
    ax.set_xticks(x)
    ax.set_xticklabels(df['Ticker'], rotation=45, fontsize=9)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax.axhline(y=100, color='red', linestyle='--', alpha=0.3)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('output/figures/fig4_profit_attribution.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig4_profit_attribution.png")
    plt.close()

def plot_double_sorts():
    """Plot double sorts from Table VIII"""
    print("Creating double sorts heatmap...")
    
    df = pd.read_csv('output/tables/table_VIII_double_sorts.csv')
    
    # Create matrix
    data = np.array([
        [df[df['Portfolio'] == 'LowHP_LowQ']['Mean_Return'].values[0],
         df[df['Portfolio'] == 'LowHP_HighQ']['Mean_Return'].values[0]],
        [df[df['Portfolio'] == 'HighHP_LowQ']['Mean_Return'].values[0],
         df[df['Portfolio'] == 'HighHP_HighQ']['Mean_Return'].values[0]]
    ])
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto')
    
    # Labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Low Q_Comm', 'High Q_Comm'])
    ax.set_yticklabels(['Low HP', 'High HP'])
    
    # Annotations
    for i in range(2):
        for j in range(2):
            text = ax.text(j, i, f'{data[i, j]:.1f}%',
                          ha="center", va="center", color="black", fontsize=14, weight='bold')
    
    ax.set_title('Double-Sorted Portfolio Returns\n(HP x Q_Comm)', fontsize=14, weight='bold')
    plt.colorbar(im, ax=ax, label='Annual Return (%)')
    
    plt.tight_layout()
    plt.savefig('output/figures/fig5_double_sorts.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig5_double_sorts.png")
    plt.close()

def create_all_visualizations():
    """Create all visualizations"""
    print("\n" + "=" * 70)
    print("CREATING VISUALIZATIONS")
    print("=" * 70)
    
    try:
        plot_summary_statistics()
        plot_return_predictability()
        plot_portfolio_sorts()
        plot_profit_attribution()
        plot_double_sorts()
        
        print("\n" + "=" * 70)
        print("ALL VISUALIZATIONS CREATED")
        print("=" * 70)
        print("\nFigures saved in output/figures/")
        print("  - fig1_summary_statistics.png")
        print("  - fig2_return_predictability.png")
        print("  - fig3_portfolio_sorts.png")
        print("  - fig4_profit_attribution.png")
        print("  - fig5_double_sorts.png")
        
    except Exception as e:
        print(f"\n✗ Error creating visualizations: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_all_visualizations()
