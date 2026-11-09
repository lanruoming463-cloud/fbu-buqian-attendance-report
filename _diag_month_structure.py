# -*- coding: utf-8 -*-
"""诊断 正式工 Nov 月块/日块的 warehouse/group 是否按 untimely>0 过滤；并复算当前源 Nov 全量。"""
import json
import _inject_1025 as I25
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
B = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性"
SRC = [
    B + r"\正式工\11月\正式工-考勤记录-11.1-11.3-及时性.xlsx",
    B + r"\正式工\11月\正式工-考勤记录-11.4-及时性.xlsx",
    B + r"\正式工\11月\正式工-考勤记录-11.5-及时性.xlsx",
]

def extract(name):
    h = open(HTML, encoding='utf-8').read()
    pre = "const %s = " % name; i = h.find(pre); nl = h.find("\n", i)
    return json.loads(h[i:nl][len(pre):].rstrip().rstrip(";"))

fp = extract("formalAttPayload")
mb = fp['data']['2026-11']
print("=== 月块 2026-11 结构 ===")
print("  total:", mb['total'])
for lvl in ('major','detail','warehouse','group'):
    lst = mb.get(lvl, [])
    n0 = sum(1 for e in lst if e.get('untimely',0) > 0)
    print(f"  {lvl}: 条目数={len(lst)} 其中 untimely>0={n0} 含 untimely==0={len(lst)-n0}")
print("  月块 warehouse 示例(前3):", mb.get('warehouse',[])[:3])

print("\n=== 日块 2026-11-04 结构 ===")
db = fp['data']['2026-11-04']
for lvl in ('major','detail','warehouse','group'):
    lst = db.get(lvl, [])
    n0 = sum(1 for e in lst if e.get('untimely',0) > 0)
    print(f"  {lvl}: 条目数={len(lst)} 其中 untimely>0={n0} 含 untimely==0={len(lst)-n0}")

print("\n=== 当前源复算 Nov 全量 (agg_formal) 结构 ===")
recs=[]; 
for p in SRC:
    r,_=I25.build_formal_recs(p); recs.extend(r)
print("  源总记录:", len(recs))
blk = I25.agg_formal(recs)
print("  全量 total:", blk['total'])
for lvl in ('major','detail','warehouse','group'):
    lst = blk.get(lvl, [])
    n0 = sum(1 for e in lst if e.get('untimely',0) > 0)
    print(f"  {lvl}: 条目数={len(lst)} 其中 untimely>0={n0} 含 untimely==0={len(lst)-n0}")
# 仅过滤 warehouse/group 后
blk2 = I25.agg_formal(recs)
blk2['warehouse']=[w for w in blk2['warehouse'] if w.get('untimely',0)>0]
blk2['group']=[g for g in blk2['group'] if g.get('untimely',0)>0]
print("  过滤后 warehouse 条目数:", len(blk2['warehouse']), " group 条目数:", len(blk2['group']))

# 月块 欧洲区|英国区 detail 当前值 vs 源
def find_detail(block, region):
    for e in block.get('detail',[]):
        if e.get('region')==region: return e
    return None
cur=find_detail(mb,'英国区'); src=find_detail(blk,'英国区')
print("\n  英国区 detail 当前:", cur)
print("  英国区 detail 源(全量):", src)
