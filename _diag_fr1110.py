# -*- coding: utf-8 -*-
"""精确诊断: 三人 + 法国区 2026-11-10 当天异常，只输出 11-10 命中。"""
import json
from collections import Counter
WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"

def extract(html, name):
    pre = "const %s = " % name; i = html.find(pre)
    if i < 0:
        pre = "var %s = " % name; i = html.find(pre)
    nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))

html = open(HTML, encoding='utf-8').read()
fp = extract(html, 'formalAttPayload'); ap = extract(html, 'attendPayload')
D = '2026-11-10'

def has_date(rec):
    return any(isinstance(c, str) and c.startswith(D) for c in rec) if isinstance(rec, list) else False

def emp_info(rec):
    return (rec[0], rec[1]) if isinstance(rec, list) and len(rec) > 1 else ('?', '?')

TARGETS = {'zt15752': 'Ying HUANG', 'zt0023339': 'Yixuan DU', 'zt0022107': 'Jie REN'}

print("######## 正式工 empIndex 中 2026-11-10 命中 ########")
for gong, nm in TARGETS.items():
    rows = []
    for key, recs in fp['empIndex'].items():
        for rec in recs:
            if has_date(rec) and gong in str(rec[1]).lower():
                rows.append((key, rec))
    print(f"\n--- {nm} ({gong}) 11-10 命中 {len(rows)} 条 ---")
    for key, rec in rows:
        print("  ", key, json.dumps(rec, ensure_ascii=False))

print("\n######## 劳务工 empIndex 中 2026-11-10 命中（三人）########")
for gong, nm in TARGETS.items():
    rows = []
    for key, recs in ap['empIndex'].items():
        for rec in recs:
            if has_date(rec) and gong in str(rec[1]).lower():
                rows.append((key, rec))
    print(f"\n--- {nm} ({gong}) 11-10 命中 {len(rows)} 条 ---")
    for key, rec in rows:
        print("  ", key, json.dumps(rec, ensure_ascii=False))

print("\n######## 法国区 2026-11-10 正式工异常统计 ########")
fr_rows = []
for key, recs in fp['empIndex'].items():
    if '法国区' not in key: continue
    for rec in recs:
        if has_date(rec):
            fr_rows.append((key, rec))
print("法国区 11-10 正式工异常条数:", len(fr_rows))
c = Counter()
for key, rec in fr_rows:
    c[key] += 1
for k, v in c.most_common():
    print(f"  {v:>4}  {k}")
print("其中三人:", sum(1 for k, r in fr_rows if str(r[1]).lower() in TARGETS))

print("\n######## 法国区 2026-11-10 劳务工未确认统计 ########")
fr_l = []
for key, recs in ap['empIndex'].items():
    if '法国区' not in key: continue
    for rec in recs:
        if has_date(rec):
            fr_l.append((key, rec))
print("法国区 11-10 劳务工未确认条数:", len(fr_l))
c2 = Counter()
for key, rec in fr_l:
    c2[key] += 1
for k, v in c2.most_common():
    print(f"  {v:>4}  {k}")

print("\n######## 日块 total 基线（11-10）########")
print("正式工 11-10 total:", fp['data'][D]['total'])
print("劳务工 11-10 total:", ap['data'][D]['total'])
