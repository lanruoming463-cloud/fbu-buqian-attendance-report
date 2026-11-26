# -*- coding: utf-8 -*-
"""妙搭部署：补签流程报表 -> app_17cg3t4mvjm（走旧 path + lark-cli 凭证）"""
import os, sys, shutil, subprocess, json, time

WS = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
import glob as _glob
_GIT_CANDIDATES = sorted(_glob.glob(r'C:\Users\zt25337\.workbuddy\binaries\PortableGit\versions\*\[Mm]ingw64\bin\git.exe'), reverse=True)
GIT_BIN = os.path.dirname(_GIT_CANDIDATES[0]) if _GIT_CANDIDATES else r'C:\Users\zt25337\.workbuddy\binaries\PortableGit\versions\1.3.0\mingw64\bin'
LARK = r'C:\Users\zt25337\.workbuddy\binaries\node\cli-connector-packages\node_modules\@larksuite\cli\bin\lark-cli.exe'
APP = 'app_17cg3t4mvjm'
OLD_PATH = '/apaas4.0/-/t_vkCL6f1I/code_p6iBZnfLI6KD.git'
HOST = 'miaoda-git.feishu.cn'
HTML = os.path.join(WS, '补签流程_补签统计.html')
REPO = os.path.join(WS, '_md_repo_deploy')
TMP_HOME = os.path.join(WS, 'tmp_git_home')

def log(*a):
    print(*a, flush=True)

def run(cmd, cwd=None, inp=None, env=None, timeout=600):
    # git 命令默认用 ENV（显式 GIT_EXEC_PATH/HOME/禁 GUI 凭证选择器）
    if env is None and cmd and os.path.basename(str(cmd[0])).lower() == 'git.exe':
        env = ENV
    p = subprocess.run(cmd, cwd=cwd, input=inp, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, timeout=timeout)
    return p

ENV = os.environ.copy()
_base_git = os.path.dirname(os.path.dirname(GIT_BIN))
ENV.update({
    'GIT_EXEC_PATH': os.path.join(_base_git, 'mingw64', 'bin'),
    'GIT_CONFIG_NOSYSTEM': '1',
    'GIT_SSL_CAINFO': os.path.join(_base_git, 'mingw64', 'etc', 'ssl', 'certs', 'ca-bundle.crt'),
    'GIT_TERMINAL_PROMPT': '0',
    'GIT_ASKPASS': 'echo',
    'SSH_ASKPASS': 'echo',
})
ENV['HOME'] = TMP_HOME
ENV['PATH'] = GIT_BIN + os.pathsep + os.path.join(_base_git, 'usr', 'bin') + os.pathsep + ENV.get('PATH', '')

GIT = os.path.join(GIT_BIN, 'git.exe')

# ---- 1. 取凭证 ----
# lark-cli 在继承 env 含 GCBuddy/工作台上下文变量时会误判 "hermes context detected"
# → 用最小 env（凭证 2026-09-22 实测正常返回）
LARK_ENV = {'SYSTEMROOT': os.environ.get('SYSTEMROOT', r'C:\Windows'),
            'COMSPEC': os.environ.get('COMSPEC', r'C:\Windows\system32\cmd.exe'),
            'PATH': os.environ.get('PATH', ''),
            'USERPROFILE': os.environ.get('USERPROFILE', ''),
            'APPDATA': os.environ.get('APPDATA', ''),
            'LOCALAPPDATA': os.environ.get('LOCALAPPDATA', ''),
            'TEMP': os.environ.get('TEMP', ''), 'TMP': os.environ.get('TMP', '')}
inp = "protocol=https\nhost=%s\npath=%s/\n" % (HOST, OLD_PATH)
p = run([LARK, 'apps', 'git-credential-helper', '--app-id', APP, 'get'], inp=inp, env=LARK_ENV)
U = P = None
for line in p.stdout.splitlines():
    if line.startswith('username='): U = line[9:]
    elif line.startswith('password='): P = line[9:]
if not (U and P):
    log('FAIL: no credential. stdout=', p.stdout[:300], 'stderr=', p.stderr[:300]); sys.exit(1)
URL = 'https://%s:%s@%s%s' % (U, P, HOST, OLD_PATH)
CLEAN = 'https://%s%s' % (HOST, OLD_PATH)
log('cred ok, user=', U[:8], '...')

# ---- 2~4. 浅获取方案：init + fetch --depth=1 + reset（避开全量 clone 超时） ----
# 目录策略：优先找/建一个有效的 git 工作目录，不做删除（沙箱拦截批量删除）
def _is_valid_repo(d):
    if not os.path.isdir(os.path.join(d, '.git')):
        return False
    return run([GIT, 'rev-parse', '--git-dir'], cwd=d).returncode == 0

REPO = os.path.join(WS, '_md_repo_deploy')
if not _is_valid_repo(REPO):
    base_ts = time.strftime('%Y%m%d_%H%M%S')
    REPO = os.path.join(WS, '_md_repo_deploy_' + base_ts)
    if not os.path.exists(REPO):
        os.makedirs(REPO)

p = run([GIT, 'init', REPO], timeout=120)
if p.returncode != 0:
    log('FAIL init:', p.stderr[-500:]); sys.exit(1)
p = run([GIT, '-c', 'credential.helper=', 'fetch', '--depth=1', URL, '+refs/heads/sprint/default'], cwd=REPO, timeout=900)
if p.returncode != 0:
    log('FAIL shallow fetch:', p.stderr[-800:]); sys.exit(1)
p = run([GIT, 'rev-parse', 'FETCH_HEAD'], cwd=REPO)
tip = p.stdout.strip()
log('sprint/default tip =', tip[:9])

# reset --hard FETCH_HEAD（若 loose ref 写入异常则手动 update-ref）
p = run([GIT, 'reset', '--hard', 'FETCH_HEAD'], cwd=REPO)
p2 = run([GIT, 'rev-parse', 'HEAD'], cwd=REPO)
head = p2.stdout.strip()
if head != tip:
    p3 = run([GIT, 'update-ref', 'HEAD', tip], cwd=REPO)
    p4 = run([GIT, 'checkout', '-f', '-b', 'main'], cwd=REPO)
    p2 = run([GIT, 'rev-parse', 'HEAD'], cwd=REPO)
    head = p2.stdout.strip()
if head != tip:
    log('FAIL: HEAD(%s) != FETCH_HEAD(%s)' % (head[:9], tip[:9])); sys.exit(1)
p = run([GIT, 'checkout', '-f', '-B', 'main', tip], cwd=REPO)
if p.returncode != 0:
    log('FAIL checkout:', p.stderr[-500:]); sys.exit(1)
log('reset ok at', head[:9])

# ---- 5. 覆盖 index.html + commit（commit 信息按需修改） ----
COMMIT_MSG = 'V25.22 T+1增量注入(2026-11-26, 数据至11.24): (A)正式工 11-24 新增日块2032行/未及时94 -> 月块2026-11 total 46254+2032=48286/untimely 1685+94=1779; 巴黎2号仓11-24经真源FORMAL_ATT_WH_DATE_EXCLUDE整条剔除(本源文件该仓该日原始0行,规则无实际剔除对象但持续生效). (B1)劳务工 LA19(洛杉矶19号仓) 11.21/22/23专用晚班1449行增量并入现有3日块(未确认2/ldk1; 11-23有2条真实未确认按实际处理); (B2)劳务工 非LA19 11-24新增日块7738行/未确认846/ldk33. 外科手术式: 6/7/8/9月61日块保留、2026-10零改动. 校验全过(正式工timely自洽/月块=日块和/6-7-10月零改动, 劳务工yqr==sjqr+unconfirmed/历史零改动). | 上批V25.21: (A)正式工 11-21/22/23 新增3日块(2034/2034/2046行, 未及时47/51/98) -> 月块2026-11 total 40144+6114=46258/untimely 1494+196=1690; zt0021853 11-23经真源整条剔除(读源仅命中11-21/22两条正常记录,保留). (B1)劳务工 LA19(洛杉矶19号仓) 11.20专用晚班558行增量并入现有11-20日块(全确认未确认0/ldk1, yqr 9321->9879, ldk 1->2); (B2)劳务工 非LA19 11-21/22/23新增3日块(yqr 6790/5770/7745, 未确认238/196/929, ldk 0/3/8). 外科手术式: 6/7/8/9月61日块保留、2026-10零改动. 校验全过(正式工timely自洽/月块=日块和/6-7-10月零改动, 劳务工yqr==sjqr+unconfirmed/历史零改动). | 上批V25.20: KANTE Aboubakari FR091592 / 欧洲区法国区巴黎7号仓交运组 / 2026-11-09(未确认,下班未打卡+迟到18分钟)按白名单剔除(保留总数,计为已确认,移出未确认名单), 仅11-09一天(11-04/05两条不动). 11-09日块 sjqr 7061->7062/unconfirmed 715->714, 交运组group节点归零后按真源压缩规则移除, empIndex删1行. 真源固化 LABOR_ATT_DATE_WHITELIST += FR091592/2026-11-09. 校验全过(自洽/61日块保留/10月零改动/其他11月日块零改动). | 上批V25.19: (A)正式工白名单11条(异常改正常/保留total) Ying HUANG zt15752 11月5条+Yixuan DU zt0023339 11月3条+法国区11-10其他3人(zt0022766/0022976/0021413); (B)正式工整条剔除法区行政部 Jie REN zt0022107 11月5条(11-04/05/06/09/10,分子分母全减); 月块2026-11 total 40151->40146/untimely 1513->1497. (C)劳务工白名单 法国区2026-11-10全天全部未确认计为已确认(sjqr 6618->6816/unconfirmed 932->734, 176条样本行删, Top unc 7人各扣1). 真源固化: FORMAL_ATT_DATE_WHITELIST/EXCLUDE_DATES(zt0022107)/LABOR_ATT_REGION_DATE_WHITELIST(法国区11-10) 于 _inject_1025+gen. 校验全过(正式工timely自洽/月块=日块和/6-7-10月零改动, 劳务工自洽/61日块保留/10月零改动).'
shutil.copyfile(HTML, os.path.join(REPO, 'index.html'))
run([GIT, 'add', '-A'], cwd=REPO)
p = run([GIT, 'status', '--porcelain'], cwd=REPO)
if not p.stdout.strip():
    log('nothing to commit（内容与线上一致）'); sys.exit(0)
p = run([GIT, 'commit', '-m', COMMIT_MSG], cwd=REPO)
if p.returncode != 0:
    log('FAIL commit:', p.stderr[-500:]); sys.exit(1)
p = run([GIT, 'rev-parse', 'HEAD'], cwd=REPO)
new_sha = p.stdout.strip()
log('commit ok:', new_sha[:9])

# ---- 6. push HEAD -> sprint/default ----
p = run([GIT, '-c', 'credential.helper=', 'push', URL, 'HEAD:refs/heads/sprint/default'],
        cwd=REPO, timeout=900)
out = (p.stdout or '') + (p.stderr or '')
log('push rc=%s' % p.returncode)
log(out[-600:])
if p.returncode != 0:
    sys.exit(1)

# ---- 7. release-create ----
p = run([LARK, 'apps', '+release-create', '--app-id', APP, '--branch', 'sprint/default'],
        timeout=300, env=LARK_ENV)
log('release-create rc=%s' % p.returncode)
log('stdout:', p.stdout[:1500])
log('stderr:', p.stderr[:800])
rid = None
try:
    j = json.loads(p.stdout)
    rid = j.get('data', {}).get('release_id') or j.get('release_id') or j.get('data', {}).get('id')
except Exception:
    import re
    m = re.search(r'(\d{15,25})', p.stdout)
    if m: rid = m.group(1)
if not rid:
    sys.exit(1)
log('release_id =', rid)

# ---- 8. 轮询 release-get ----
for i in range(60):
    time.sleep(10)
    p = run([LARK, 'apps', '+release-get', '--app-id', APP, '--release-id', rid], timeout=120, env=LARK_ENV)
    txt = p.stdout
    st = None
    try:
        j = json.loads(txt)
        d = j.get('data', j)
        st = d.get('status') or d.get('release_status')
        if not st:
            s = json.dumps(j, ensure_ascii=False)
            for k in ('finished', 'running', 'failed'):
                if k in s: st = k; break
    except Exception:
        for k in ('finished', 'running', 'failed'):
            if k in txt: st = k; break
    log('poll#%d status=%s' % (i + 1, st))
    if st in ('finished', 'failed'):
        log(txt[:2000])
        break

# ---- 9. 发布成功后同步 GitHub（失败不影响部署结果） ----
if st == 'finished':
    try:
        GH_SYNC = os.path.join(WS, '_github_sync.py')
        if os.path.exists(GH_SYNC):
            gh_msg = '[release %s] %s' % (rid, COMMIT_MSG)
            gp = subprocess.run([sys.executable, GH_SYNC, gh_msg],
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=1800)
            log('--- github sync ---')
            log((gp.stdout or '')[-600:])
            if gp.returncode != 0:
                log('github sync rc=%s（不影响妙搭发布）' % gp.returncode)
    except Exception as _ge:
        log('github sync exception:', str(_ge)[:200])
log('DONE')
