"""
使用 yfinance 获取期货合约基差数据
基于实际验证的方法：特定合约格式为 [CODE][MONTH][YEAR]=F
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 期货月份代码映射
MONTH_CODES = {
    'F': 1,  # January
    'G': 2,  # February
    'H': 3,  # March
    'J': 4,  # April
    'K': 5,  # May
    'M': 6,  # June
    'N': 7,  # July
    'Q': 8,  # August
    'U': 9,  # September
    'V': 10, # October
    'X': 11, # November
    'Z': 12  # December
}

COMMODITIES = {
    'CL': 'Crude Oil',
    'NG': 'Natural Gas',
    'HO': 'Heating Oil',
    'GC': 'Gold',
    'SI': 'Silver',
    'HG': 'Copper',
    'ZW': 'Wheat',
    'ZC': 'Corn',
    'ZS': 'Soybean',
    'ZL': 'Soybean Oil',
    'ZM': 'Soybean Meal',
    'CT': 'Cotton',
    'KC': 'Coffee',
    'SB': 'Sugar',
}

def generate_contract_ticker(commodity, month_code, year, is_front=False):
    """
    生成期货合约ticker
    
    Parameters:
    -----------
    commodity : str
        商品代码，如 'CL' for Crude Oil
    month_code : str
        月份代码，如 'H' for March
    year : int or str
        年份，如 2025 或 '25'
    is_front : bool
        是否为主力合约（连续合约）
        
    Returns:
    --------
    str : ticker格式，如 'CLH25=F' 或 'CL=F'
    """
    if is_front:
        return f"{commodity}=F"
    
    # 处理年份格式
    if isinstance(year, int):
        year_str = str(year)[-2:]  # 取后两位
    else:
        year_str = str(year)
        
    return f"{commodity}{month_code}{year_str}=F"

def get_futures_basis(commodity='CL', start_date='2020-01-01', end_date=None):
    """
    获取期货合约基差数据
    
    Parameters:
    -----------
    commodity : str
        商品代码
    start_date : str
        开始日期
    end_date : str
        结束日期，默认为今天
        
    Returns:
    --------
    pd.DataFrame : 包含主力合约、次主力合约和基差的DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n{'='*70}")
    print(f"获取 {COMMODITIES.get(commodity, commodity)} 期货基差数据")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"{'='*70}\n")
    
    # 获取主力合约
    front_ticker = generate_contract_ticker(commodity, None, None, is_front=True)
    print(f"下载主力合约: {front_ticker} ... ", end='')
    try:
        front_data = yf.download(front_ticker, start=start_date, end=end_date, progress=False)
        if not front_data.empty:
            print(f"✓ ({len(front_data)} 天)")
        else:
            print("✗ 无数据")
            return None
    except Exception as e:
        print(f"✗ 错误: {str(e)[:50]}")
        return None
    
    # 尝试获取下一个到期月份的合约
    # 简化：尝试获取3个月后和6个月后的合约
    today = datetime.now()
    
    contracts = {}
    for months_ahead in [3, 6, 9, 12]:
        future_date = today + timedelta(days=30*months_ahead)
        month_num = future_date.month
        year = future_date.year
        
        # 找到对应的月份代码
        month_code = None
        for code, num in MONTH_CODES.items():
            if num == month_num:
                month_code = code
                break
        
        if month_code:
            ticker = generate_contract_ticker(commodity, month_code, year)
            print(f"下载 {months_ahead}个月后合约: {ticker} ... ", end='')
            try:
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    print(f"✓ ({len(data)} 天)")
                    contracts[f'{months_ahead}M'] = data['Close']
                else:
                    print("✗ 无数据")
            except Exception as e:
                print(f"✗ 错误")
    
    # 构建基差DataFrame
    result = pd.DataFrame()
    result['Front_Month'] = front_data['Close']
    
    for period, prices in contracts.items():
        result[f'Contract_{period}'] = prices
        result[f'Basis_{period}'] = prices - front_data['Close']
        result[f'Basis_Pct_{period}'] = (prices - front_data['Close']) / front_data['Close'] * 100
    
    return result

def calculate_calendar_spread(commodity='CL', near_month='H', far_month='M', 
                              year=2025, start_date='2024-01-01'):
    """
    计算两个特定合约之间的日历价差
    
    Parameters:
    -----------
    commodity : str
        商品代码
    near_month : str
        近月合约月份代码
    far_month : str
        远月合约月份代码
    year : int
        年份
    start_date : str
        开始日期
    
    Returns:
    --------
    pd.DataFrame : 包含价差的DataFrame
    """
    near_ticker = generate_contract_ticker(commodity, near_month, year)
    far_ticker = generate_contract_ticker(commodity, far_month, year)
    
    print(f"\n计算日历价差: {near_ticker} vs {far_ticker}")
    
    # 下载数据
    near_data = yf.download(near_ticker, start=start_date, progress=False)
    far_data = yf.download(far_ticker, start=start_date, progress=False)
    
    if near_data.empty or far_data.empty:
        print("✗ 无法获取数据")
        return None
    
    # 计算价差
    result = pd.DataFrame({
        f'{near_ticker}': near_data['Close'],
        f'{far_ticker}': far_data['Close']
    })
    
    result['Calendar_Spread'] = far_data['Close'] - near_data['Close']
    result['Spread_Pct'] = (far_data['Close'] - near_data['Close']) / near_data['Close'] * 100
    
    return result

if __name__ == '__main__':
    print("\n" + "="*70)
    print("期货基差数据获取工具")
    print("="*70)
    
    # 示例1: 获取原油基差
    print("\n【示例1】获取原油(CL)基差数据")
    basis_cl = get_futures_basis('CL', start_date='2024-01-01')
    if basis_cl is not None:
        print("\n最近5天的基差数据:")
        print(basis_cl.tail())
        print(f"\n平均基差（3个月）: {basis_cl['Basis_3M'].mean():.2f}")
        
        # 保存数据
        basis_cl.to_csv('data/prices/CL_basis.csv')
        print("\n✓ 数据已保存至 data/prices/CL_basis.csv")
    
    # 示例2: 计算特定合约价差
    print("\n" + "="*70)
    print("【示例2】计算特定合约日历价差")
    # spread = calculate_calendar_spread('CL', 'H', 'M', 2025, '2024-01-01')
    # if spread is not None:
    #     print("\n最近5天的价差:")
    #     print(spread.tail())
    
    print("\n" + "="*70)
    print("说明:")
    print("1. 主力合约格式: CL=F")
    print("2. 特定合约格式: CLH25=F (原油2025年3月)")
    print("3. 月份代码: F(1月), G(2月), H(3月), J(4月), K(5月), M(6月)")
    print("             N(7月), Q(8月), U(9月), V(10月), X(11月), Z(12月)")
    print("="*70)
