import re
path = r'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html'
html = open(path, encoding='utf-8', errors='ignore').read()
print("文件大小(字符):", len(html))

print("子串 '2026-10' 出现次数:", html.count('2026-10'))
print("子串 '2026-09' 出现次数:", html.count('2026-09'))
print("子串 '2026-08' 出现次数:", html.count('2026-08'))

for tag in ('formalAtt', 'laborAtt'):
    i = html.find('"type":"%s"' % tag)
    if i < 0:
        print("[%s] 未找到 type" % tag)
        continue
    j = html.find('"months":', i)
    k = html.find(']', j)
    print("[%s] months = %s" % (tag, html[j:k+1]))

i = html.find('"type":"formalAtt"')
seg = html[i:i+400000]
print("formalAtt 段内 '2026-10' 次数:", seg.count('2026-10'))
i2 = html.find('"type":"laborAtt"')
seg2 = html[i2:i2+400000]
print("laborAtt 段内 '2026-10' 次数:", seg2.count('2026-10'))
print("DONE")
