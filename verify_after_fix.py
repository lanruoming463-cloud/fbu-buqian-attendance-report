import re, sys
W = sys.__stdout__.write
html = open('C:/tmp/after_fix.html', encoding='utf-8', errors='replace').read()
W("dump len %d\n" % len(html))
for vid in ['viewFormal','viewAttend','viewGen','viewT1']:
    m = re.search(r'<div[^>]*id="%s"[^>]*>' % vid, html)
    if not m: W("%s NOT FOUND\n" % vid); continue
    seg = html[m.start():]
    nxt = re.search(r'<div[^>]*id="view[A-Z]', seg[20:])
    blk = seg[:20+nxt.start()] if nxt else seg[:100000]
    txt = re.sub(r'<[^>]+>', '', blk)
    W("%s: rows=%d vis=%d | first40=%s\n" % (vid, blk.count('<tr'), len(txt.strip()), txt.strip()[:40].encode('unicode_escape').decode()[:120]))
# KPI 数字在渲染后的位置（应在 viewGen 块内）
i_cards = html.find('id="genCards"')
i_gen = html.find('id="viewGen"')
i_t1 = html.find('id="viewT1"')
W("order: viewGen(%d) < genCards(%d) < viewT1(%d): %s\n" % (i_gen, i_cards, i_t1, i_gen < i_cards < i_t1))
W("kpi 49,854 present: %d | 美洲区 present: %d\n" % (html.count('>49,854<'), html.count('美洲区')))
W("END\n")
