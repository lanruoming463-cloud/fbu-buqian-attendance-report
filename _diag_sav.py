# -*- coding: utf-8 -*-
import json, re
def ext(h,n):
    i=h.find('const '+n+' = ');j=h.find('\n',i);return json.loads(h[i+len('const '+n+' = '):j].rstrip(';'))
h=open('补签流程_补签统计.html',encoding='utf-8').read()
for name in ('formalAttPayload','attendPayload'):
    P=ext(h,name)
    print('====',name,'====')
    # empIndex keys 含 萨凡纳 的：列出 键 -> 行数
    sav={}
    for k,rows in P.get('empIndex',{}).items():
        if '萨凡纳' in k:
            sav[k]=len(rows)
    print('  萨凡纳 empIndex 键数=%d, 总行数=%d'%(len(sav),sum(sav.values())))
    # 找最大的几个
    top=sorted(sav.items(),key=lambda x:-x[1])[:8]
    for k,v in top: print('    %s -> %d 行'%(k,v))
    # 施文 出现在哪些 empIndex 行
    print('  含 施文 的 empIndex 行:')
    cnt=0
    for k,rows in P.get('empIndex',{}).items():
        for r in rows:
            name_field = r[0] if len(r)>0 else ''
            if '施文' in str(name_field):
                cnt+=1
                if cnt<=10:
                    print('    key=%s row=%s'%(k, r[:4]))
    print('  施文 命中行数=%d'%cnt)
