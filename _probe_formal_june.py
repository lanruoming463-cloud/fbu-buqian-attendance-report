# -*- coding: utf-8 -*-
"""本地复算：正式工-6月考勤记录.xlsx 的及时率口径，验证与脚本 _build_formal_recs 一致"""
import pandas as pd

F = r'D:\Documents\Downloads\正式工-6月考勤记录.xlsx'
df = pd.read_excel(F, sheet_name='考勤记录')
print('列数:', len(df.columns), '行数:', len(df))
print('关键列存在:', [c for c in ['考勤日期','考勤状态','异常备注','备注','三级部门','四级部门','五级部门','六级部门','姓名','工号'] if c in df.columns])
print('列清单:', list(df.columns))

df['_d'] = pd.to_datetime(df['考勤日期'], errors='coerce')
df = df[df['_d'].notna()]
print('有效日期行:', len(df))

# 口径：考勤状态=异常 且 异常备注/备注不含迟到/早退 → 未及时确认
df['_abn'] = df['考勤状态'].astype(str) == '异常'
yc = df['异常备注'].astype(str)
bz = df['备注'].astype(str)
has_le = yc.str.contains('迟到|早退', na=False) | bz.str.contains('迟到|早退', na=False)
df['_untimely'] = df['_abn'] & ~has_le

total, abn, unt = len(df), int(df['_abn'].sum()), int(df['_untimely'].sum())
print('总考勤数:', total, '异常数:', abn, '未及时确认数:', unt)
print('及时率: %.4f' % ((total - unt) / total * 100) + '%')

# 异常备注的取值分布（前 15）
print('\n异常备注取值分布:')
print(df.loc[df['_abn'], '异常备注'].astype(str).value_counts().head(15).to_string())

# 备注列的取值分布（前 10）
print('\n备注(异常行)取值分布:')
print(df.loc[df['_abn'], '备注'].astype(str).value_counts().head(10).to_string())
