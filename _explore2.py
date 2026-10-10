import pandas as pd, openpyxl

print("=== 正式工源文件（Downloads）===")
for f in [r'D:/Documents/Downloads/正式工-7月考勤记录.xlsx',
          r'D:/Documents/Downloads/正式工-6月考勤记录.xlsx']:
    try:
        df = pd.read_excel(f, sheet_name='考勤记录', usecols=['考勤日期'])
        ds = pd.to_datetime(df['考勤日期'], errors='coerce').dropna()
        print(f.split('/')[-1], '| rows=', len(ds), '| min=', ds.min(), '| max=', ds.max())
    except Exception as e:
        print('ERR', f, '->', e)

print("=== 劳务工源文件（Downloads/劳务工工时）===")
for f in [r'D:/Documents/Downloads/劳务工工时-20260702.xlsx',
          r'D:/Documents/Downloads/劳务工工时-20260803.xlsx']:
    try:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        ws = wb['考勤']
        mn, mx, cnt = None, None, 0
        for row in ws.iter_rows(values_only=True):
            d = row[10]
            if isinstance(d, str) and len(d) >= 10:
                s = d[:10]
                if mn is None or s < mn: mn = s
                if mx is None or s > mx: mx = s
                cnt += 1
        print(f.split('/')[-1], '| rows=', cnt, '| min=', mn, '| max=', mx)
        wb.close()
    except Exception as e:
        print('ERR', f, '->', e)
print("DONE")
