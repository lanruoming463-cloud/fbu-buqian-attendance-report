# -*- coding: utf-8 -*-
"""导出法国区（隶属欧洲区）两类名单：
  A. 考勤确认率 未及时确认人员（10月，正式工+劳务工）
  B. 补签 Top10 人员（2026-09 最新月，正式工+劳务工）
口径与主报表 gen_buqian_stats.py 保持一致。
"""
import pandas as pd
import numpy as np
import json
import os
from collections import defaultdict

BASE = r"C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58"
OUT = os.path.join(BASE, "法国区_导出名单.xlsx")

# -------------------- 花名册 工号->职位（用于正式工职位匹配） --------------------
ROSTER = r"D:/Documents/Downloads/花名册 - 2026-08-24T185145.634.xlsx"
_ro = pd.read_excel(ROSTER, usecols=['工号', '职位'])
pos_map = {}
for _, r in _ro.iterrows():
    g = str(r['工号']).strip() if pd.notna(r['工号']) else ''
    p = str(r['职位']).strip() if pd.notna(r['职位']) else ''
    if g and g != 'nan':
        pos_map[g] = p if p and p != 'nan' else '—'

# 劳务工考勤确认「指定日期剔除」（与主体报表一致，2026-10-22 起累计）：
# 法国区 6 位劳务工对应日期考勤数据剔除（不计入考勤确认及时率，亦不计入未及时确认名单）
LABOR_ATT_EXCLUDE_DATES = {
    ('FR083014', '2026-10-19'), ('FR091493', '2026-10-18'),
    ('FR086719', '2026-10-14'), ('FR092791', '2026-10-14'),
    ('FR093742', '2026-10-20'), ('FR092978', '2026-10-21'),
}


def fsv(v):
    """NaN 安全转字符串"""
    return str(v).strip() if pd.notna(v) else ''


# ============================================================
# Part A1: 正式工 考勤确认率 未及时确认（10月, 法国区）
# ============================================================
FORMAL_FILES = [
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.1-10.6-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.7-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.8-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.9-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.10-10.12-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.13-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.14-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.15-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.16-10.18-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/正式工/正式工-考勤记录-10.19-及时性.xlsx",
]
FORMAL_ATT_WHITELIST = {'zt0022905'}


def formal_untimely(r):
    """复刻主报表 _build_formal_recs 的未确认判定（法国区不触发捷克特殊口径）"""
    status = fsv(r['考勤状态'])
    if status != '异常':
        return False
    yc = fsv(r['异常备注'])
    bz = fsv(r['备注'])
    has_lc = ('迟到' in yc or '早退' in yc or '迟到' in bz or '早退' in bz)
    untimely = not has_lc
    # 法国区 != 捷克区，捷克特殊口径不生效
    if untimely:
        fc = fsv(r['首打卡'])
        lc = fsv(r['末打卡'])
        yc2 = fsv(r['异常备注'])
        if fc and lc and (yc2 == '' or yc2 == '空白'):
            untimely = False
    return untimely


rows_f = []
for f in FORMAL_FILES:
    print("[A1] reading", f.split('\\')[-1])
    df = pd.read_excel(f, sheet_name='考勤记录')
    df['_d'] = pd.to_datetime(df['考勤日期'], errors='coerce')
    for _, r in df.iterrows():
        d = r['_d']
        if pd.isna(d):
            continue
        l4 = fsv(r['四级部门'])
        if l4 != '法国区':          # 仅法国区运营（剔除 法国区HRBP部）
            continue
        gong = fsv(r['工号'])
        if gong in FORMAL_ATT_WHITELIST:   # 白名单统一及时
            continue
        if not formal_untimely(r):
            continue
        rows_f.append({
            '大区': '欧洲区', '区域': '法国区',
            '仓': fsv(r['五级部门']) or '部门直属',
            '组': fsv(r['六级部门']) or '部门直属',
            '姓名': fsv(r['姓名']), '工号': gong,
            '职位': pos_map.get(gong, '—'),
            '考勤日期': d.strftime('%Y-%m-%d'),
            '考勤状态': '异常',
            '备注': fsv(r['异常备注']),
            '确认状态': '未及时确认',
        })
df_f = pd.DataFrame(rows_f).sort_values('考勤日期', ascending=False).reset_index(drop=True)

# ============================================================
# Part A2: 劳务工 考勤确认率 未及时确认（10月, 法国区）
# ============================================================
LABOR_FILES = [
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.1-10.6-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.7-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.8-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.9-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.10-10.12-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.13-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.14-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.15-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.16-10.18-及时性.xlsx",
    r"D:/Documents/Desktop/AI做每月人力数据/T+1确认及时性/劳务工/劳务工-考勤记录-10.19-及时性.xlsx",
]
rows_l = []
for f in LABOR_FILES:
    print("[A2] reading", f.split('\\')[-1])
    df = pd.read_excel(f, sheet_name='考勤')
    for _, r in df.iterrows():
        if fsv(r['区域']) != '法国区':
            continue
        g = fsv(r['工号']); d = fsv(r['考勤日期'])[:10]
        if (g, d) in LABOR_ATT_EXCLUDE_DATES:   # 指定日期剔除（不计入及时率/未及时确认名单）
            continue
        qr = fsv(r['确认状态'])
        if qr in ('已确认', '已复核'):   # 及时确认
            continue
        rows_l.append({
            '大区': '欧洲区', '区域': '法国区',
            '仓库': fsv(r['仓库']), '组': fsv(r['组']) or '部门直属',
            '姓名': fsv(r['姓名']), '工号': fsv(r['工号']),
            '工种': fsv(r['工种']),
            '考勤日期': fsv(r['考勤日期']),
            '班次': fsv(r['班次']),
            '首打卡时间': fsv(r['首打卡时间']), '末打卡时间': fsv(r['末打卡时间']),
            '确认状态': qr,
            '考勤状态': fsv(r['考勤状态']),
            '备注': fsv(r['异常原因']),
        })
df_l = pd.DataFrame(rows_l).sort_values('考勤日期', ascending=False).reset_index(drop=True)

# ============================================================
# Part B1: 正式工 补签 Top10（2026-09, 法国区）—— 来自 emp_detail（考勤为基）
# ============================================================
_j = json.load(open(os.path.join(BASE, '_formal_attend_rate.json'), encoding='utf-8'))
_ed = _j['data']['2026-09']['emp_detail']
_fr = [e for e in _ed if e.get('region') == '法国区' and e.get('major') == '欧洲区']

_pf = defaultdict(lambda: {'name': '', 'days': 0})
for e in _fr:
    g = e['gong']
    _pf[g]['name'] = e['name']
    _pf[g]['days'] += 1
_top_f = sorted(_pf.items(), key=lambda kv: -kv[1]['days'])[:10]
_rank = {g: i + 1 for i, (g, _) in enumerate(_top_f)}
rows_ft = []
for e in sorted(_fr, key=lambda e: (_rank.get(e['gong'], 99), e['date'])):
    g = e['gong']
    if g not in _rank:
        continue
    rows_ft.append({
        '排名': _rank[g], '姓名': e['name'], '工号': g,
        '大区': e.get('major'), '区域': e.get('region'),
        '仓': e.get('wh') or '部门直属', '组': e.get('group') or '部门直属',
        '职位': pos_map.get(g, '—'),
        '补签天数': _pf[g]['days'],
        '补签日期': e['date'],
        '补签事由': e.get('reason', ''),
        '备注': e.get('remark', ''),
    })
df_ft = pd.DataFrame(rows_ft)

# ============================================================
# Part B2: 劳务工 补签 Top10（2026-09, 法国区）—— 来自 LABOR_SRCS 9月文件
# ============================================================
# 仅读 9 月文件即可（补签 Top10 取 2026-09 最新月）
LABOR_SRCS = [
    r'D:/Documents/Downloads/考勤确认及时性劳务工（09.01-09.30）.xlsx',
]
_time_cols = ['首打卡补签时间', '末打卡补签时间', '休息开始补签时间', '休息结束补签时间']


def fmt_time(v):
    if pd.isna(v) or v is None or v == '':
        return ''
    if hasattr(v, 'strftime'):
        return v.strftime('%H:%M')
    s = str(v).strip()
    if s.lower() in ('', 'nan', 'none'):
        return ''
    if __import__('re').match(r'^\d{1,2}:\d{2}:\d{2}$', s):
        return s[:-3]
    return s


L_frames = []
for f in LABOR_SRCS:
    print("[B2] reading", f.split('\\')[-1])
    L = pd.read_excel(f, sheet_name='劳务工-考勤表')
    L = L.rename(columns={'员工名称': '姓名'})
    L_frames.append(L)
L = pd.concat(L_frames, ignore_index=True)
L = L[L['区域'].astype(str) == '法国区'].copy()
L['dt'] = pd.to_datetime(L['考勤日期'], errors='coerce')
L = L[L['dt'].dt.strftime('%Y-%m') == '2026-09'].copy()
for c in ('实际补签数', '应打卡数', '应补签数'):
    L[c] = pd.to_numeric(L[c], errors='coerce').fillna(0)
# 应补签数封顶 2/人/日（复刻主报表）
L = L.sort_values(['工号', '考勤日期']).reset_index(drop=True)
_g = L.groupby(['工号', '考勤日期'])['应补签数']
_cum = _g.cumsum()
_prev = _cum - L['应补签数']
L['应补签数'] = np.minimum((2 - _prev).clip(lower=0), L['应补签数'])
L['实际补签数'] = np.minimum(L['实际补签数'], L['应补签数'])
L['is_record'] = (L['应补签数'] > 0) | (L['实际补签数'] > 0)
Lr = L[L['is_record']].copy()
for c in _time_cols:
    if c in Lr.columns:
        Lr[c] = Lr[c].apply(fmt_time)


def join_time(s):
    return '; '.join(sorted(set(x for x in s if x)))


_lab = Lr.groupby(['工号', '姓名', '工种']).agg(
    补签次数=('应补签数', 'sum'),
    主属仓=('仓库', lambda s: s.value_counts().sort_index().idxmax()),
    主属组=('组', lambda s: s.value_counts().sort_index().idxmax()),
).reset_index()
_lab = _lab[_lab['补签次数'] > 3].sort_values('补签次数', ascending=False).head(10)
_rank_l = {row['工号']: i + 1 for i, (_, row) in enumerate(_lab.iterrows())}
_labd = Lr[Lr['工号'].isin(_rank_l)].copy()
_labd['排名'] = _labd['工号'].map(_rank_l)
rows_lt = []
for _, r in _labd.sort_values(['排名', '考勤日期']).iterrows():
    g = r['工号']
    rows_lt.append({
        '排名': _rank_l[g], '姓名': r['姓名'], '工号': g,
        '大区': '欧洲区', '区域': '法国区',
        '仓库': r['仓库'], '组': r['组'] if pd.notna(r['组']) and str(r['组']).strip() else '部门直属',
        '工种': r['工种'] if pd.notna(r['工种']) else '—',
        '补签次数': int(_lab.set_index('工号').loc[g, '补签次数']),
        '补签日期': str(r['考勤日期'])[:10],
        '首打卡补签时间': r.get('首打卡补签时间', ''),
        '末打卡补签时间': r.get('末打卡补签时间', ''),
    })
df_lt = pd.DataFrame(rows_lt)

# ============================================================
# 写出 Excel
# ============================================================
with pd.ExcelWriter(OUT, engine='openpyxl') as xw:
    df_f.to_excel(xw, sheet_name='正式工_未及时确认_法国区_10月', index=False)
    df_l.to_excel(xw, sheet_name='劳务工_未及时确认_法国区_10月', index=False)
    df_ft.to_excel(xw, sheet_name='正式工_补签Top10_法国区_9月', index=False)
    df_lt.to_excel(xw, sheet_name='劳务工_补签Top10_法国区_9月', index=False)

print("输出文件:", OUT)
print("正式工 未及时确认(10月,法国区): %d 条" % len(df_f))
print("劳务工 未及时确认(10月,法国区): %d 条" % len(df_l))
print("正式工 补签Top10(9月,法国区): %d 人 / %d 行" % (df_ft['工号'].nunique() if len(df_ft) else 0, len(df_ft)))
print("劳务工 补签Top10(9月,法国区): %d 人 / %d 行" % (df_lt['工号'].nunique() if len(df_lt) else 0, len(df_lt)))
