import re, json
data = open('补签流程_补签统计.html', encoding='utf-8').read()
print("total bytes:", len(data.encode('utf-8')))
names = ['formalAttPayload','attendPayload','formalPayload','laborPayload']
for nm in names:
    m = re.search(r'const\s+'+re.escape(nm)+r'\s*=\s*', data)
    if not m:
        print(nm, "NOT FOUND"); continue
    i = data.index('{', m.end())
    depth=0; j=i
    instr=False; esc=False; ch=None
    for k in range(i, len(data)):
        c=data[k]
        if instr:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c==ch: instr=False
        else:
            if c in '"\'`': instr=True; ch=c
            elif c=='{': depth+=1
            elif c=='}':
                depth-=1
                if depth==0: j=k; break
    blob = data[i:j+1]
    print(f"\n=== {nm}: bytes={len(blob.encode('utf-8'))} ({len(blob.encode('utf-8'))/1024/1024:.2f} MB) ===")
    # key-level stats via json
    try:
        obj=json.loads(blob)
        def walk(o, prefix=''):
            if isinstance(o, dict):
                for k,v in o.items():
                    if isinstance(v,(dict,list)): walk(v, prefix+'.'+str(k))
        # count allEmp
        for key in ('allEmp',):
            if key in obj and isinstance(obj[key], list):
                print(f"  {key}: {len(obj[key])} records")
        if 'empIndex' in obj and isinstance(obj['empIndex'], dict):
            rows=sum(len(v) for v in obj['empIndex'].values())
            print(f"  empIndex: {len(obj['empIndex'])} keys, {rows} rows")
        if 'data' in obj and isinstance(obj['data'], dict):
            print(f"  data months: {list(obj['data'].keys())}")
        if 'topEmpIndex' in obj and isinstance(obj['topEmpIndex'], dict):
            te=sum(len(v) for v in obj['topEmpIndex'].values())
            print(f"  topEmpIndex: {len(obj['topEmpIndex'])} regions, {te} entries")
    except Exception as e:
        print("  (json parse error:", e, ")")
