import re, sys
W = sys.__stdout__.write
# 在源 HTML 里验证 T1_DATA 定义存在且完整（JSON 可解析）
p = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html'
html = open(p, encoding='utf-8').read()
m = re.search(r'const\s+T1_DATA\s*=\s*(\{.*?\});\s*\n', html, re.S)
if not m:
    m = re.search(r'T1_DATA\s*=\s*(\{.*?\})\s*;', html, re.S)
W("T1_DATA found: %s\n" % bool(m))
if m:
    import json
    try:
        d = json.loads(m.group(1))
        W("JSON valid. updated=%s cutoff=%s months=%d days=%d\n" % (d.get('updated'), d.get('cutoff'), len(d.get('months',[])), len(d.get('days',[]))))
    except Exception as e:
        W("JSON ERROR: %s\n" % e)
        W("snippet: %r\n" % m.group(1)[:300])
# showCell 里 T1 隐藏逻辑
m2 = re.search(r'function showCell\([^)]*\)\s*\{.{0,600}', html, re.S)
if m2:
    body = m2.group(0)
    W("showCell mentions viewT1: %s\n" % ('viewT1' in body))
W("END\n")
