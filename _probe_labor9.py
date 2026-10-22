# -*- coding: utf-8 -*-
import json, re
html = open('补签流程_补签统计.html', encoding='utf-8').read()
dec = json.JSONDecoder()
m = re.search(r'laborPayload\s*=\s*', html)
obj, _ = dec.raw_decode(html[m.end():].lstrip())
print("months:", obj['months'])
md = obj['data']
for ym in obj['months']:
    b = md[ym]
    print(ym, "total=%s done=%s rate=%s" % (b['total'], b['done'], b['rate']))
# 西班牙区 9月
sep = md['2026-09']
sp = [d for d in sep['detail'] if d['region'] == '西班牙区']
print("\n9月 西班牙区 detail:", sp)
jp = [d for d in sep['detail'] if d['region'] == '日本区']
print("9月 日本区 detail:", jp)
# 西班牙区 8月 对比
aug = md['2026-08']
sp8 = [d for d in aug['detail'] if d['region'] == '西班牙区']
print("8月 西班牙区 detail:", sp8)
# 9月 Top10 西班牙区
top9 = obj['topEmpIndexM'].get('2026-09', {})
print("\n9月 topEmpIndexM 西班牙区:", top9.get('欧洲区|西班牙区', 'EMPTY'))
# noteHtml 含新文案
print("\nnote 含'9月新口径':", '9月新口径' in obj['noteHtml'], "| 含'西班牙区 补签原因=其他':", '西班牙区 补签原因=其他' in obj['noteHtml'])
# fDays 检查（T+1 注入后应有 10.16-10.20）——注入前应只有源文件范围
mf = re.search(r'formalAttPayload\s*=\s*', html)
if mf:
    fo, _ = dec.raw_decode(html[mf.end():].lstrip())
    print("\nformal months:", fo.get('months'), "| days 数:", len(fo.get('days', [])), "| 末3天:", fo.get('days', [])[-3:])
