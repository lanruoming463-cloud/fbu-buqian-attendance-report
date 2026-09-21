# -*- coding: utf-8 -*-
"""调试：劳务工组行展开员工（v2，修正 marker 与 const 访问）"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8945

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
function step1(){
  var d = document.getElementById('f').contentDocument;
  click(d.getElementById('secAtt')); click(d.getElementById('wtLabor'));
  results.hasToggleAttendEmp = typeof d.defaultView.toggleAttendEmp === 'function';
  var g = q('#attGrpBody tr.att-grp');
  results.gFound = !!g;
  if (g){
    results.gAttrs = [g.getAttribute('data-major'), g.getAttribute('data-region'), g.getAttribute('data-wh'), g.getAttribute('data-group')];
    try { d.defaultView.toggleAttendEmp(g); results.directCall = qa('#attGrpBody tr.emp-subrow').length; }
    catch(e){ results.directCall = 'ERR ' + (e && e.message); }
    var g2 = qa('#attGrpBody tr.att-grp')[1];
    if (g2){ click(g2); results.delegatedClick = qa('#attGrpBody tr.emp-subrow').length; }
  }
  results.errors = errors;
  document.getElementById('out').textContent = '@@' + 'PD2@@' + JSON.stringify(results) + '@@' + 'PD2END@@';
}
setTimeout(function(){ try { step1(); } catch(e){ document.getElementById('out').textContent = 'PROBE_ERR ' + (e && e.stack || e); } }, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe_dbg.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe_dbg.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
dom = p.stdout
m2 = re.search(r'PROBE_ERR (.*?)</pre>', dom, re.S)
m = re.search(r'@@PD2@@(.*?)@@PD2END@@', dom, re.S)
if m:
    print(m.group(1))
elif m2:
    print('PROBE_ERR:', m2.group(1)[:800])
else:
    print('no marker; dom len=%d stderr=%s' % (len(dom), p.stderr[:300]))
httpd.shutdown()
