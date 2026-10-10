import re, sys
W = sys.__stdout__.write
p = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html'
html = open(p, encoding='utf-8').read()

# 逐个面板验证 div 平衡
for vid in ['viewFormal','viewAttend','viewGen','viewT1']:
    m = re.search(r'<div[^>]*id="%s"[^>]*>' % vid, html)
    i = m.start()
    depth = 0; end = -1
    for mm in re.finditer(r'<div\b|</div>', html[i:]):
        if mm.group(0).startswith('<div'): depth += 1
        else:
            depth -= 1
            if depth == 0: end = i + mm.end(); break
    inner = html[i:end]
    W("%s: len=%d tr=%d | contains genTitle=%s genCards=%s t1Kpis=%s\n" % (
        vid, len(inner), inner.count('<tr'),
        'id="genTitle"' in inner, 'id="genCards"' in inner, 'id="t1Kpis"' in inner))
W("END\n")
