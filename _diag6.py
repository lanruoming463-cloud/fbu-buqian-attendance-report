# -*- coding: utf-8 -*-
"""S1_defaultDisplay=none 诊断：页面加载后谁把 viewFormal 藏了？"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PATH = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html"
with open(PATH, 'r', encoding='utf-8') as f: h = f.read()

# 1. viewFormal 是否有内联 display
i = h.find('id="viewFormal"')
print("tag:", h[max(0,i-60):i+60])

# 2. view-panel 的 CSS
j = h.find('.view-panel')
print("\ncss:", h[j:j+200])

# 3. 初始化调用（script 底部的启动逻辑）
import re
for m in re.finditer(r'showCell\(', h):
    s = max(0, m.start()-120)
    print("\n--- showCell call @", m.start(), "---")
    print(h[s:m.end()+160].replace('\n', ' ⏎ '))
