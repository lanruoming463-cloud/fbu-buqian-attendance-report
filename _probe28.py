# -*- coding: utf-8 -*-
"""探针 v28：检查展开 emp-table 的行结构异常（46行/首行无td）"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8953

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
function click(el){ el.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
function step1(){
  try {
    var grpRows = qa('#genGrpBody tr.att-grp');
    var info = grpRows.map(function(r){
      var b = r.querySelector('.emp-count');
      if (!b) return null;
      var m = b.textContent.match(/(\\d+)/);
      return { row: r, cnt: m ? parseInt(m[1],10) : -1 };
    }).filter(Boolean).filter(function(x){ return x.cnt > 0; });
    info.sort(function(a,b){ return b.cnt - a.cnt; });
    var b0 = info[0];
    click(b0.row.querySelector('td'));
    var sub = b0.row.nextElementSibling;
    var et = sub.querySelector('table.emp-table');
    var trs = Array.from(et.querySelectorAll('tbody tr'));
    results.trCount = trs.length;
    results.firstTwoHTML = trs.slice(0,2).map(function(tr){ return tr.outerHTML.slice(0, 400); });
    results.lastHTML = trs[trs.length-1].outerHTML.slice(0, 400);
    results.tbodyCount = et.querySelectorAll('tbody').length;
    results.theadCount = et.querySelectorAll('thead').length;
  } catch(e) { results.EXC = String(e && e.stack || e); }
  document.getElementById('out').textContent = '@@P28@@' + JSON.stringify(results) + '@@P28END@@';
}
setTimeout(step1, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe28.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe28.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
m = re.search(r'@@P28@@(.*?)@@P28END@@', dom, re.S)
if m:
    print(m.group(1)[:4000])
else:
    print('NO MARKER')
httpd.shutdown()
