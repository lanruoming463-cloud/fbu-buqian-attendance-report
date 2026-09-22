# -*- coding: utf-8 -*-
"""验证：迟到/早退结构化字段口径 与 异常备注文本口径 是否等价（6月数据）"""
import pandas as pd

F = r'D:\Documents\Downloads\正式工-6月考勤记录.xlsx'
df = pd.read_excel(F, sheet_name='考勤记录')
df['_abn'] = df['考勤状态'].astype(str) == '异常'
abn = df[df['_abn']].copy()

late_min = pd.to_numeric(abn['迟到分钟'], errors='coerce').fillna(0)
early_min = pd.to_numeric(abn['早退分钟'], errors='coerce').fillna(0)
yc = abn['异常备注'].astype(str)
bz = abn['备注'].astype(str)
has_le_txt = yc.str.contains('迟到|早退', na=False) | bz.str.contains('迟到|早退', na=False)
has_le_num = (late_min > 0) | (early_min > 0)

print('异常行数:', len(abn))
print('文本口径含迟到/早退:', int(has_le_txt.sum()))
print('数值口径含迟到/早退:', int(has_le_num.sum()))
print('两口径不一致行数:', int((has_le_txt != has_le_num).sum()))
diff = abn[has_le_txt != has_le_num]
if len(diff):
    print('\n不一致样本（异常备注 | 迟到分钟 | 早退分钟）:')
    for _, r in diff.head(10).iterrows():
        print(' ', r['异常备注'], '|', r['迟到分钟'], '|', r['早退分钟'])

# 未及时确认数（两种口径）
unt_txt = int((abn['_abn'] & ~has_le_txt).sum()) if '_abn' in abn else int((~has_le_txt).sum())
unt_num = int((~has_le_num).sum())
print('\n未及时确认（文本口径）:', unt_txt)
print('未及时确认（数值口径）:', unt_num)
print('总行数:', len(df), ' 及时率(数值口径): %.4f%%' % ((len(df) - unt_num) / len(df) * 100))
