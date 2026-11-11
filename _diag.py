# -*- coding: utf-8 -*-
import json, re
PREFIX='const formalAttPayload = '
def extract(h,n):
    i=h.find(n);j=h.find('\n',i);return json.loads(h[i+len(n):j].rstrip(';'))
def load(p):return extract(open(p,encoding='utf-8').read(),PREFIX)
new=load('补签流程_补签统计.html')
def wh_match(a,b):
    a=re.sub(r'[（(].*?[)）]','',a or '').strip();b=re.sub(r'[（(].*?[)）]','',b or '').strip()
    if not a or not b:return False
    return a==b or a in b or b in a
# 在 day 2026-10-30 的 warehouse 中，哪些条目会被 wh_match('伯明翰23号仓') 命中？
day=new['data']['2026-10-30']
print("day 2026-10-30 warehouse entries matched by '伯明翰23号仓':")
for e in day.get('warehouse',[]):
    if wh_match('伯明翰23号仓', e.get('wh','')):
        print("   MATCH wh=%r maj=%r reg=%r untimely=%s"%(e.get('wh'),e.get('major'),e.get('region'),e.get('untimely')))
# group: 在 day 2026-10-30 中，gmap 会纳入哪些 group（按 wh_day_contrib 逻辑）
w_entries=[e for e in day.get('warehouse',[]) if wh_match('伯明翰23号仓',e.get('wh',''))]
print("\n对应 gmap 将纳入的 group (wh,group):")
seen=set()
for g in day.get('group',[]):
    if any(e.get('major')==g.get('major') and e.get('region')==g.get('region') and wh_match('伯明翰23号仓',e.get('wh','')) for e in w_entries):
        if (g.get('wh'),g.get('group')) not in seen:
            seen.add((g.get('wh'),g.get('group')))
            print("   wh=%r group=%r"%(g.get('wh'),g.get('group')))
