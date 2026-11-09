# -*- coding: utf-8 -*-
"""复算 Nov 11.1-11.4 源文件(经 build_formal_recs) 与 线上 V22 日块累加 对比。"""
import json, re
import _inject_1025 as I25
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
B = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性"
SRC = [
    B + r"\正式工\11月\正式工-考勤记录-11.1-11.3-及时性.xlsx",
    B + r"\正式工\11月\正式工-考勤记录-11.4-及时性.xlsx",
]

def extract(name):
    h = open(HTML, encoding='utf-8').read()
    pre = "const %s = " % name; i = h.find(pre); nl = h.find("\n", i)
    return json.loads(h[i:nl][len(pre):].rstrip().rstrip(";"))

# 全量复算 11.1-11.4 源
allrecs = []
for p in SRC:
    recs, _ = I25.build_formal_recs(p)
    allrecs.extend(recs)
print("11.1-11.4 源 build_formal_recs 总行:", len(allrecs))
per_day = defaultdict(lambda: {k:0 for k in I25.FORMAL_ATT_KEYS})
for r in allrecs:
    for kk in I25.FORMAL_ATT_KEYS:
        per_day[r['date']][kk] += r[kk]
print("  源逐日 total/untimely:")
for d in sorted(per_day):
    print(f"    {d}: total={per_day[d]['total']} untimely={per_day[d]['untimely']}")

# 线上逐日累加
fp = extract("formalAttPayload")
nov_days = sorted([d for d in fp['days'] if '2026-11' in d])
on_day = defaultdict(lambda: {k:0 for k in I25.FORMAL_ATT_KEYS})
for d in nov_days:
    for kk in I25.FORMAL_ATT_KEYS:
        on_day[d][kk] += fp['data'][d]['total'].get(kk,0)
print("线上逐日 total/untimely:")
for d in nov_days:
    print(f"    {d}: total={on_day[d]['total']} untimely={on_day[d]['untimely']}")

# 逐日对比
print("\n逐日对比(源 vs 线上):")
all_dates = sorted(set(per_day)|set(on_day))
mismatch = 0
for d in all_dates:
    s = per_day.get(d, {}); o = on_day.get(d, {})
    flag = "OK" if (s.get('total')==o.get('total') and s.get('untimely')==o.get('untimely')) else "DIFF"
    if flag=="DIFF": mismatch += 1
    print(f"  {d}: 源(total={s.get('total')},unt={s.get('untimely')}) 线上(total={o.get('total')},unt={o.get('untimely')}) {flag}")
print("MISMATCH 日数:", mismatch)

# 线上是否含伯明翰 detail
bk8 = None; bk2 = None
for d in nov_days:
    for e in fp['data'][d].get('detail', []):
        if e.get('region')=='英国区' and '伯明翰8号仓' in e.get('wh',''): bk8 = e
        if e.get('region')=='英国区' and '伯明翰2号仓' in e.get('wh',''): bk2 = e
print("线上 detail 伯明翰8号仓:", bk8)
print("线上 detail 伯明翰2号仓:", bk2)
