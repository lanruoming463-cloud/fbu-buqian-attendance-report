# -*- coding: utf-8 -*-
"""headless Chrome 探针 v27：纯 ASCII 判定（提取角标数字），避免编码干扰"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8952

os.chdir(WS)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

PROBE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body><pre id="out">PENDING</pre>
<iframe id="f" src="/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html" style="width:1400px;height:900px"></iframe>
<script>
var results = {}; var errors = [];
window.addEventListener('error', function(e){ errors.push(String(e.message)); });
function qa(sel){ return Array.from(document.getElementById('f').contentDocument.querySelectorAll(sel)); }
function click(el){ el.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
function step1(){
  var d = document.getElementById('f').contentDocument;
  try {
    var grpRows = qa('#genGrpBody tr.att-grp');
    results.grpRowCount = grpRows.length;
    var info = grpRows.map(function(r){
      var b = r.querySelector('.emp-count');
      if (!b) return null;
      var m = b.textContent.match(/(\\d+)/);
      return { row: r, cnt: m ? parseInt(m[1],10) : -1, txt: b.textContent };
    }).filter(Boolean);
    results.badgedCount = info.length;
    results.posBadged = info.filter(function(x){ return x.cnt > 0; }).length;
    results.zeroBadged = info.filter(function(x){ return x.cnt === 0; }).length;
    var pos = info.filter(function(x){ return x.cnt > 0; });
    if (pos.length) {
      pos.sort(function(a,b){ return b.cnt - a.cnt; });
      var b0 = pos[0];
      results.topBadgeCnt = b0.cnt;
      results.topBadgeKey = ['major','region','wh','group'].map(function(a){ return b0.row.getAttribute('data-'+a); }).join('|');
      click(b0.row.querySelector('td'));
      var sub = b0.row.nextElementSibling;
      results.subrowAppeared = !!(sub && sub.classList.contains('emp-subrow'));
      if (sub) {
        var et = sub.querySelector('table.emp-table');
        results.empTable = !!et;
        if (et) {
          results.empHeads = Array.from(et.querySelectorAll('thead th')).map(function(e){ return e.textContent; });
          var fr = et.querySelector('tbody tr');
          results.empFirstRow = fr ? Array.from(fr.querySelectorAll('td')).map(function(e){ return e.textContent; }) : [];
          results.empRowCount = et.querySelectorAll('tbody tr').length;
        }
      }
      // collapse
      click(b0.row.querySelector('td'));
      var sub2 = b0.row.nextElementSibling;
      results.collapsed = !(sub2 && sub2.classList.contains('emp-subrow'));
      // expand again and verify position/date-desc order
      click(b0.row.querySelector('td'));
      var sub3 = b0.row.nextElementSibling;
      if (sub3) {
        var et3 = sub3.querySelector('table.emp-table');
        if (et3) {
          var dates = Array.from(et3.querySelectorAll('tbody tr')).map(function(tr){ return tr.querySelectorAll('td')[5].textContent; });
          results.datesSortedDesc = dates.every(function(v,i){ return i===0 || dates[i-1] >= v; });
          results.firstThreeDates = dates.slice(0,3);
        }
      }
      click(b0.row.querySelector('td')); // final collapse
    }
    results.errors = errors;
  } catch(e) { results.EXC = String(e && e.stack || e); }
  document.getElementById('out').textContent = '@@P27@@' + JSON.stringify(results) + '@@P27END@@';
}
setTimeout(function(){ try { step1(); } catch(e){ document.getElementById('out').textContent = 'PROBE_ERR ' + (e && e.stack || e); } }, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe27.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe27.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
m = re.search(r'@@P27@@(.*?)@@P27END@@', dom, re.S)
if m:
    print(m.group(1))
else:
    m2 = re.search(r'PROBE_ERR (.*?)</pre>', dom, re.S)
    print('PROBE_ERR:', m2.group(1)[:800] if m2 else 'no marker; dom len=%d stderr=%s' % (len(dom), p.stderr[:300]))
httpd.shutdown()
