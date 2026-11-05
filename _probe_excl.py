# -*- coding: utf-8 -*-
"""探针: 确认 4 条法国区正式工异常记录 在 formalAttPayload.empIndex 中存在, 并捕获修改前状态。
目标(来自截图):
  Huaiyue ZHANG zt0022449 2026-10-18 法国区 缺首打卡+未打卡
  Qianyi ZHU    zt0022048 2026-10-27 法国区 缺未打卡
  Qianyi ZHU    zt0022048 2026-10-28 法国区 缺首打卡+未打卡
  Yuqi LIU      zt0022580 2026-10-30 法国区 缺末打卡
"""
import json, re, os

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"

TARGETS = [
    ("zt0022449", "2026-10-18"),
    ("zt0022048", "2026-10-27"),
    ("zt0022048", "2026-10-28"),
    ("zt0022580", "2026-10-30"),
]

def extract(html, name):
    pre = "const %s = " % name; i = html.find(pre)
    if i < 0:
        pre = "var %s = " % name; i = html.find(pre)
    nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))

html = open(HTML, encoding='utf-8').read()
fp = extract(html, "formalAttPayload")
print("fp keys:", list(fp.keys()))
print("days count:", len(fp['days']), "末3:", fp['days'][-3:])

# 在 empIndex 中找命中
print("\n=== empIndex 命中扫描 ===")
hits = []
for gk, rows in fp['empIndex'].items():
    for row in rows:
        gong = str(row[1]).strip()
        ds = str(row[5]).strip()[:10]
        for (tg, td) in TARGETS:
            if gong == tg and ds == td:
                hits.append((gk, gong, ds, row))
                print("命中 gk=%s gong=%s ds=%s row[:13]=%s" % (gk, gong, ds, row[:13]))

print("\n命中总数:", len(hits))
if not hits:
    print("--- 按工号扫描(忽略日期) ---")
    for gk, rows in fp['empIndex'].items():
        for row in rows:
            gong = str(row[1]).strip()
            if gong in [t[0] for t in TARGETS]:
                print("  gk=%s gong=%s ds=%s row[:13]=%s" % (gk, gong, str(row[5]).strip()[:10], row[:13]))

# 修改前状态: 日块
print("\n=== 日块 untimely(修改前) ===")
for d in ("2026-10-18","2026-10-27","2026-10-28","2026-10-30"):
    if d in fp['data']:
        blk = fp['data'][d]
        print("  %s total.untimely=%s total.timely=%s" % (d, blk['total'].get('untimely'), blk['total'].get('timely')))

# 月块 2026-10 欧洲区|法国区
print("\n=== 月块 2026-10 欧洲区|法国区 (修改前) ===")
blk = fp['data']['2026-10']
print("  total.untimely=%s timely=%s" % (blk['total'].get('untimely'), blk['total'].get('timely')))
for e in blk.get('detail', []):
    if e.get('region') == '法国区':
        print("  detail 法国区: untimely=%s timely=%s total=%s" % (e.get('untimely'), e.get('timely'), e.get('total')))
