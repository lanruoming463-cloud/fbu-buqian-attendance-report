# -*- coding: utf-8 -*-
"""诊断：3 个英国区工号(zt0018758/zt0018175/zt0020024)在哪些 Nov 源文件出现；
以及线上 V22 HTML 的 Nov 日块/月块/empIndex 是否已含它们。"""
import json, re, os
import _inject_1025 as I25

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
B = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性"
FORMAL_SRC = {
    '11.1-11.3': B + r"\正式工\11月\正式工-考勤记录-11.1-11.3-及时性.xlsx",
    '11.4':      B + r"\正式工\11月\正式工-考勤记录-11.4-及时性.xlsx",
    '11.5':      B + r"\正式工\11月\正式工-考勤记录-11.5-及时性.xlsx",
}
UK3 = {'zt0018758', 'zt0018175', 'zt0020024'}

def extract(name):
    h = open(HTML, encoding='utf-8').read()
    pre = "const %s = " % name; i = h.find(pre); nl = h.find("\n", i)
    return json.loads(h[i:nl][len(pre):].rstrip().rstrip(";"))

print("===== (1) 各 Nov 正式工源文件中的 3 个英国区工号 =====")
for label, path in FORMAL_SRC.items():
    recs, unt = I25.build_formal_recs(path)
    hits = [r for r in recs if r['gong'] in UK3]
    dates = sorted(set(r['date'] for r in hits))
    unt_dates = sorted(set(r['date'] for r in hits if r['untimely']))
    print(f"  [{label}] 该3工号命中行数={len(hits)} 出现日期={dates} 其中未及时日期={unt_dates}")
    for r in hits:
        print(f"      {r['gong']} {r['name']} {r['region']}/{r['wh']}/{r['grp']} {r['date']} untimely={r['untimely']}")

print("\n===== (2) 线上 V22 HTML 的 Nov 正式工数据 =====")
fp = extract("formalAttPayload")
nov_days = sorted([d for d in fp['days'] if d >= '2026-11-01'])
print("  Nov 日块:", nov_days)
print("  月块 2026-11 total:", fp['data']['2026-11']['total'])
# empIndex 中是否含这3个工号
print("  empIndex 中含这3工号的 gk:", [gk for gk in fp['empIndex'] if any(e[1] in UK3 for e in fp['empIndex'][gk])])
# 逐日 total 累加
from collections import defaultdict
s = defaultdict(int)
for d in nov_days:
    for kk in I25.FORMAL_ATT_KEYS:
        s[kk] += fp['data'][d]['total'].get(kk, 0)
print("  线上 Nov 日块累加:", dict(s))
print("  与月块一致:", all(s[kk]==fp['data']['2026-11']['total'].get(kk,0) for kk in I25.FORMAL_ATT_KEYS))

print("\n===== (3) 这3工号是否出现在其他月份(6/7/10)线上 empIndex (验证历史存在) =====")
for ym in ('2026-06','2026-07','2026-10'):
    hits = []
    for gk, rows in fp['empIndex'].items():
        for e in rows:
            if str(e[1]) in UK3 and len(e) > 13 and e[13] == ym:
                hits.append((gk, e[1], e[-1]))
    print(f"  [{ym}] 命中 empIndex 行数={len(hits)} 例:{hits[:3]}")
