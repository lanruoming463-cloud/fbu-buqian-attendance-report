import json
def ext(h,n):
    i=h.find('const '+n+' = ');j=h.find('\n',i);return json.loads(h[i+len('const '+n+' = '):j].rstrip(';'))
h=open('补签流程_补签统计.html',encoding='utf-8').read()
for name in ('formalAttPayload','attendPayload','formalPayload','laborPayload'):
    try:
        P=ext(h,name)
    except Exception as e:
        print(name,'parse fail',e);continue
    al=P.get('allEmp')
    print('====',name,'====')
    print('  allEmp 条数:', len(al) if al is not None else 'N/A(无此字段)')
    # empIndex 总行数 与 最大键
    ei=P.get('empIndex')
    if ei:
        tot=sum(len(v) for v in ei.values()); mx=max(ei.items(),key=lambda x:len(x[1]))
        print('  empIndex 键数=%d 总行数=%d  最大键=%s(%d行)'%(len(ei),tot,mx[0],len(mx[1])))
    print('  data 日块数:', len([k for k in P.get('data',{}) if len(k)<=10]))
