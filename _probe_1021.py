# -*- coding: utf-8 -*-
import re, json
HTML = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html"
html = open(HTML, encoding='utf-8').read()
def extract(name):
    pre = "const %s = " % name
    i = html.find(pre); nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))
fp = extract("formalAttPayload"); ap = extract("attendPayload")

print("=== 10.21 日块存在性 ===")
print("  fp['days'] 含 2026-10-21:", '2026-10-21' in fp['days'], "| 末6:", fp['days'][-6:])
print("  ap['days'] 含 2026-10-21:", '2026-10-21' in ap['days'], "| 末6:", ap['days'][-6:])
print("  正式工 day 2026-10-21:", fp['data'].get('2026-10-21', {}).get('total'))
print("  劳务工 day 2026-10-21 unconfirmed:", ap['data'].get('2026-10-21', {}).get('total', {}).get('unconfirmed'))

print("=== 10月月块(更新后) ===")
print("  正式工 10月:", fp['data']['2026-10']['total'])
print("  劳务工 10月(无月块键,跳过)")

print("=== 历史白名单/剔除仍生效 ===")
# zt0021580 @ 2026-10-19 应=0
hit_f = sum(1 for gk, rows in fp.get('empIndex', {}).items() for r in rows if r[1]=='zt0021580' and r[-1]=='2026-10-19')
print("  gen_emp_index 含 zt0021580/2026-10-19(应0):", hit_f)
# 四位劳务工对应剔除日期 应=0
LABOR_EXCL = {('FR083014','2026-10-19'),('FR091493','2026-10-18'),('FR086719','2026-10-14'),('FR092791','2026-10-14')}
for gong,d in LABOR_EXCL:
    c = sum(1 for gk, rows in ap.get('empIndex', {}).items() for r in rows if r[1]==gong and r[-1]==d)
    print("  ap_emp_index 含 %s/%s(应0): %d" % (gong,d,c))
# zt0021903 10月 应=0（两处）
hf = sum(1 for gk, rows in fp.get('empIndex', {}).items() for r in rows if r[1]=='zt0021903' and r[-1].startswith('2026-10'))
hl = sum(1 for gk, rows in ap.get('empIndex', {}).items() for r in rows if r[1]=='zt0021903' and r[-1].startswith('2026-10'))
print("  zt0021903 10月: 正式工=%d 劳务工=%d (应0)" % (hf, hl))

print("=== 10.21 劳务工无异常剔除(全量计入校验) ===")
# 10.21 文件 8292 行全为 10-21 且 yqr=8292 -> 无被 LABOR_ATT_EXCLUDE_DATES 误剔(剔除日期均非10-21)
print("  劳务工 day 2026-10-21 yqr:", ap['data']['2026-10-21']['total']['yqr'])

print("=== Top10 未确认数>3 口径维持 ===")
uf = [(k,e['gong'],e['untimely']) for k,v in fp.get('topEmpIndexM',{}).get('2026-10',{}).items() for e in v if e.get('untimely',0)<=3]
ul = [(k,e['gong'],e['unc']) for k,v in ap.get('topEmpIndexM',{}).get('2026-10',{}).items() for e in v if e.get('unc',0)<=3]
uld = [(k,e['gong'],e['ldk']) for k,v in ap.get('topEmpIndexLdkM',{}).get('2026-10',{}).items() for e in v if e.get('ldk',0)<=3]
print("  正式工10月 topEmpIndexM 未确认<=3:", len(uf), "| 劳务工 unc<=3:", len(ul), "| ldk<=3:", len(uld))

print("=== noteHtml 日期范围已更新 ===")
print("  formal 含 '10.1–10.21':", '10.1–10.21' in fp['noteHtml'], "| 含 10.21文件:", '正式工-考勤记录-10.21-及时性.xlsx' in fp['noteHtml'])
print("  labor  含 '10.1–10.21':", '10.1–10.21' in ap['noteHtml'], "| 含 10.21文件:", '劳务工-考勤记录-10.21-及时性' in ap['noteHtml'])
print("OK")
