# -*- coding: utf-8 -*-
"""
GitHub 同步脚本：补签考勤报表项目 -> github.com/lanruoming463-cloud/<REPO>
用法:
  python _github_sync.py            # 常规增量同步（commit+push 当前工作树）
  python _github_sync.py "msg"      # 指定 commit message
  python _github_sync.py --init     # 首次初始化（含 README/.gitignore）
需要环境变量 GITHUB_TOKEN（repo 权限 classic token）或同目录 .github_token 文件。
"""
import os, sys, subprocess, time

WS       = r'C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58'
BASE_GIT = r'C:\Users\zt25337\.workbuddy\binaries\PortableGit\versions\1.2.0'
GIT      = os.path.join(BASE_GIT, 'mingw64', 'bin', 'git.exe')
REPO_DIR = os.path.join(WS, '_github_repo')          # 独立干净仓库目录
GH_USER  = 'lanruoming463-cloud'
REPO     = 'fbu-buqian-attendance-report'
BRANCH   = 'main'

# ---- 同步范围（代码+文档+日志；大文件数据产物也包含，用户已确认） ----
INCLUDE_FILES = [
    'gen_buqian_stats.py',
    '_deploy3.py',
    '_github_sync.py',
    'README.md', '.gitignore',
]
INCLUDE_PREFIXES = [
    '_probe',            # 无头浏览器验证脚本
    'gen_run', '_gen_run',  # 生成日志
    '_deploy3_run',      # 部署日志
]
INCLUDE_EXACT = [
    'attend_acc_data.json',
]
# 开发历史日志（.workbuddy/memory/*.md）
MEMORY_DIR = os.path.join(WS, '.workbuddy', 'memory')

def log(*a):
    print(*a, flush=True)

def read_token():
    tok = os.environ.get('GITHUB_TOKEN', '').strip()
    if tok:
        return tok
    f = os.path.join(WS, '.github_token')
    if os.path.exists(f):
        return open(f, encoding='utf-8').read().strip()
    return None

def run(cmd, cwd=None, env=None, timeout=900):
    env = env or os.environ.copy()
    env.update({
        'GIT_EXEC_PATH': os.path.join(BASE_GIT, 'mingw64', 'bin'),
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_SSL_CAINFO': os.path.join(BASE_GIT, 'mingw64', 'etc', 'ssl', 'certs', 'ca-bundle.crt'),
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_ASKPASS': 'echo',
    })
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, timeout=timeout)
    return p

def collect_files():
    """收集要同步的文件清单 -> [(abs_path, repo_relpath)]"""
    items = []
    for name in INCLUDE_FILES:
        p = os.path.join(WS, name)
        if os.path.exists(p):
            items.append((p, name))
    for name in os.listdir(WS):
        if name.startswith(tuple(INCLUDE_PREFIXES)) and os.path.isfile(os.path.join(WS, name)):
            items.append((os.path.join(WS, name), name))
    for name in INCLUDE_EXACT:
        p = os.path.join(WS, name)
        if os.path.exists(p):
            items.append((os.path.join(WS, name), name))
    # 大文件数据产物（用户确认公开上传）
    for name in ('补签流程_补签统计.html', '补签流程_补签统计.xlsx'):
        p = os.path.join(WS, name)
        if os.path.exists(p):
            items.append((p, name))
    # 开发日志 -> docs/devlog/
    if os.path.isdir(MEMORY_DIR):
        for name in os.listdir(MEMORY_DIR):
            if name.endswith('.md'):
                items.append((os.path.join(MEMORY_DIR, name), 'docs/devlog/' + name))
    # 去重（按 repo relpath）
    seen, out = set(), []
    for abs_p, rel in items:
        if rel not in seen:
            seen.add(rel)
            out.append((abs_p, rel))
    return out

def ensure_repo_created(token):
    """通过 API 确保远端仓库存在（不存在则创建，public）"""
    import urllib.request, json as _json
    url = 'https://api.github.com/repos/%s/%s' % (GH_USER, REPO)
    req = urllib.request.Request(url, headers={
        'Authorization': 'token ' + token,
        'User-Agent': 'workbuddy-sync',
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            log('repo exists:', REPO)
            return True
    except Exception:
        pass
    body = _json.dumps({
        'name': REPO,
        'description': '海外FBU 补签流程/考勤确认 报表：生成脚本、部署链路、无头验证探针与开发日志',
        'private': False,   # 公开仓库（用户已确认）
        'has_issues': True, 'has_projects': False, 'has_wiki': False,
        'auto_init': False,
    }).encode('utf-8')
    req = urllib.request.Request('https://api.github.com/user/repos', data=body, method='POST', headers={
        'Authorization': 'token ' + token,
        'User-Agent': 'workbuddy-sync',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            log('repo created:', REPO, '(public)')
            return True
    except Exception as e:
        # 422 = already exists（并发场景），再验证一次
        try:
            with urllib.request.urlopen(req2 := urllib.request.Request(url, headers={
                    'Authorization': 'token ' + token, 'User-Agent': 'workbuddy-sync'}), timeout=30) as r:
                log('repo exists (after 422):', REPO)
                return True
        except Exception as e2:
            log('FAIL ensure repo:', str(e)[:200], '|', str(e2)[:200])
            return False

def main():
    msg = None
    init_mode = False
    args = [a for a in sys.argv[1:]]
    if args and args[0] == '--init':
        init_mode = True
        args = args[1:]
    if args:
        msg = args[0]

    token = read_token()
    if not token:
        log('ERROR: 未找到 GITHUB_TOKEN（环境变量或 .github_token 文件）')
        sys.exit(2)

    if init_mode:
        readme = os.path.join(WS, 'README.md')
        if not os.path.exists(readme):
            log('ERROR: README.md 不存在，先运行 --make-docs')
            sys.exit(2)
        gi = os.path.join(WS, '.gitignore')
        if not os.path.exists(gi):
            open(gi, 'w', encoding='utf-8').write(
                '# 本地运行产物/临时文件\n__pycache__/\n*.pyc\n.github_token\n'
                '_env_check.txt\n_inv.txt\n_inv2.txt\n_cred_check.txt\nchk_*.js\n'
                'orig_chk_*.js\n_temp_check.js\n_inspect_labor.log\n_rendergen_live.txt\nrepo_*/\n'
                '_md_repo_deploy*/\ntmp_git_home/\n_html_out/\n')

    if not os.path.isdir(os.path.join(REPO_DIR, '.git')):
        os.makedirs(REPO_DIR, exist_ok=True)
        p = run([GIT, 'init', '-b', BRANCH, REPO_DIR], timeout=120)
        if p.returncode != 0:
            log('FAIL init:', p.stderr[-300:]); sys.exit(1)
        # git 身份
        run([GIT, 'config', 'user.name', 'lanruoming463-cloud'], cwd=REPO_DIR)
        run([GIT, 'config', 'user.email', 'lanruoming463-cloud@users.noreply.github.com'], cwd=REPO_DIR)
        run([GIT, 'config', 'core.autocrlf', 'false'], cwd=REPO_DIR)

    if not ensure_repo_created(token):
        sys.exit(1)

    # 拷贝文件到仓库工作树
    files = collect_files()
    if not files:
        log('no files to sync'); sys.exit(0)
    import shutil
    for abs_p, rel in files:
        dst = os.path.join(REPO_DIR, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(abs_p, dst)

    run([GIT, 'add', '-A'], cwd=REPO_DIR)
    p = run([GIT, 'status', '--porcelain'], cwd=REPO_DIR)
    if not p.stdout.strip():
        log('nothing to commit（本地与远端一致）')
        return

    if not msg:
        n = len([l for l in p.stdout.splitlines() if l.strip()])
        msg = 'sync: %s — 更新 %d 个文件（代码/探针/日志/数据产物与本地保持一致）' % (
            time.strftime('%Y-%m-%d %H:%M'), n)

    p = run([GIT, 'commit', '-m', msg], cwd=REPO_DIR)
    if p.returncode != 0:
        log('FAIL commit:', p.stderr[-400:]); sys.exit(1)
    p = run([GIT, 'rev-parse', 'HEAD'], cwd=REPO_DIR)
    log('commit ok:', p.stdout.strip()[:9])

    # push（token 内嵌 URL，用完即弃；远程地址写 clean URL 到 config）
    url = 'https://%s:x-oauth-basic@github.com/%s/%s.git' % (token, GH_USER, REPO)
    run([GIT, 'remote', 'remove', 'origin'], cwd=REPO_DIR)
    p = run([GIT, 'remote', 'add', 'origin', 'https://github.com/%s/%s.git' % (GH_USER, REPO)], cwd=REPO_DIR)
    # push 不带 -u，避免 token URL 写入 branch tracking 配置
    p = run([GIT, '-c', 'credential.helper=', 'push', url, '%s:%s' % (BRANCH, BRANCH)],
            cwd=REPO_DIR, timeout=1800)
    out = (p.stdout or '') + (p.stderr or '')
    log('push rc=%s' % p.returncode)
    log(out[-500:])
    if p.returncode != 0:
        sys.exit(1)
    log('SYNC DONE -> https://github.com/%s/%s' % (GH_USER, REPO))

if __name__ == '__main__':
    main()
