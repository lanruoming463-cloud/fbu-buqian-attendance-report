# -*- coding: utf-8 -*-
"""诊断 4 个探针失败项"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PATH = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58\补签流程_补签统计.html"
with open(PATH, 'r', encoding='utf-8') as f: h = f.read()

print("== A1: viewFormal 默认显示 ==")
i = h.find("id=\"viewFormal\"")
print(repr(h[max(0,i-160):i+120]))

print("\n== A6: 8月空态路径 ==")
i = h.find("t1RangeDays();")
seg = h[i:i+700]
print(seg.replace('\n', ' ⏎ ')[:700])

print("\n== A7: dd_9yue 选项文本 ==")
i = h.find("（日更中）")
print(h[max(0,i-200):i+150])

print("\n== EXC: showCell('formal','sign') 后 btnPicker/render ==")
i = h.find("if (curViewKey() === 'sign') { syncModeBtns(mode); renderPicker(); }")
print(h[max(0,i-300):i+200])
