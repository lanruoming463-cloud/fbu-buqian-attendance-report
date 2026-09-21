# -*- coding: utf-8 -*-
"""Probe34: verify 补签率 Top10 (#tableTop) centered alignment + widths (formal & labor)."""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8966
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
function grab(){
  return '(function(){' +
    'var ths = Array.from(document.querySelectorAll("#tableTop thead th"));' +
    'var tds = Array.from(document.querySelectorAll("#tableTop tr.top-emp-row td")).slice(0,9);' +
    'var grpTd = document.querySelector("#tableTop tr.major-row-t td, #tableTop tr.region-row-t td");' +
    'var numTd = document.querySelector("#tableTop tr.top-emp-row td.num");' +
    'var c8 = document.querySelector("#tableTop tr.top-emp-row td:nth-child(8)");' +
    'return {heads: ths.map(function(h){ return h.textContent; }),' +
    ' th: ths.map(function(h){ return getComputedStyle(h).textAlign; }),' +
    ' td: tds.map(function(c){ return getComputedStyle(c).textAlign; }),' +
    ' widths: ths.map(function(h){ return Math.round(h.getBoundingClientRect().width); }),' +
    ' grpAlign: grpTd ? getComputedStyle(grpTd).textAlign : "N/A",' +
    ' numColor: numTd ? getComputedStyle(numTd).color + "/" + getComputedStyle(numTd).fontWeight : "N/A",' +
    ' c8Color: c8 ? getComputedStyle(c8).color : "N/A"};' +
    '})()';
}
function step1(){
  var out = {};
  try {
    ev('showCell("formal","sign")');
    out.formal = ev(grab());
    ev('showCell("labor","sign")');
    out.labor = ev(grab());
  } catch(e) { out = {EXC: String(e && e.stack || e)}; }
  document.getElementById('out').textContent = '@@P34@@' + JSON.stringify(out) + '@@P34END@@';
}
setTimeout(step1, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe34.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom', '--virtual-time-budget=25000',
       'http://127.0.0.1:%d/_probe34.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
dom = p.stdout
m = re.search(r'@@P34@@(.*?)@@P34END@@', dom, re.S)
print(m.group(1) if m else ('NO MARKER dom=%d' % len(dom)))
httpd.shutdown()
