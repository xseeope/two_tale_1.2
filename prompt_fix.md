# Prompt_fix

### 任务一

从 data aquisition 开始，更换数据源为如下资产。

```python
tickers = {
    # Energy
    'CL': 'CL=F',  # Crude Oil（原文本中 Oil 一般指原油）
    'HO': 'HO=F',  # Heating Oil
    'NG': 'NG=F',  # Natural Gas

    # Metals
    'PL': 'PL=F',  # Platinum
    'PA': 'PA=F',  # Palladium
    'SI': 'SI=F',  # Silver
    'HG': 'HG=F',  # Copper
    'GC': 'GC=F',  # Gold

    # Grains
    'ZW': 'ZW=F',  # Wheat（一般指芝加哥软红冬麦）
    'KE': 'KE=F',  # KC Wheat（堪萨斯城硬红冬麦，yfinance 用 KE）
    'MW': 'MW=F',  # Minn Wheat（明尼阿波利斯硬红春麦，yfinance 用 MW）
    'ZC': 'ZC=F',  # Corn
    'ZO': 'ZO=F',  # Oats
    'ZS': 'ZS=F',  # Soybean
    'ZL': 'ZL=F',  # Soybean Oil
    'ZM': 'ZM=F',  # Soybean Meal
    'RR': 'RR=F',  # Rough Rice

    # Softs
    'CT': 'CT=F',  # Cotton
    'OJ': 'OJ=F',  # Orange Juice
    'LB': 'LB=F',  # Lumber（yfinance 用 LB）
    'CC': 'CC=F',  # Cocoa
    'SB': 'SB=F',  # Sugar
    'KC': 'KC=F',  # Coffee

    # Livestock
    'HE': 'HE=F',  # Lean Hogs
    'LE': 'LE=F',  # Live Cattle
    'GF': 'GF=F',  # Feeder Cattle
}
```

### 任务二

现在的数据预处理后产生的processed 文件夹下，第一列的日期列没有按照时间顺序排列，请修复，并且重新运行 data aquisition 和 data preproc

### 任务三

table_replication.py 中函数 table_I_summary_statistics() 请一定要注意要年化收益率，如果已经是年化收益率了，就不用改

### 任务四

table_replication.py 中函数 table_II_position_changes_returns()  中修改 y 的设定，将y 设定为 commercial Q 和 non commercial Q

### 任务五

在你完成以上四个任务之后，重新跑一遍全流程，尤其是 table 的构建