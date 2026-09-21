# -*- coding: utf-8 -*-
"""Probe: verify gen Top10 table now has 职位 column with values."""
import http.server, socketserver, threading, subprocess, os, re, json

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8960
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
    // switch to gen view
    ev('showCell("formal","att")');
    out.head = ev('document.getElementById("genTopHead").innerHTML');
    var rows = ev('(function(){' +
      'var rs = Array.from(document.querySelectorAll("#genTopBody tr.top-emp-row")).slice(0, 5);' +
      'return rs.map(function(r){ return Array.from(r.cells).map(function(c){ return c.textContent.trim(); }); });' +
      '})()');
    out.rows = rows;
    out.rowCount = ev('document.querySelectorAll("#genTopBody tr.top-emp-row").length');
    // check pos col (index 3) non-empty across all rows
    out.posFilled = ev('(function(){' +
      'var rs = Array.from(document.querySelectorAll("#genTopBody tr.top-emp-row"));' +
      'var filled = 0; rs.forEach(function(r){ var v = r.cells[3] ? r.cells[3].textContent.trim() : ""; if (v && v !== "\\u2014") filled++; });' +
      'return {total: rs.length, filled: filled};' +
      '})()');
    // major/region group header colspans
    out.colspans = ev('(function(){' +
      'var a = document.querySelector("#genTopBody tr.major-row-gt td");' +
      'var b = document.querySelector("#genTopBody tr.region-row-gt td");' +
      'return {major: a ? a.colSpan : null, region: b ? b.colSpan : null};' +
      '})()');
  } catch(e) { out = {EXC: String(e && e.stack || e)}; }
  document.getElementById('out').textContent = '@@P30@@' + JSON.stringify(out) + '@@P30END@@';
}
setTimeout(step1, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe30.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom', '--virtual-time-budget=20000',
       'http://127.0.0.1:%d/_probe30.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
dom = p.stdout
m = re.search(r'@@P30@@(.*?)@@P30END@@', dom, re.S)
print(m.group(1) if m else ('NO MARKER dom=%d' % len(dom)))
httpd.shutdown()
