import re, json
html = open('补签流程_补签统计.html', encoding='utf-8').read()
# 提取 formalAttPayload JSON（在 const formalAttPayload = {...}; 内）
m = re.search(r'const formalAttPayload\s*=\s*(\{.*?\});', html, re.S)
payload = json.loads(m.group(1))
# 找欧洲区 major，遍历 detail 中 region=捷克区
maj = next(x for x in payload['major'] if x['name']=='欧洲区')
print('欧洲区(全月聚合) total=%d timely=%d untimely=%d 及时率=%.2f%%' % (
    maj['total'], maj['timely'], maj['untimely'], maj['timely']/maj['total']*100))
# detail 层找捷克区
cz = [x for x in payload.get('detail', []) if x.get('region')=='捷克区']
print('捷克区 detail 条数:', len(cz))
for x in cz[:5]:
    print('  ', x.get('major'), x.get('region'), 'total=%d timely=%d untimely=%d rate=%.2f%%' % (
        x['total'], x['timely'], x['untimely'], x['timely']/x['total']*100))
# 全量未确认核对
print('全表 total=%d untimely=%d' % (payload['total']['total'], payload['total']['untimely']))
