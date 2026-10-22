# -*- coding: utf-8 -*-
import re, json
HTML = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html"
html = open(HTML, encoding='utf-8').read()

def extract(name):
    pre = "const %s = " % name
    i = html.find(pre); nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))

fp = extract("formalAttPayload")
ap = extract("attendPayload")

print("=== 正式工白名单：zt0021580 @ 2026-10-19 应算及时确认(不出现在未及时明细) ===")
hit_f = 0
for gk, rows in fp.get('empIndex', {}).items():
    for r in rows:
        if r[1] == 'zt0021580' and r[-1] == '2026-10-19':
            hit_f += 1
print("  gen_emp_index 含 zt0021580/2026-10-19 条数(应为0):", hit_f)

print("=== 劳务工日期剔除：四位对应日期记录应完全消失 ===")
LABOR_EXCL = {
    'FR083014': '2026-10-19',
    'FR091493': '2026-10-18',
    'FR086719': '2026-10-14',
    'FR092791': '2026-10-14',
}
for gong, d in LABOR_EXCL.items():
    cnt = 0
    for gk, rows in ap.get('empIndex', {}).items():
        for r in rows:
            if r[1] == gong and r[-1] == d:
                cnt += 1
    print("  ap_empIndex 含 %s/%s 条数(应为0): %d" % (gong, d, cnt))

print("=== 离职剔除：zt0021903 10月全剔除(维持) ===")
hf = sum(1 for gk, rows in fp.get('empIndex', {}).items() for r in rows if r[1]=='zt0021903' and r[-1].startswith('2026-10'))
hl = sum(1 for gk, rows in ap.get('empIndex', {}).items() for r in rows if r[1]=='zt0021903' and r[-1].startswith('2026-10'))
print("  正式工 10月 empIndex 含 zt0021903:", hf, "| 劳务工 10月 empIndex 含 zt0021903:", hl)

print("=== Top10 未确认数>3 口径(维持) ===")
under_f = [(k, e['gong'], e['untimely']) for k, v in fp.get('topEmpIndexM', {}).get('2026-10', {}).items() for e in v if e.get('untimely',0)<=3]
under_l = [(k, e['gong'], e['unc']) for k, v in ap.get('topEmpIndexM', {}).get('2026-10', {}).items() for e in v if e.get('unc',0)<=3]
under_l3 = [(k, e['gong'], e['ldk']) for k, v in ap.get('topEmpIndexLdkM', {}).get('2026-10', {}).items() for e in v if e.get('ldk',0)<=3]
print("  正式工10月 topEmpIndexM 未确认<=3:", len(under_f))
print("  劳务工10月 topEmpIndexM(unc) 未确认<=3:", len(under_l))
print("  劳务工10月 topEmpIndexLdkM(ldk) 未确认<=3:", len(under_l3))

print("=== 月度合计(校验) ===")
print("  正式工 10月:", fp['data']['2026-10']['total'])
print("  劳务工 10月:", ap['data']['2026-10']['total'])
print("  days 末5:", fp['days'][-5:], "| attend days 末5:", ap['days'][-5:])
print("OK")
