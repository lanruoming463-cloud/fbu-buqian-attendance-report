# -*- coding: utf-8 -*-
"""核对劳务工法国区11-10 empIndex未确认(176) 与 日块group节点unconfirmed(198) 差异来源。"""
import json
from collections import Counter, defaultdict
WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
def ex(n):
    p="const %s = "%n; i=__import__('builtins').open(HTML,encoding='utf-8').read().find(p)
    h=open(HTML,encoding='utf-8').read()
    i=h.find(p)
    if i<0:p="var %s = "%n;i=h.find(p)
    nl=h.find("\n",i);return json.loads(h[i:nl][len(p):].rstrip().rstrip(";"))
ap=ex('attendPayload'); D='2026-11-10'; blk=ap['data'][D]

# 日块各层级法国区 unconfirmed
print("=== 日块 total ===", blk['total'])
det=[e for e in blk.get('detail',[]) if '法国区' in str(e.get('region',''))]
print("detail 法国区:",det)
whs=[e for e in blk.get('warehouse',[]) if '法国区' in str(e.get('region',''))]
print("warehouse 法国区 (6):")
for e in whs: print("   ",e.get('wh'),"unconfirmed=",e.get('unconfirmed'),"yqr=",e.get('yqr'),"sjqr=",e.get('sjqr'))
grps=[e for e in blk.get('group',[]) if '法国区' in str(e.get('region',''))]
print("group 法国区 (%d) unconfirmed合计=%d:"%(len(grps),sum(e.get('unconfirmed',0) for e in grps)))
for e in sorted(grps,key=lambda x:-x.get('unconfirmed',0)):
    print("   ",e.get('wh'),"/",e.get('group'),"unc=",e.get('unconfirmed'),"yqr=",e.get('yqr'),"sjqr=",e.get('sjqr'))

# empIndex 法国区11-10 按GK计数
emp_by_gk=Counter()
emp_gongs=defaultdict(list)
for gk,recs in ap['empIndex'].items():
    if '法国区' not in gk: continue
    for r in recs:
        if isinstance(r,list) and len(r)>3 and str(r[3])[:10]==D:
            emp_by_gk[gk]+=1
            emp_gongs[gk].append(str(r[1]))
print("\n=== empIndex 法国区11-10 按GK (%d条/%d组) ==="%(sum(emp_by_gk.values()),len(emp_by_gk)))
for gk,c in sorted(emp_by_gk.items(),key=lambda x:-x[1]):
    print("   ",c," ",gk)

# group节点 key -> unconfirmed
grp_key={f"{e.get('major')}|{e.get('region')}|{e.get('wh')}|{e.get('group')}":e.get('unconfirmed',0) for e in grps}
print("\n=== 差异：group节点unc vs empIndex行数 ===")
allk=set(grp_key)|set(emp_by_gk)
diffs=[]
for k in sorted(allk):
    gu=grp_key.get(k,0); ec=emp_by_gk.get(k,0)
    if gu!=ec:
        diffs.append((k,gu,ec,gu-ec))
        print("   DIFF",k,"group_unc=",gu,"emp_rows=",ec,"gap=",gu-ec)
print("差异组数:",len(diffs)," 差异合计:",sum(d[3] for d in diffs))

# 是否有非法国区group节点被误判
print("\n  group全部节点数:",len(blk.get('group',[]))," 法国区:",len(grps))
