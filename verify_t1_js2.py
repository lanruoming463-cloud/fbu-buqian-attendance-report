import re, sys
W = sys.__stdout__.write
html = open('C:/tmp/after_fix.html', encoding='utf-8', errors='replace').read()
# 提取 t1Show 函数体看数据从哪来
m = re.search(r'function t1Show\(\)\s*\{(.{0,800})', html, re.S)
W("t1Show body:\n%s\n---\n" % m.group(1)[:600] if m else "t1Show N/A\n")
# T1 数据常量名
m2 = re.search(r'const (t1[A-Za-z_]*Data|T1[A-Za-z_]*)\s*=', html)
W("T1 data const: %s\n" % (m2.group(1) if m2 else 'N/A'))
W("END\n")
