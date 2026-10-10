import re, sys
W = sys.__stdout__.write
p = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html'
html = open(p, encoding='utf-8').read()

i_gen = html.find('<div class="view-panel" id="viewGen"')
i_t1  = html.find('<div class="view-panel" id="viewT1"')

# viewT1 块：从 i_t1 到 </div>\n<div class="header">\n<h1 id="genTitle"> 的 </div> 结束
m_end = re.search(r'</div>\s*\n<div class="header">\s*\n<h1 id="genTitle">', html[i_t1:])
t1_block = html[i_t1 : i_t1 + m_end.start()]  # 不含结尾的 </div>? re.match 到 </div> 起
# m_end.start() 指向 '</div>' 开始，即 viewT1 的收尾 </div> 已包含在块内
t1_block = html[i_t1 : i_t1 + m_end.start() + len('</div>')]
W("t1_block len %d, head %r..., tail %r\n" % (len(t1_block), t1_block[:60], t1_block[-80:]))

# 1) 从原位置删除整个 viewT1 块
html2 = html[:i_t1] + html[i_t1 + len(t1_block):]

# 2) 重新计算 viewGen 面板在 html2 中的结束位置（div 深度扫描）
depth = 0
viewgen_end = -1
for m in re.finditer(r'<div\b|</div>', html2[i_gen:]):
    if m.group(0).startswith('<div'):
        depth += 1
    else:
        depth -= 1
        if depth == 0:
            viewgen_end = i_gen + m.end()
            break
W("viewGen ends at %d; after: %r\n" % (viewgen_end, html2[viewgen_end:viewgen_end+80]))

# 3) 在 viewGen 面板结束后插入 viewT1 块（前置换行保持格式）
html3 = html2[:viewgen_end] + '\n' + t1_block + html2[viewgen_end:]

# 4) 验证：genCards 应在 viewGen 内、viewT1 内无 genTitle
ok1 = html3.find('<div class="view-panel" id="viewGen"') < html3.find('id="genCards"') < html3.find('<div class="view-panel" id="viewT1"')
W("order check (viewGen < genCards < viewT1): %s\n" % ok1)

# 5) div 平衡校验（全文件）
opens = len(re.findall(r'<div\b', html3)); closes = html3.count('</div>')
W("div balance: opens=%d closes=%d diff=%d\n" % (opens, closes, opens-closes))

# 6) 写回
open(p, 'w', encoding='utf-8').write(html3)
W("written %d chars\n" % len(html3))
W("END\n")
