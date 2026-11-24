# -*- coding: utf-8 -*-
"""T+1 注入前基线诊断 (2026-11-24): 三份源文件统计 + 当前 HTML payload 状态。"""
import os, json
import _inject_1025 as I25

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
FORMAL = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\11月\正式工-考勤记录-11.20-及时性.xlsx"
LA19   = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\11月\劳务工-考勤记录-11.19-及时性（仅洛杉矶19号仓）.xlsx"
LABOR  = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\11月\劳务工-考勤记录-11.20-及时性（不含洛杉矶19号仓）.xlsx"

def extract(html, name):
    pre = "const %s = " % name; i = html.find(pre)
    if i < 0:
        pre = "var %s = " % name; i = html.find(pre)
    nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))

html = open(HTML, encoding='utf-8').read()
fp = extract(html, 'formalAttPayload'); ap = extract(html, 'attendPayload')
print("HTML size:", os.path.getsize(HTML))
print("FORMAL days 末尾8:", fp['days'][-8:])
print("FORMAL 11月月块:", fp['data']['2026-11']['total'])
print("ATTEND days 末尾8:", ap['days'][-8:])
print("ATTEND 2026-11-19 存在?", '2026-11-19' in ap['data'])
print("ATTEND 2026-11-20 存在?", '2026-11-20' in ap['data'])
print()
for label, path in [('正式工11.20', FORMAL), ('LA19 11.19', LA19), ('非LA19 11.20', LABOR)]:
    print(label, "exists:", os.path.exists(path), "size:", os.path.getsize(path) if os.path.exists(path) else 0)

fr, fu = I25.build_formal_recs(FORMAL)
print("\n正式工11.20 行数:", len(fr), "未及时:", sum(r['untimely'] for r in fr), "日期:", sorted(set(r['date'] for r in fr)))
print("  zt0021853 命中行数(整条剔除后应=0):", sum(1 for r in fr if str(r['gong']).strip() == 'zt0021853'))

la, lu = I25.read_labor_recs(LA19, exclude_la19=False, read_only=False)
la = [r for r in la if r['wh'] == I25.LA19_WH]
print("\nLA19 11.19 行数:", len(la), "未确认:", sum(r['yqr'] - r['sjqr'] for r in la),
      "ldk:", sum(r['ldk'] for r in la), "日期:", sorted(set(r['date'] for r in la)))

lr, lunc = I25.read_labor_recs(LABOR, exclude_la19=True, read_only=True)
print("\n非LA19 11.20 行数:", len(lr), "未确认:", sum(r['yqr'] - r['sjqr'] for r in lr),
      "ldk:", sum(r['ldk'] for r in lr), "日期:", sorted(set(r['date'] for r in lr)))
print("  其中 LA19 行(应=0):", sum(1 for r in lr if r['wh'] == I25.LA19_WH))
