# -*- coding: utf-8 -*-
"""headless Chrome 探针：验证 顶部共享控件 + 三视图 + HRBP 分出"""
import http.server, socketserver, threading, subprocess, os, re, sys

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8937

os.chdir(WS)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

# 探针页面：iframe 加载报表（同源），依次执行检查，把结果写进 <pre id=out>
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
  results.globalControls = !!d.getElementById('globalControls');
  results.oneBtnDay = d.querySelectorAll('#btnDay').length;
  results.oneBtnPicker = d.querySelectorAll('#btnPicker').length;
  results.oneBtnRegion = d.querySelectorAll('#btnRegion').length;
  results.noGenBtn = d.querySelectorAll('#genBtnDay,#genBtnPicker,#genBtnRegion').length;
  results.noAttBtn = d.querySelectorAll('#attBtnDay,#attBtnPicker,#attBtnRegion').length;
  results.noViewControls = d.querySelectorAll('#viewFormal .controls,#viewGen .controls,#viewAttend .controls').length;
  results.globalBeforeViewFormal = d.getElementById('globalControls').compareDocumentPosition(d.getElementById('viewFormal')) & Node.DOCUMENT_POSITION_FOLLOWING ? true : false;
  results.genRows = d.querySelectorAll('#genMajorBody tr').length;
  results.attRows = d.querySelectorAll('#attMajorBody tr').length;
  results.majorRows = d.querySelectorAll('#majorBody tr').length;
  // 切到 补签率（正式工 sign）
  click(d.getElementById('secSign'));
  results.signRowsAfterSwitch = d.querySelectorAll('#majorBody tr').length;
  results.signPickerLabel = d.getElementById('btnPicker').textContent;
  // 打开正式工补签率区域面板，检查 HRBP 列
  click(d.getElementById('btnRegion'));
  var h3 = qa('#rpGrid .rd-col-title').map(function(e){return e.textContent;});
  results.signRegionMajors = h3;
  click(d.body); // close
  // 切到 正式工及时率
  click(d.getElementById('secAtt')); click(d.getElementById('wtFormal'));
  results.genRows2 = d.querySelectorAll('#genMajorBody tr').length;
  results.genPickerLabel = d.getElementById('btnPicker').textContent;
  results.genMajorsInTable = qa('#genMajorBody tr.att-major').map(function(r){return r.getAttribute('data-major');});
  click(d.getElementById('btnRegion'));
  results.genRegionMajors = qa('#rpGrid .rd-col-title').map(function(e){return e.textContent;});
  var hrdCol = qa('#rpGrid .rd-col').filter(function(c){ return c.querySelector('.rd-col-title') && c.querySelector('.rd-col-title').textContent === 'FBU HRBP Dept.'; })[0];
  results.genHbpRegions = hrdCol ? Array.from(hrdCol.querySelectorAll('.rd-region-title')).map(function(e){return e.textContent;}) : [];
  // 切到 劳务工及时率
  click(d.getElementById('wtLabor'));
  results.attRows2 = d.querySelectorAll('#attMajorBody tr').length;
  results.attPickerLabel = d.getElementById('btnPicker').textContent;
  // 劳务区域面板（筛选行为）
  click(d.getElementById('btnRegion'));
  var beforeRows = d.querySelectorAll('#attMajorBody tr').length;
  var reg = qa('#rpGrid .rd-region-title')[0]; var regName = reg ? reg.textContent : '';
  if (reg) click(reg);
  results.attFilterRegion = regName;
  results.attRowsAfterFilter = d.querySelectorAll('#attMajorBody tr').length;
  results.attRegionBtnLabel = d.getElementById('btnRegion').textContent;
  // 模式切换（劳务工-按天）
  click(d.getElementById('btnDay'));
  results.attDayPicker = d.getElementById('btnPicker').textContent;
  // 切回 正式工及时率，切按月
  click(d.getElementById('wtFormal'));
  results.genAfterBackPicker = d.getElementById('btnPicker').textContent;
  results.modeActiveMonth = d.getElementById('btnMonth').classList.contains('active');
  results.errors = errors;
  document.getElementById('out').textContent = '@@P17@@' + JSON.stringify(results) + '@@P17END@@';
}
setTimeout(function(){ try { step1(); } catch(e){ document.getElementById('out').textContent = 'PROBE_ERR ' + (e && e.stack || e); } }, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe17.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom',
       '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe17.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
m = re.search(r'@@P17@@(.*?)@@P17END@@', dom, re.S)
if m:
    print(m.group(1))
else:
    m2 = re.search(r'PROBE_ERR (.*?)</pre>', dom, re.S)
    print('PROBE_ERR:', m2.group(1)[:800] if m2 else 'no marker; dom len=%d stderr=%s' % (len(dom), p.stderr[:300]))
httpd.shutdown()
