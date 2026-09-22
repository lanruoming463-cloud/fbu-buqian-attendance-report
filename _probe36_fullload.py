# -*- coding: utf-8 -*-
"""完整加载页面（非 eval），截图看真实渲染"""
import http.server, socketserver, threading, subprocess, os, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
PORT = 8799
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def translate_path(self, path):
        # 所有路径映射到工作区根
        import urllib.parse
        path = urllib.parse.unquote(path).split('?')[0]
        if path.startswith('/'): path = path[1:]
        return os.path.join(WS, path) or WS
srv = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.5)
CHROME = None
for c in [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
          r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
          os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe')]:
    if os.path.exists(c): CHROME = c; break
print('chrome:', CHROME)
prof = os.path.join(WS, '_chrome_prof_t1full')
url = 'http://127.0.0.1:' + str(PORT) + '/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html'
shot = os.path.join(WS, '_t1full.png')
cmd = [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
       '--user-data-dir=' + prof, '--window-size=1600,1000',
       '--virtual-time-budget=20000',
       '--screenshot=' + shot, url]
p = subprocess.run(cmd, capture_output=True, timeout=120)
print('rc=', p.returncode, 'png bytes=', os.path.getsize(shot))
print('stderr tail:', (p.stderr or b'').decode('utf-8','replace')[-300:])
srv.shutdown()
