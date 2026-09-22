# -*- coding: utf-8 -*-
"""模拟妙搭真实打开方式：URL 带各种 query 参数（lang/open_in_browser 等）"""
import http.server, socketserver, threading, subprocess, os, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
PORT = 8801
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def translate_path(self, path):
        import urllib.parse
        path = urllib.parse.unquote(path).split('?')[0]
        if path.startswith('/'): path = path[1:]
        return os.path.join(WS, path)
srv = socketserver.TCPServer(('127.0.0.1', PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.5)
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
prof = os.path.join(WS, '_chrome_prof_q')
base = 'http://127.0.0.1:' + str(PORT) + '/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html'
cases = [
    ('plain', base),
    ('lang', base + '?lang=zh-CN'),
    ('miaoda_like', base + '?lang=zh-CN&open_in_browser=true&from=miaoda&gcid=xxx&token=abc'),
    ('fragment', base + '#/?lang=zh-CN'),
]
for name, u in cases:
    shot = os.path.join(WS, '_q_%s.png' % name)
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
           '--user-data-dir=' + prof + '_' + name, '--window-size=1600,900',
           '--virtual-time-budget=15000', '--screenshot=' + shot, u]
    p = subprocess.run(cmd, capture_output=True, timeout=120)
    print(name, 'rc=', p.returncode, 'bytes=', os.path.getsize(shot))
srv.shutdown()
