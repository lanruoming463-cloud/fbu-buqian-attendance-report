# -*- coding: utf-8 -*-
"""Probe35: 验证 T+1 板块（tab → t1Show → KPI/月表/日表 DOM 渲染 + 定稿徽章）。"""
import http.server, socketserver, threading, subprocess, os, re

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8967
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
    ev('t1Show()');
    out.tabActive = ev('document.getElementById("secT1").classList.contains("active")');
    out.panelVisible = ev('document.getElementById("viewT1").style.display');
    out.otherHidden = ev('["viewFormal","viewAttend","viewGen"].map(function(i){return document.getElementById(i).style.display;}).join(",")');
    out.kpiCount = ev('document.querySelectorAll("#t1Kpis .t1-kpi").length');
    out.kpiFirst = ev('document.querySelector("#t1Kpis .t1-kpi-v") ? document.querySelector("#t1Kpis .t1-kpi-v").textContent : "NONE"');
    out.monthRows = ev('document.querySelectorAll(".t1-months-wrap tbody tr").length');
    out.monthRate = ev('(function(){var tds=document.querySelectorAll(".t1-months-wrap tbody tr:last-child td");return tds.length?tds[4].textContent:"NONE";})()');
    out.dayRows = ev('document.querySelectorAll("#t1Days tbody tr").length');
    out.tagCounts = ev('(function(){var ok=document.querySelectorAll("#t1Days .t1-ok").length;var lv=document.querySelectorAll("#t1Days .t1-live").length;return ok+"/"+lv;})()');
    out.lastDayRow = ev('(function(){var tr=document.querySelector("#t1Days tbody tr:last-child");return tr?Array.from(tr.cells).slice(0,6).map(function(c){return c.textContent;}).join("|"):"NONE";})()');
    out.updLine = ev('document.getElementById("t1UpdLine").textContent.slice(0,60)');
    // 回归：切回原三视图仍正常
    ev('showCell("formal","att")');
    out.backToGen = ev('document.getElementById("viewGen").style.display + "/" + document.getElementById("viewT1").style.display');
    ev('showCell("labor","sign")');
    out.backToSign = ev('document.getElementById("viewFormal").style.display + "/" + document.getElementById("viewT1").style.display');
  } catch(e) { out = {EXC: String(e && e.stack || e)}; }
  document.getElementById('out').textContent = '@@P35@@' + JSON.stringify(out) + '@@P35END@@';
}
setTimeout(step1, 9000);
</script></body></html>"""

with open(os.path.join(WS, '_probe35.html'), 'w', encoding='utf-8') as f:
    f.write(PROBE)

cmd = [CHROME, '--headless=new', '--disable-gpu', '--dump-dom', '--virtual-time-budget=25000',
       'http://127.0.0.1:%d/_probe35.html' % PORT]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
dom = p.stdout
m = re.search(r'@@P35@@(.*?)@@P35END@@', dom, re.S)
print(m.group(1) if m else ('NO MARKER dom=%d' % len(dom)))
httpd.shutdown()
