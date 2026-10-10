import re, sys
W = sys.__stdout__.write
html = open('C:/tmp/after_fix.html', encoding='utf-8', errors='replace').read()
# T1 是懒渲染：showCell('t1','T1') 时才填充。模拟点击 tab：执行 t1Show 后 dump 不可行，
# 但可以检查 t1Show 函数与数据在位：window.__T1_DATA__ / t1Render 调用链
for marker in ['__T1_DATA__','t1Show','t1Render','T1_DATA_OK','const __T1__']:
    W("%s: %d\n" % (marker, html.count(marker)))
# 检查 tab 按钮与 onclick
m = re.search(r'<button[^>]*onclick="[^"]*T1[^"]*"[^>]*>[^<]*<[^>]*>[^<]*', html)
W("T1 tab: %s\n" % (m.group(0)[:150] if m else 'N/A'))
W("END\n")
