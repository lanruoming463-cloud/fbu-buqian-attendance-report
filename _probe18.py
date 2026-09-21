# -*- coding: utf-8 -*-
"""headless Chrome 探针：验证 及时率两视图的分组折叠结构（与补签率一致）"""
import http.server, socketserver, threading, subprocess, os, re, sys

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8941

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
  // 切到 正式工及时率
  click(d.getElementById('secAtt')); click(d.getElementById('wtFormal'));
  results.genMajHdrs = qa('#genDetailBody tr.ghd-m').map(function(r){ return r.getAttribute('data-major'); });
  results.genRegHdrs = qa('#genWhBody tr.ghd-r').length;
  results.genWhHdrs = qa('#genGrpBody tr.ghd-w').length;
  results.genRegionLeaves = qa('#genDetailBody tr.att-region').length;
  results.genWhLeaves = qa('#genWhBody tr.att-wh').length;
  results.genGrpLeaves = qa('#genGrpBody tr.att-grp').length;
  results.genHeaderTxt = (q('#genDetailBody tr.ghd-m td') || {}).textContent || '';
  // 折叠交互：点击第一个大区组头，区域行应隐藏
  var hdr = q('#genDetailBody tr.ghd-m');
  var maj = hdr.getAttribute('data-major');
  var before = qa('#genDetailBody tr.att-region[data-major="' + maj + '"]').filter(function(r){ return !r.classList.contains('hidden'); }).length;
  click(hdr);
  var after = qa('#genDetailBody tr.att-region[data-major="' + maj + '"]').filter(function(r){ return !r.classList.contains('hidden'); }).length;
  results.genCollapseWorks = before > 0 && after === 0;
  click(hdr); // 展开
  var restored = qa('#genDetailBody tr.att-region[data-major="' + maj + '"]').filter(function(r){ return !r.classList.contains('hidden'); }).length;
  results.genExpandWorks = restored === before;
  // 仓表：点大区组头折叠
  var hdr3 = q('#genWhBody tr.ghd-m');
  var maj3 = hdr3.getAttribute('data-major');
  var wBefore = qa('#genWhBody tr.att-wh[data-major="' + maj3 + '"]').filter(function(r){ return !r.classList.contains('hidden'); }).length;
  click(hdr3);
  var wAfter = qa('#genWhBody tr.att-wh[data-major="' + maj3 + '"]').filter(function(r){ return !r.classList.contains('hidden'); }).length;
  results.genWhCollapseWorks = wBefore > 0 && wAfter === 0;
  // 架构面板跳转目标存在
  click(d.getElementById('btnRegion'));
  results.genPanelMajors = qa('#rpGrid .rd-col-title').map(function(e){return e.textContent;});
  click(d.body);
  // 切到 劳务工及时率
  click(d.getElementById('wtLabor'));
  results.attMajHdrs = qa('#attDetailBody tr.ahd-m').map(function(r){ return r.getAttribute('data-major'); });
  results.attRegHdrs = qa('#attWhBody tr.ahd-r').length;
  results.attWhHdrs = qa('#attGrpBody tr.ahd-w').length;
  results.attGrpLeaves = qa('#attGrpBody tr.att-grp').length;
  // 劳务工组行展开员工
  var g = q('#attGrpBody tr.att-grp');
  if (g) { click(g); results.attEmpRows = d.querySelectorAll('#attGrpBody tr.emp-subrow').length; }
  results.errors = errors;
  document.getElementById('out').textContent = '@@P18@@' + JSON.stringify(results) + '@@P18END@@';
}
setTimeout(function(){ try { step1(); } catch(e){ document.getElementById('out').textContent = 'PROBE_ERR ' + (e && e.stack || e); } }, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe18.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe18.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
dom = p.stdout
m = re.search(r'@@P18@@(.*?)@@P18END@@', dom, re.S)
if m:
    print(m.group(1))
else:
    m2 = re.search(r'PROBE_ERR (.*?)</pre>', dom, re.S)
    print('PROBE_ERR:', m2.group(1)[:800] if m2 else 'no marker; dom len=%d stderr=%s' % (len(dom), p.stderr[:300]))
httpd.shutdown()
