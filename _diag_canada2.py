# -*- coding: utf-8 -*-
import json, re
WS = r"C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
html = open(HTML, encoding='utf-8').read()
def extract(name):
    pre = "const %s = " % name; i = html.find(pre); nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))
fp = extract("formalAttPayload")
EXCL = {'卡尔加里1号仓','温哥华2号仓','温哥华3号仓'}
print("days(Nov):", [d for d in fp['days'] if d>='2026-11-01'])
print("has 2026-11:", '2026-11' in fp['data'])
# month block warehouse entries for excluded wh
mb = fp['data']['2026-11']
print("\n=== 2026-11 month block total ===", mb['total'])
for lvl in ('warehouse','group'):
    hits = [e for e in mb[lvl] if e.get('wh') in EXCL or (e.get('region')=='加拿大区' and any(w in str(e) for w in EXCL))]
    print(f"-- month {lvl} entries (wh in EXCL): {len(hits)}")
    for e in hits:
        print("   ", {k:e[k] for k in ('major','region','wh','group','total','normal','abnormal','untimely') if k in e})
# day blocks
for d in [x for x in fp['days'] if '2026-11-0' in x or x in ('2026-11-01',)]:
    pass
for d in sorted([x for x in fp['days'] if x>='2026-11-01']):
    blk = fp['data'][d]
    hits=[e for e in blk.get('warehouse',[]) if e.get('wh') in EXCL]
    if hits:
        print(f"\n-- day {d} total:", blk['total'])
        for e in hits:
            print("   wh:", {k:e[k] for k in ('region','wh','group','total','normal','abnormal','untimely') if k in e})
# empIndex gks 加拿大区
print("\n=== empIndex 加拿大区 gks ===")
ck=[gk for gk in fp['empIndex'] if '加拿大区' in gk]
print("count:", len(ck))
excl_gks=[gk for gk in ck if any(w in gk for w in EXCL)]
print("excl wh gks:", len(excl_gks))
# count rows in excl gks with date 11.1-11.8
rc=0
for gk in excl_gks:
    for r in fp['empIndex'][gk]:
        if '2026-11-0' in str(r[-1]) or '2026-11-1' in str(r[-1]):
            rc+=1
print("excl rows (Nov 1-8):", rc)
# top
print("\n=== topEmpIndex keys with 加拿大区 ===", [k for k in fp['topEmpIndex'] if '加拿大区' in k])
for k in [x for x in fp['topEmpIndex'] if '加拿大区' in x]:
    print("  ", k, "->", [(e.get('gong'),e.get('wh'),e.get('group'),e.get('untimely')) for e in fp['topEmpIndex'][k]])
print("topEmpIndexM 2026-11 keys 加拿大区:", [k for k in fp['topEmpIndexM'].get('2026-11',{}) if '加拿大区' in k])
if '2026-11' in fp['topEmpIndexM']:
    for k in [x for x in fp['topEmpIndexM']['2026-11'] if '加拿大区' in x]:
        print("  M", k, "->", [(e.get('gong'),e.get('wh'),e.get('group'),e.get('untimely')) for e in fp['topEmpIndexM']['2026-11'][k]])
