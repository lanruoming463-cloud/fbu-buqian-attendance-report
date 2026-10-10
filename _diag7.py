# -*- coding: utf-8 -*-
"""S1 之谜最后一步：viewFormal 的 CSS 规则与 hidden class 逻辑"""
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PATH = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html"
with open(PATH, 'r', encoding='utf-8') as f: h = f.read()

# view-panel 基础规则
for m in re.finditer(r'\.view-panel[^{,]*\{[^}]*\}', h):
    print(m.group(0)[:150])

# showCell 全文（重点：showFormal/showAtt/showGen 组合 + hidden class 操作）
i = h.find("function showCell(wt, sec) {")
print("\n" + h[i:i+1500])
