# -*- coding: utf-8 -*-
"""本地正式工 6 月逐日基线：原始值 + 脚本剔除后值（与前端口径对齐用）"""
import pandas as pd, glob, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

cands = [p for p in glob.glob(r'D:\Documents\Downloads\*正式工*考勤*.xlsx') if '6月' in p or '2026-06' in p]
exact = r'D:\Documents\Downloads\正式工-6月考勤记录.xlsx'
import os
cands = [exact] if os.path.exists(exact) else cands
print('file:', cands[0].split('\\')[-1] if cands else 'NONE')
df = pd.read_excel(cands[0], sheet_name=0)
print('cols:', list(df.columns))
df['考勤日期'] = pd.to_datetime(df['考勤日期'], errors='coerce')
d6 = df[df['考勤日期'].dt.strftime('%Y-%m') == '2026-06'].copy()

def le(v):
    if pd.isna(v):
        return False
    s = str(v)
    return ('迟到' in s) or ('早退' in s)

# 检测脚本剔除所用列（四级部门等）
dept_col = next((c for c in d6.columns if '四级' in str(c)), None)
print('dept_col:', dept_col)

rows = []
for d, g in d6.groupby(d6['考勤日期'].dt.strftime('%Y-%m-%d')):
    abn = g[g['考勤状态'] == '异常']
    nt = abn[~(abn['异常备注'].apply(le) | abn['备注'].apply(le))]
    # 脚本剔除口径：财务部 / 四级部门为空
    kept = g
    if dept_col:
        dc = g[dept_col].astype(str)
        kept = g[~(dc.str.contains('财务部', na=False) | (g[dept_col].isna()) | (dc == 'nan'))]
    kabn = kept[kept['考勤状态'] == '异常']
    knt = kabn[~(kabn['异常备注'].apply(le) | kabn['备注'].apply(le))]
    rows.append({'date': d, 'raw_total': len(g), 'raw_abn': len(abn), 'raw_nt': len(nt),
                 'kept_total': len(kept), 'kept_abn': len(kabn), 'kept_nt': len(knt)})

out = pd.DataFrame(rows).sort_values('date')
out.to_csv('mcp_baseline_2026-06_daily.csv', index=False, encoding='utf-8-sig')
print(out.to_string(index=False))
s = out[['raw_total', 'raw_abn', 'raw_nt', 'kept_total', 'kept_abn', 'kept_nt']].sum()
print('JUNE RAW:', int(s.raw_total), int(s.raw_abn), int(s.raw_nt))
print('JUNE KEPT:', int(s.kept_total), int(s.kept_abn), int(s.kept_nt))
r1 = out[out.date == '2026-06-01'].iloc[0]
print('0601 RAW:', int(r1.raw_total), int(r1.raw_abn), int(r1.raw_nt), '| KEPT:', int(r1.kept_total), int(r1.kept_abn), int(r1.kept_nt))
