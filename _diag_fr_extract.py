# -*- coding: utf-8 -*-
"""提取本次三类目标的精确字段与分组路径，供修正脚本使用。
A) 正式工白名单: Ying HUANG zt15752 11月5条 + Yixuan DU zt0023339 11月3条 + 法国区11-10非Jie REN 3条
B) 正式工整条剔除: Jie REN zt0022107 11月5条
C) 劳务工白名单: 法国区 2026-11-10 全部176条未确认
"""
import json
from collections import defaultdict, Counter
WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"

def extract(html, name):
    pre = "const %s = " % name; i = html.find(pre)
    if i < 0: pre = "var %s = " % name; i = html.find(pre)
    nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))

html = open(HTML, encoding='utf-8').read()
fp = extract(html, 'formalAttPayload'); ap = extract(html, 'attendPayload')

# ===== 正式工：列出所有目标行的 完整字段 + 组key =====
WL_GONGS = {'zt15752': 'Ying HUANG', 'zt0023339': 'Yixuan DU'}
EXCL_GONG = 'zt0022107'  # Jie REN
D = '2026-11-10'

print("######## 正式工 empIndex 记录字段结构 ########")
sample = next(iter(fp['empIndex'].values()))[0]
for i, v in enumerate(sample): print(f"  [{i}] {repr(v)}")

print("\n######## A) 正式工白名单目标（Ying HUANG/Yixuan DU，11月）########")
a_rows = []
for gk, recs in fp['empIndex'].items():
    for r in recs:
        if not isinstance(r, list) or len(r) < 6: continue
        gong = str(r[1]).strip().lower(); date = str(r[5])[:10]
        if gong in WL_GONGS and date.startswith('2026-11'):
            a_rows.append((gk, gong, date, r))
for gk, gong, date, r in sorted(a_rows, key=lambda x: (x[1], x[2])):
    print(f"  {WL_GONGS[gong]:12} {date} GK={gk} rec={json.dumps(r,ensure_ascii=False)}")
print("A) 合计:", len(a_rows), " 按人:", dict(Counter(x[1] for x in a_rows)))

print("\n######## A2) 法国区11-10 正式工异常（排除Jie REN）########")
a2_rows = []
for gk, recs in fp['empIndex'].items():
    if '法国区' not in gk: continue
    for r in recs:
        if not isinstance(r, list) or len(r) < 6: continue
        date = str(r[5])[:10]; gong = str(r[1]).strip().lower()
        if date == D and gong != EXCL_GONG:
            a2_rows.append((gk, gong, date, r))
for gk, gong, date, r in a2_rows:
    print(f"  {gong} {date} GK={gk} rec={json.dumps(r,ensure_ascii=False)}")
print("A2) 合计:", len(a2_rows))

print("\n######## B) 正式工整条剔除 Jie REN（11月）########")
b_rows = []
for gk, recs in fp['empIndex'].items():
    for r in recs:
        if not isinstance(r, list) or len(r) < 6: continue
        gong = str(r[1]).strip().lower(); date = str(r[5])[:10]
        if gong == EXCL_GONG and date.startswith('2026-11'):
            b_rows.append((gk, gong, date, r))
for gk, gong, date, r in sorted(b_rows, key=lambda x: x[2]):
    print(f"  {date} GK={gk} rec={json.dumps(r,ensure_ascii=False)}")
print("B) 合计:", len(b_rows))

print("\n######## C) 劳务工 法国区 11-10 未确认 empIndex 记录结构 ########")
sample_l = next(iter(ap['empIndex'].values()))[0]
for i, v in enumerate(sample_l): print(f"  [{i}] {repr(v)}")
print("\n  法国区11-10 样本5条:")
cnt = 0
c_rows = []
for gk, recs in ap['empIndex'].items():
    if '法国区' not in gk: continue
    for r in recs:
        if not isinstance(r, list) or len(r) < 4: continue
        if str(r[3])[:10] == D:
            c_rows.append((gk, r))
            if cnt < 5:
                print(f"    GK={gk} rec={json.dumps(r,ensure_ascii=False)}"); cnt += 1
print("C) 合计:", len(c_rows), " 按GK组数:", len(set(x[0] for x in c_rows)))
# 确认这些组的日块 group 节点是否都存在
dblk = ap['data'][D]
print("  劳务工11-10 total:", dblk['total'])
print("  detail 法国区:", [e for e in dblk.get('detail',[]) if '法国区' in str(e.get('region',''))])
print("  warehouse 法国区数:", sum(1 for e in dblk.get('warehouse',[]) if '法国区' in str(e.get('region',''))))
print("  group 法国区数:", sum(1 for e in dblk.get('group',[]) if '法国区' in str(e.get('region',''))))
