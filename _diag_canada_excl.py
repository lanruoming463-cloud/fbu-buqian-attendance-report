# -*- coding: utf-8 -*-
"""诊断：加拿大区 3 个仓(卡尔加里1号仓/温哥华2号仓/温哥华3号仓) 11月1-8日 正式工记录受影响量。
口径：匹配 wh in 三仓 且 region 含'加拿' 且 date in 11.01-11.08。
"""
import json, _inject_1025 as I25
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
B = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性"
SRC = [
    B + r"\正式工\11月\正式工-考勤记录-11.1-11.3-及时性.xlsx",
    B + r"\正式工\11月\正式工-考勤记录-11.4-及时性.xlsx",
    B + r"\正式工\11月\正式工-考勤记录-11.5-及时性.xlsx",
    B + r"\正式工\11月\正式工-考勤记录-11.6-及时性.xlsx",
]
WH_SET = {'卡尔加里1号仓', '温哥华2号仓', '温哥华3号仓'}

recs = []
for p in SRC:
    r, _ = I25.build_formal_recs(p)
    recs.extend(r)

# 匹配
hit = [r for r in recs if r['wh'] in WH_SET and '加拿' in r['region'] and '2026-11-01' <= r['date'] <= '2026-11-08']
print("匹配记录数:", len(hit))
print("  区域/仓 分布:")
by_wh = defaultdict(int)
for r in hit: by_wh[(r['region'], r['wh'])] += 1
for k, v in sorted(by_wh.items()): print("    ", k, v)
abn = [r for r in hit if r['abnormal']]
unt = [r for r in hit if r['untimely']]
print("  其中 异常(abnormal)数:", len(abn), " 未及时(untimely)数:", len(unt))
# 异常按日
abn_day = defaultdict(int)
for r in abn: abn_day[r['date']] += 1
print("  异常按日:", dict(sorted(abn_day.items())))
# 异常按工号
abn_gong = defaultdict(int)
for r in abn: abn_gong[r['gong']] += 1
print("  异常按工号(前20):", dict(sorted(abn_gong.items(), key=lambda x:-x[1])[:20]))
print("  参与工号数:", len(set(r['gong'] for r in hit)))

# 当前线上 empIndex 中 加拿大区 gk 的 Nov 行
h = open(WS + r"\补签流程_补签统计.html", encoding='utf-8').read()
i = h.find('const formalAttPayload = '); nl = h.find("\n", i)
fp = json.loads(h[i:nl][len('const formalAttPayload = '):].rstrip().rstrip(";"))
print("\n线上 加拿大区 gk (含 Nov 行数):")
for gk, rows in fp['empIndex'].items():
    if '加拿大区' in gk:
        nov = [r for r in rows if r[13] >= '2026-11-01']
        if nov:
            print("   ", gk, "总行", len(rows), "Nov行", len(nov))
# 加拿大区 在 topEmpIndex?
print("\n线上 topEmpIndex 含 加拿大区 键:", [k for k in fp['topEmpIndex'] if '加拿大区' in k])
for k in [kk for kk in fp['topEmpIndex'] if '加拿大区' in kk]:
    print("   ", k, "条目:", [(e['gong'], e.get('untimely')) for e in fp['topEmpIndex'][k]])
print("\ntopEmpIndexM['2026-11'] 含 加拿大区 键:", [k for k in fp['topEmpIndexM'].get('2026-11',{}) if '加拿大区' in k])
