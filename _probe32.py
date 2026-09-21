# -*- coding: utf-8 -*-
"""Probe: verify labor attend view Top10 now shows 未确认数 (7 cols)."""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8963
os.chdir(WS)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

PROBE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body>
<pre id="out">PENDING</pre>
<iframe id="f" src="/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html" style="width:1400px;height:900px"></iframe>
<script>
function ev(code){ return document.getElementById('f').contentWindow.eval(code); }
function step1(){
  var out = {};
  try {
    ev('showCell("labor","att")');
    out.headCols = ev('Array.from(document.querySelectorAll("#tableAttTop thead th")).map(function(h){ return h.textContent.trim(); })');
    out.capText = ev('var el = document.querySelector("#tableAttTop").closest("div").previousElementSibling; el ? el.textContent.trim().slice(0,60) : "NOCAP"');
    out.topData = ev('(function(){' +
      'var rows = Array.from(document.querySelectorAll("#attTopBody tr"));' +
      'var majors = 0, emps = [];' +
      'rows.forEach(function(r){' +
      '  if (r.classList.contains("att-major")) { majors++; return; }' +
      '  if (emps.length < 6) emps.push(Array.from(r.cells).map(function(c){ return c.textContent.trim(); }));' +
      '});' +
      'var ncols = {};' +
      'rows.forEach(function(r){ if(!r.classList.contains("att-major")) ncols[r.cells.length] = (ncols[r.cells.length]||0)+1; });' +
      'return {totalRows: rows.length, majorRows: majors, colCountDist: ncols, firstEmps: emps};' +
      '})()');
    // cross-check: payload topEmpIndex first key values all have unc>0 and sorted desc
    out.payloadCheck = ev('(function(){' +
      'var ks = Object.keys(attendPayload.topEmpIndex);' +
      'var ok = true, totalRegions = ks.length;' +
      'ks.forEach(function(k){' +
      '  var a = attendPayload.topEmpIndex[k];' +
      '  for (var i=0;i<a.length;i++){ if (!(a[i].unc > 0)) ok = false; if (i>0 && a[i].unc > a[i-1].unc) ok = false; }' +
      '});' +
      'return {regions: totalRegions, sortedAndPositive: ok};' +
      '})()');
  } catch(e) { out = {EXC: String(e && e.stack || e)}; }
  document.getElementById('out').textContent = '@@P32@@' + JSON.stringify(out) + '@@P32END@@';
}
setTimeout(step1, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe32.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom', '--virtual-time-budget=25000',
       'http://127.0.0.1:%d/_probe32.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
dom = p.stdout
m = re.search(r'@@P32@@(.*?)@@P32END@@', dom, re.S)
print(m.group(1) if m else ('NO MARKER dom=%d' % len(dom)))
httpd.shutdown()
