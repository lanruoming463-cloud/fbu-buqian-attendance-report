# -*- coding: utf-8 -*-
"""审计线上 index.html 的所有 <script> 块：配对、大小、逐块语法检查"""
import re, io, sys, subprocess, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
p = os.path.join(WS, '_md_repo_deploy', 'index.html')
html = open(p, encoding='utf-8').read()
print('total bytes:', len(html))

opens = [m for m in re.finditer(r'<script\b[^>]*>', html)]
closes = [m for m in re.finditer(r'</script\s*>', html)]
print('script opens:', len(opens), '| closes:', len(closes))
for m in opens[:20]:
    print('  open@%d: %s' % (m.start(), m.group(0)[:90]))

# 逐块提取（忽略嵌套风险，按顺序配对）
nodes = sorted([(m.start(), 'o', m.group(0)) for m in opens] + [(m.start(), 'c', '') for m in closes])
depth = 0; blocks = []; cur = None
for pos, kind, tag in nodes:
    if kind == 'o':
        if depth == 0:
            cur = {'start': pos, 'tag': tag}
        depth += 1
    else:
        depth -= 1
        if depth == 0 and cur is not None:
            cur['end'] = pos
            blocks.append(cur); cur = None
print('paired blocks:', len(blocks))
NODE = None
for c in [r'C:\Program Files\nodejs\node.exe',
          r'C:\Users\zt25337\.workbuddy\binaries\node\cli-connector-packages\node\node.exe',
          r'C:\Users\zt25337\.workbuddy\binaries\node\node.exe']:
    if os.path.exists(c): NODE = c; break
print('node:', NODE)
for i, b in enumerate(blocks):
    inner_s = b['start'] + len(b['tag'])
    inner = html[inner_s:b['end']]
    has_src = 'src=' in b['tag']
    print('block#%d @%d len=%d src=%s | head: %r' % (i, b['start'], len(inner), has_src, inner.strip()[:60]))
    if not has_src and len(inner) > 10:
        f = os.path.join(WS, '_blockchk.js')
        open(f, 'w', encoding='utf-8').write(inner)
        r = subprocess.run([NODE, '--check', f], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        print('   syntax:', 'OK' if r.returncode == 0 else 'FAIL -> ' + (r.stderr or '')[:400])
