# -*- coding: utf-8 -*-
"""探针 v29：月度切换后角标联动 + 表头样式 + 按月过滤展开行"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8954

os.chdir(WS)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

PROBE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body><pre id="out">PENDING</pre>
<iframe id="f" src="/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html" style="width:1400px;height:900px"></iframe>
<script>
var results = {};
function qa(sel){ return Array.from(document.getElementById('f').contentDocument.querySelectorAll(sel)); }
function ev(code){ return document.getElementById('f').contentWindow.eval(code); }
function click(el){ el.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
function badgeInfo(){
  return qa('#genGrpBody tr.att-grp').map(function(r){
    var b = r.querySelector('.emp-count');
    if (!b) return null;
    var m = b.textContent.match(/(\\d+)/);
    return { row: r, cnt: m ? parseInt(m[1],10) : -1 };
  }).filter(Boolean);
}
function step1(){
  try {
    // 切到 2026-06
    ev('genSel = "2026-06"; renderGen(genPayload);');
    var info = badgeInfo();
    results.jun_posBadged = info.filter(function(x){ return x.cnt > 0; }).length;
    results.jun_zeroBadged = info.filter(function(x){ return x.cnt === 0; }).length;
    info.sort(function(a,b){ return b.cnt - a.cnt; });
    results.jun_top = { cnt: info[0].cnt, key: ['major','region','wh','group'].map(function(a){ return info[0].row.getAttribute('data-'+a); }).join('|') };
    // 展开top组，检查行数 = cnt，且所有考勤日期都是6月
    click(info[0].row.querySelector('td'));
    var sub = info[0].row.nextElementSibling;
    var et = sub.querySelector('table.emp-table');
    var dataRows = Array.from(et.querySelectorAll('tbody tr')).filter(function(tr){ return tr.querySelector('td'); });
    results.jun_dataRows = dataRows.length;
    results.jun_allJune = dataRows.every(function(tr){ return tr.querySelectorAll('td')[5].textContent.indexOf('2026-06') === 0; });
    results.jun_sampleRow = dataRows.slice(0,2).map(function(tr){ return Array.from(tr.querySelectorAll('td')).map(function(e){ return e.textContent; }); });
    // 表头样式（th 背景色应为 #eef4fb = rgb(238, 244, 251)）
    var th = et.querySelector('th');
    results.thBg = th ? getComputedStyle(th).backgroundColor : 'NO_TH';
    click(info[0].row.querySelector('td'));
  } catch(e) { results.EXC = String(e && e.stack || e); }
  document.getElementById('out').textContent = '@@P29@@' + JSON.stringify(results) + '@@P29END@@';
}
setTimeout(step1, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe29.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe29.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
m = re.search(r'@@P29@@(.*?)@@P29END@@', dom, re.S)
if m:
    print(m.group(1)[:3500])
else:
    print('NO MARKER')
httpd.shutdown()
