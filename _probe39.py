# -*- coding: utf-8 -*-
import http.server, socketserver, threading, subprocess, os, time, io, sys, urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
PORT = 8804
src = open(os.path.join(WS, '补签流程_补签统计.html'), encoding='utf-8', errors='ignore').read()
hook = ('<script>window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+" @"+l+":"+c);'
        'try{var d=document.createElement("div");d.id="__errbanner";d.style.cssText="position:fixed;top:0;left:0;right:0;z-index:99999;background:#dc2626;color:#fff;font:14px monospace;padding:10px;max-height:50%;overflow:auto";'
        'd.textContent="JSERR: "+m+" @"+l+":"+c;document.body.appendChild(d);}catch(e){}};'
        'window.addEventListener("DOMContentLoaded",function(){setTimeout(function(){try{'
        'var trs=document.querySelectorAll("tbody tr").length;'
        'var tabs=document.querySelectorAll("table").length;'
        'var d=document.createElement("div");d.id="__okbanner";d.style.cssText="position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#059669;color:#fff;padding:8px;font:14px monospace";'
        'd.textContent="errs="+window.__errs.length+" | tbodyTr="+trs+" | tables="+tabs;'
        'document.body.appendChild(d);'
        'if(window.__errs.length){var e=document.createElement("div");e.style.cssText="position:fixed;top:40px;left:0;right:0;z-index:99999;background:#dc2626;color:#fff;padding:8px;font:12px monospace;max-height:40%;overflow:auto";e.textContent="ERRS:\\n"+window.__errs.join("\\n");document.body.appendChild(e);}'
        '}catch(e){}},5000);});</script>')
injected = src.replace('<head>', '<head>' + hook, 1)
dbg = os.path.join(WS, '_dbg_probe39.html')
open(dbg, 'w', encoding='utf-8').write(injected)
print('dbg html bytes:', len(injected))


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def translate_path(self, path):
        path = urllib.parse.unquote(path).split('?')[0]
        if path.startswith('/'):
            path = path[1:]
        return os.path.join(WS, path)


srv = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.6)
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
prof = os.path.join(WS, '_chrome_prof_probe39')
shot = os.path.join(WS, '_dbg_shot39.png')
url = 'http://127.0.0.1:' + str(PORT) + '/_dbg_probe39.html'
cmd = [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
       '--user-data-dir=' + prof, '--window-size=1600,900',
       '--virtual-time-budget=30000', '--screenshot=' + shot, url]
p = subprocess.run(cmd, capture_output=True, timeout=200)
print('rc=', p.returncode, 'png=', os.path.getsize(shot) if os.path.exists(shot) else -1)
srv.shutdown()
print('DONE')
