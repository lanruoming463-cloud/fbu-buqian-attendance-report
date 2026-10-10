import re, json
html = open('补签流程_补签统计.html', encoding='utf-8').read()
m = re.search(r'const formalAttPayload\s*=\s*(\{.*?\});', html, re.S)
payload = json.loads(m.group(1))
months = payload['months']

# 跨月份聚合 major / HRBP region
major_agg = {}
hrbp_regions = {}
for mk in months:
    blk = payload['data'][mk]
    tot = blk['total']
    for x in blk.get('major', []):
        nm = x['name']
        d = major_agg.setdefault(nm, {'total':0,'untimely':0,'timely':0})
        d['total']+=x['total']; d['untimely']+=x['untimely']; d['timely']+=x['timely']
    for x in blk.get('detail', []):
        if x['major']=='FBU HRBP Dept.':
            hrbp_regions[x['region']] = hrbp_regions.get(x['region'],0)+x['total']

print('月份:', months)
print('=== 大区汇总(全月) ===')
for nm,d in sorted(major_agg.items(), key=lambda kv:-kv[1]['total']):
    print(f"  {nm:20s} 总={d['total']:6d} 未及时={d['untimely']:5d} 及时率={d['timely']/d['total']*100:.2f}%")
print('=== HRBP 各区域 ===')
for rg,c in sorted(hrbp_regions.items(), key=lambda kv:-kv[1]):
    print(f"  {rg:20s} {c}")
# 检查是否还有 其他 / 支持 / 国内
print('含"其他"大区?', '其他' in major_agg)
bad = [rg for rg in hrbp_regions if ('支持' in rg) or ('国内' in rg)]
print('HRBP 仍含 支持/国内 组?', bad)
