# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
html = open('补签流程_补签统计.html', encoding='utf-8').read()
print('HTML size:', len(html))
for pat in ['secAcc', 'secAtt', 'secSign', 'wtFormal', 'wtLabor',
            'viewFormal', 'viewGen', 'viewAttend',
            '考勤确认及时率', '补签率', '考勤准确率',
            'empIndex', 'topEmpIndex', 'globalControls', 'FBU交付前台']:
    print(pat, html.count(pat))
