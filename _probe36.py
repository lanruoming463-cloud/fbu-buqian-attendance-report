# -*- coding: utf-8 -*-
"""Probe36: 线上妙搭页面验证 —— release finished 后 T+1 tab 是否真实在线。
妙搭页面是壳（iframe/JS 渲染），直接 dump-dom 看初始 HTML + 探测资源 URL。
"""
import subprocess, re, sys
sys.stdout.reconfigure(encoding='utf-8')
URL = 'https://ztn.larkenterprise.com/page/RgGYm9pJkdaDGKafK8lc5pS1ntf?lang=zh-CN'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
p = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
                    '--virtual-time-budget=20000', URL],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
print('dom len:', len(dom))
for pat in ['secT1', 'T1_DATA', 'T+1确认率', 'viewT1', 'secAtt', '补签率']:
    print(pat, '->', dom.count(pat))
# 找页面标题
m = re.search(r'<title[^>]*>(.*?)</title>', dom, re.S)
print('title:', m.group(1)[:80] if m else 'NONE')
# 若为壳页面，找 iframe/JS 资源链接
for mm in re.finditer(r'(src|href)="(https?://[^"]{10,150})"', dom)[:0] if False else []:
    pass
srcs = re.findall(r'src="(https?://[^"]+)"', dom)[:5]
print('srcs:', srcs)
