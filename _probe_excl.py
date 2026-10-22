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
TARGET = "zt0021903"
print("=== 正式工考勤确认率 (formalAttPayload) ===")
# empIndex 组角标明细
bad_emp = 0
for gk, rows in fp.get('empIndex', {}).items():
    for r in rows:
        if len(r) >= 14 and r[13].startswith('2026-10') and r[1] == TARGET:
            bad_emp += 1
print("  10月 empIndex 含 zt0021903 条数:", bad_emp)
# topEmpIndexM 2026-10
tm = fp.get('topEmpIndexM', {}).get('2026-10', {})
cnt = sum(len(v) for v in tm.values())
under = [(k, e['gong'], e['untimely']) for k, v in tm.items() for e in v if e.get('untimely', 0) <= 3]
hit = [(k, e['gong']) for k, v in tm.items() for e in v if e.get('gong') == TARGET]
print("  10月 topEmpIndexM 条目数:", cnt, "| 未确认数<=3 条数:", len(under), "| 含zt0021903:", len(hit))
# topEmpIndex 累计(2026-10 也在此)
tc = fp.get('topEmpIndex', {})
hit2 = [(k, e['gong']) for k, v in tc.items() for e in v if e.get('gong') == TARGET]
# 抽查欧洲区/西班牙区
for rg in ('欧洲区|西班牙区',):
    print("  欧洲区|西班牙区 topEmpIndex 人数:", len(tc.get(rg, [])))
print("  累计 topEmpIndex 含zt0021903:", len(hit2))

print("=== 劳务工考勤确认率 (attendPayload) ===")
# empIndex
bad_emp_l = 0
for gk, rows in ap.get('empIndex', {}).items():
    for r in rows:
        if len(r) >= 11 and r[10].startswith('2026-10') and r[1] == TARGET:
            bad_emp_l += 1
print("  10月 empIndex 含 zt0021903 条数:", bad_emp_l)
# topEmpIndexM unc
tm2 = ap.get('topEmpIndexM', {}).get('2026-10', {})
cnt2 = sum(len(v) for v in tm2.values())
under2 = [(k, e['gong'], e['unc']) for k, v in tm2.items() for e in v if e.get('unc', 0) <= 3]
hit_l = [(k, e['gong']) for k, v in tm2.items() for e in v if e.get('gong') == TARGET]
print("  10月 topEmpIndexM(unc) 条目数:", cnt2, "| 未确认数<=3:", len(under2), "| 含zt0021903:", len(hit_l))
# topEmpIndexLdkM ldk
tm3 = ap.get('topEmpIndexLdkM', {}).get('2026-10', {})
under3 = [(k, e['gong'], e['ldk']) for k, v in tm3.items() for e in v if e.get('ldk', 0) <= 3]
hit_l3 = [(k, e['gong']) for k, v in tm3.items() for e in v if e.get('gong') == TARGET]
print("  10月 topEmpIndexLdkM(ldk) 条目数:", sum(len(v) for v in tm3.values()), "| ldk<=3:", len(under3), "| 含zt0021903:", len(hit_l3))

print("=== 10月合计(校验) ===")
print("  正式工 10月:", fp['data']['2026-10']['total'])
print("  劳务工 10月 unconfirmed:", ap['data']['2026-10']['total'].get('unconfirmed'))
print("  days 末5:", fp['days'][-5:], "| attend days 末5:", ap['days'][-5:])
