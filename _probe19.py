# -*- coding: utf-8 -*-
"""headless Chrome 探针 v2：验证 正式工及时率 组行角标 + 点击展开（在 iframe 作用域内 eval）"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8944

os.chdir(WS)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

PROBE = """<!DOCTYPE html><html><body><pre id="out">PENDING</pre>
<iframe id="f" src="/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html" style="width:1400px;height:900px"></iframe>
<script>
var results = {}; var errors = [];
window.addEventListener('error', function(e){ errors.push(String(e.message)); });
function q(sel){ return document.getElementById('f').contentDocument.querySelector(sel); }
function qa(sel){ return Array.from(document.getElementById('f').contentDocument.querySelectorAll(sel)); }
function click(el){ el.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
function ev(code){ return document.getElementById('f').contentWindow.eval(code); }
function step1(){
  var d = document.getElementById('f').contentDocument;
  try {
    results.genSelMonth = ev('genSel');
    results.payloadEmpIdxKeys = ev('Object.keys(formalAttPayload.empIndex||{}).length');
    results.payloadEmpCntKeys = ev('Object.keys(formalAttPayload.empCount||{}).length');
    results.payloadTotalRows = ev('Object.values(formalAttPayload.empCount||{}).reduce(function(a,b){return a+b;},0)');
    var grpRows = qa('#genGrpBody tr.att-grp');
    results.grpRowCount = grpRows.length;
    var badged = grpRows.filter(function(r){ return r.querySelector('.emp-count'); });
    results.badgedCount = badged.length;
    // 找一个当前月角标 >0 的组
    var pos = badged.filter(function(r){ return /未及时确认 [1-9]/.test(r.querySelector('.emp-count').textContent); });
    results.posBadgedCount = pos.length;
    results.zeroBadgedCount = badged.length - pos.length;
    if (pos.length) {
      var b0 = pos[0];
      results.firstBadgeText = b0.querySelector('.emp-count').textContent;
      results.firstKey = ['major','region','wh','group'].map(function(a){return b0.getAttribute('data-'+a);}).join('|');
      // 展开前查索引
      var kk = JSON.stringify(results.firstKey);
      results.idxLen = ev('(formalAttPayload.empIndex[' + kk + ']||[]).length');
      results.genIdxLen = ev('(genEmpIdx[' + kk + ']||[]).length');
      click(b0.querySelector('td'));
      var sub = b0.nextElementSibling;
      results.subrowAppeared = !!(sub && sub.classList.contains('emp-subrow'));
      if (sub) {
        var et = sub.querySelector('table.emp-table');
        results.empTable = !!et;
        if (et) {
          results.empHeads = Array.from(et.querySelectorAll('thead th')).map(function(e){return e.textContent;});
          var firstRow = et.querySelector('tbody tr');
          results.empFirstRow = firstRow ? Array.from(firstRow.querySelectorAll('td')).map(function(e){return e.textContent;}) : [];
          results.empRowCount = et.querySelectorAll('tbody tr').length;
        }
      }
      results.badgeAfterExpand = b0.querySelector('.emp-count').textContent;
      click(b0.querySelector('td'));
      var sub2 = b0.nextElementSibling;
      results.collapsed = !(sub2 && sub2.classList.contains('emp-subrow'));
      results.badgeAfterCollapse = b0.querySelector('.emp-count').textContent;
    }
    results.errors = errors;
  } catch(e) { results.EXC = String(e && e.stack || e); }
  document.getElementById('out').textContent = '@@P19@@' + JSON.stringify(results) + '@@P19END@@';
}
setTimeout(function(){ try { step1(); } catch(e){ document.getElementById('out').textContent = 'PROBE_ERR ' + (e && e.stack || e); } }, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe19.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe19.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
m = re.search(r'@@P19@@(.*?)@@P19END@@', dom, re.S)
if m:
    print(m.group(1))
else:
    m2 = re.search(r'PROBE_ERR (.*?)</pre>', dom, re.S)
    print('PROBE_ERR:', m2.group(1)[:800] if m2 else 'no marker; dom len=%d stderr=%s' % (len(dom), p.stderr[:300]))
httpd.shutdown()
