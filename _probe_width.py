# -*- coding: utf-8 -*-
"""headless Chrome 探针：实测三个视图容器宽度是否一致（.wrap 1100px 居中）"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8947

os.chdir(WS)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

PROBE = """<!DOCTYPE html><html><body><pre id="out">PENDING</pre>
<iframe id="f" src="/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html" style="width:1440px;height:900px"></iframe>
<script>
var R = {}; var errors = [];
window.addEventListener('error', function(e){ errors.push(String(e.message)); });
function q(sel){ return document.getElementById('f').contentDocument.querySelector(sel); }
function click(el){ el.dispatchEvent(new MouseEvent('click', {bubbles:true})); }
function w(el){ return el ? Math.round(el.getBoundingClientRect().width) : null; }
function left(el){ return el ? Math.round(el.getBoundingClientRect().left) : null; }
function step1(){
  var d = document.getElementById('f').contentDocument;
  R.iframeW = 1440;
  var vf = d.getElementById('viewFormal');
  var vfWrap = vf.closest('.wrap');
  R.formalWrapW = w(vfWrap); R.formalWrapL = left(vfWrap);
  R.formalPanelW = w(vf);
  // 切到正式工及时率
  click(d.getElementById('secAtt')); click(d.getElementById('wtFormal'));
  var vg = d.getElementById('viewGen');
  var vgWrap = vg.closest('.wrap');
  R.genWrapW = w(vgWrap); R.genWrapL = left(vgWrap);
  R.genPanelW = w(vg);
  R.genSameWrapAsFormal = (vgWrap === vfWrap);
  // 切到劳务工及时率
  click(d.getElementById('wtLabor'));
  var va = d.getElementById('viewAttend');
  var vaWrap = va.closest('.wrap');
  R.attWrapW = w(vaWrap); R.attWrapL = left(vaWrap);
  R.attPanelW = w(va);
  R.attSameWrapAsGen = (vaWrap === vgWrap);
  R.errors = errors;
  document.getElementById('out').textContent = '@@' + 'PW@@' + JSON.stringify(R) + '@@PWEND@@';
}
setTimeout(function(){ try { step1(); } catch(e){ document.getElementById('out').textContent = 'PROBE_ERR ' + (e && e.stack || e); } }, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe_w.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe_w.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
dom = p.stdout
m2 = re.search(r'PROBE_ERR (.*?)</pre>', dom, re.S)
m = re.search(r'@@PW@@(.*?)@@PWEND@@', dom, re.S)
if m:
    print(m.group(1))
elif m2:
    print('PROBE_ERR:', m2.group(1)[:800])
else:
    print('no marker; dom len=%d stderr=%s' % (len(dom), p.stderr[:300]))
httpd.shutdown()
