# -*- coding: utf-8 -*-
"""看 sign render() 中 innerHTML 目标元素 + A9 EXC 复现路径"""
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PATH = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html"
with open(PATH, 'r', encoding='utf-8') as f: h = f.read()

i = h.find("function render() {\n  renderPicker();")
print("render() @", i)
print(h[i:i+2600])
