import pandas as pd, openpyxl
from collections import Counter

BASE = r'D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性'

print("=== 正式工10月 日期解析 ===")
for f in [BASE + r'/正式工-考勤记录-10.1-10.6-及时性.xlsx',
          BASE + r'/正式工-考勤记录-10.7-及时性.xlsx']:
    df = pd.read_excel(f, sheet_name='考勤记录')
    d = pd.to_datetime(df['考勤日期'], errors='coerce')
    c = Counter(d.dropna().dt.strftime('%Y-%m'))
    print(f.split('/')[-1], '总行=', len(df), 'ym分布=', dict(c))

print("=== 劳务工10月 日期解析 ===")
for f in [BASE + r'/劳务工-考勤记录-10.1-10.6-及时性.xlsx',
          BASE + r'/劳务工-考勤记录-10.7-及时性.xlsx']:
    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    ws = wb['考勤']
    c = Counter()
    for row in ws.iter_rows(values_only=True):
        dd = row[10]
        if isinstance(dd, str) and len(dd) >= 10 and dd[:4] == '2026':
            c[dd[:7]] += 1
        elif hasattr(dd, 'strftime'):
            c[dd.strftime('%Y-%m')] += 1
    print(f.split('/')[-1], 'ym分布=', dict(c))
    wb.close()

print("=== 正式工旧6/7月 日期分布（确认5月来源）===")
for f in [r'D:/Documents/Downloads/正式工-7月考勤记录.xlsx',
          r'D:/Documents/Downloads/正式工-6月考勤记录.xlsx']:
    df = pd.read_excel(f, sheet_name='考勤记录')
    d = pd.to_datetime(df['考勤日期'], errors='coerce')
    c = Counter(d.dropna().dt.strftime('%Y-%m'))
    print(f.split('/')[-1], 'ym分布=', dict(c))
print("DONE")
