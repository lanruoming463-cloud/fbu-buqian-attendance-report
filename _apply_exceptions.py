# -*- coding: utf-8 -*-
"""
_apply_exceptions.py — 将《考勤确认及时率异常表》抓取结果(att_exceptions.json)应用到报表 HTML。
规则(用户口径)：
  EXCLUDE(无故缺勤/没来上班等) → 剔除该天考勤数据：
    formal: total-1, abnormal-1, untimely-1 (timely=total-untimely 自洽不变)
    labor : yqr-1, 且若该行未确认 unconfirmed-1
  CONFIRM(未及时审批/有原因导致未及时确认) → 算该天考勤及时确认：
    formal: untimely-1, timely+1 (total 不变)
    labor : unconfirmed-1, sjqr+1 (yqr 不变)
幂等性：以 empIndex 中 (工号,日期) 行是否存在为判据——行在=未应用→应用并删行；行不在=已应用/当天本就及时/不在报表范围→跳过。
因此可每天重复执行，不会二次扣减；T+1 注入重建某日后再次运行会自动重新应用(自愈)。
同时同步：day 块 total/major/detail/warehouse/group、formal 月块、topEmpIndex/topEmpIndexM(/Ldk 变体)、empIndex。
退出码：0=有应用(需部署)；2=无任何应用(可跳过部署)；1=错误。
"""
import json, re, sys, hashlib, shutil, os

HTML = '补签流程_补签统计.html'
EXC = 'att_exceptions.json'
STATE = '_exc_state.json'
OUT = '_applied_exc.html'
NOTE_MARK = '<!-- EXC -->'

PREFIX = {'formalAttPayload': 'const formalAttPayload = ', 'attendPayload': 'const attendPayload = '}


def extract(h, name):
    i = h.find(PREFIX[name])
    if i < 0:
        raise RuntimeError('payload not found: ' + name)
    j = h.find('\n', i)
    s = h[i + len(PREFIX[name]):j].rstrip(';')
    return json.loads(s)


def splice(h, name, obj):
    old_i = h.find(PREFIX[name])
    old_j = h.find('\n', old_i)
    new_line = PREFIX[name] + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ';'
    return h[:old_i] + new_line + h[old_j:]


def clamp(v):
    return 0 if v < 0 else v


def is_id(g):
    g = (g or '').strip()
    return bool(re.match(r'^(zt[A-Za-z]?\d+|[A-Z]{2,4}\d{3,})$', g))


def row_matches(kind, row, gong, date):
    if is_id(gong):
        if row[1] != gong:
            return False
    else:  # 无工号，按姓名匹配
        if row[0].strip().lower() != gong.strip().lower():
            return False
    return row[13] == date if kind == 'formal' else row[11] == date


def adj_formal(d, action, n):
    t = d['total']
    if action == 'EXCLUDE':
        t['total'] = clamp(t['total'] - n); t['abnormal'] = clamp(t['abnormal'] - n); t['untimely'] = clamp(t['untimely'] - n)
    else:  # CONFIRM
        t['untimely'] = clamp(t['untimely'] - n); t['timely'] = clamp(t['timely'] + n)


def adj_formal_dims(d, action, n, maj, reg, wh, grp):
    def f(e):
        if action == 'EXCLUDE':
            e['total'] = clamp(e['total'] - n); e['abnormal'] = clamp(e['abnormal'] - n); e['untimely'] = clamp(e['untimely'] - n)
        else:
            e['untimely'] = clamp(e['untimely'] - n); e['timely'] = clamp(e['timely'] + n)
    for e in d['major']:
        if e['name'] == maj: f(e); break
    for e in d['detail']:
        if e['major'] == maj and e['region'] == reg: f(e); break
    for e in d['warehouse']:
        if e['major'] == maj and e['region'] == reg and e['wh'] == wh: f(e); break
    for e in d['group']:
        if e['major'] == maj and e['region'] == reg and e['wh'] == wh and e['group'] == grp: f(e); break


def adj_top_entry(e, action, n):
    if action == 'EXCLUDE':
        for k in ('total', 'abnormal', 'untimely'):
            if k in e: e[k] = clamp(e[k] - n)
    else:
        for k in (('untimely',) if 'untimely' in e else ('unc',)):
            if k in e: e[k] = clamp(e[k] - n)


def adj_top(idx, gong, action, n, region_keys, month=None):
    """idx: topEmpIndex(region keys) 或 topEmpIndexM[month](region keys)"""
    if month is not None:
        idx = idx.get(month) or {}
    for rk in region_keys:
        for e in idx.get(rk, []):
            if e.get('gong') == gong:
                adj_top_entry(e, action, n)


def adj_labor(d, action, n, was_unconf):
    t = d['total']
    if action == 'EXCLUDE':
        t['yqr'] = clamp(t['yqr'] - n)
        if was_unconf: t['unconfirmed'] = clamp(t['unconfirmed'] - n)
    else:
        t['unconfirmed'] = clamp(t['unconfirmed'] - n); t['sjqr'] = clamp(t['sjqr'] + n)


def adj_labor_dims(d, action, n, was_unconf, maj, reg, wh, grp):
    def f(e):
        if action == 'EXCLUDE':
            e['yqr'] = clamp(e['yqr'] - n)
            if was_unconf: e['unconfirmed'] = clamp(e['unconfirmed'] - n)
        else:
            e['unconfirmed'] = clamp(e['unconfirmed'] - n); e['sjqr'] = clamp(e['sjqr'] + n)
    for e in d['major']:
        if e['name'] == maj: f(e); break
    for e in d['detail']:
        if e['major'] == maj and e['region'] == reg: f(e); break
    for e in d['warehouse']:
        if e['major'] == maj and e['region'] == reg and e['wh'] == wh: f(e); break
    for e in d['group']:
        if e['major'] == maj and e['region'] == reg and e['wh'] == wh and e['group'] == grp: f(e); break


def patch_note(note, text):
    # 幂等：先移除旧注释块再追加
    if NOTE_MARK in note:
        note = re.sub(r'<!-- EXC -->.*?<!-- /EXC -->', '', note, flags=re.S)
    return note + '<span ' + NOTE_MARK.replace('<!--', 'data-x="1" ') + '></span>' if False else note + NOTE_MARK + text + '<!-- /EXC -->'


def main():
    exc = json.load(open(EXC, encoding='utf-8'))
    h = open(HTML, encoding='utf-8').read()
    fp = extract(h, 'formalAttPayload')
    ap = extract(h, 'attendPayload')

    stats = {'formal_applied': 0, 'labor_applied': 0, 'skip_no_row': 0, 'skip_out_range': 0, 'skip_no_dim': 0}
    details = []

    # ---------- formal ----------
    for x in exc['formal']:
        gong, date, action = x['gong'].strip(), x['date'], x['action']
        P, dkey_i = fp, 13
        if date not in P['data']:
            stats['skip_out_range'] += 1; details.append(('SKIP-RANGE', 'formal', gong, date, action, x['reason'])); continue
        day = P['data'][date]
        hits = [(k, r) for k, rows in P['empIndex'].items() for r in rows if row_matches('formal', r, gong, date)]
        if not hits:
            stats['skip_no_row'] += 1; details.append(('SKIP-NOROW', 'formal', gong, date, action, x['reason'])); continue
        n = len(hits)
        adj_formal(day, action, n)
        month = date[:7]
        if month in P['data']:
            adj_formal(P['data'][month], action, n)
        for k, r in hits:
            parts = k.split('|')
            maj, reg, wh, grp = parts[0], parts[1], parts[2], parts[3]
            try:
                adj_formal_dims(day, action, 1, maj, reg, wh, grp)
                if month in P['data']:
                    adj_formal_dims(P['data'][month], action, 1, maj, reg, wh, grp)
            except Exception as ex:
                stats['skip_no_dim'] += 1
            # top 索引
            rks = {maj + '|' + reg}
            adj_top(P['topEmpIndex'], gong, action, 1, rks)
            adj_top(P['topEmpIndexM'], gong, action, 1, rks, month=month)
            # 删 empIndex 行
            P['empIndex'][k] = [rr for rr in P['empIndex'][k] if rr is not r]
            if not P['empIndex'][k]:
                del P['empIndex'][k]
        stats['formal_applied'] += n
        details.append(('APPLY', 'formal', gong, date, action, x['reason'] + ' x%d' % n))

    # ---------- labor ----------
    for x in exc['labor']:
        gong, date, action = x['gong'].strip(), x['date'], x['action']
        P, dkey_i = ap, 11
        if date not in P['data']:
            stats['skip_out_range'] += 1; details.append(('SKIP-RANGE', 'labor', gong, date, action, x['reason'])); continue
        day = P['data'][date]
        hits = [(k, r) for k, rows in P['empIndex'].items() for r in rows if row_matches('labor', r, gong, date)]
        if not hits:
            stats['skip_no_row'] += 1; details.append(('SKIP-NOROW', 'labor', gong, date, action, x['reason'])); continue
        n = len(hits)
        was_unconf = all(r[7] == '未确认' for _, r in hits)
        adj_labor(day, action, n, was_unconf)
        for k, r in hits:
            parts = k.split('|')
            maj, reg, wh, grp = parts[0], parts[1], parts[2], parts[3]
            try:
                adj_labor_dims(day, action, 1, was_unconf, maj, reg, wh, grp)
            except Exception:
                stats['skip_no_dim'] += 1
            rks = {maj + '|' + reg}
            month = date[:7]
            adj_top(P['topEmpIndex'], gong, action, 1, rks)
            adj_top(P['topEmpIndexM'], gong, action, 1, rks, month=month)
            for kk in ('topEmpIndexLdk', 'topEmpIndexLdkM'):
                if kk in P:
                    adj_top(P[kk], gong, action, 1, rks, month=None if kk == 'topEmpIndexLdk' else month)
            P['empIndex'][k] = [rr for rr in P['empIndex'][k] if rr is not r]
            if not P['empIndex'][k]:
                del P['empIndex'][k]
        stats['labor_applied'] += n
        details.append(('APPLY', 'labor', gong, date, action, x['reason'] + ' x%d' % n))

    total_applied = stats['formal_applied'] + stats['labor_applied']

    # ---------- noteHtml ----------
    ts = exc.get('scraped_at', '')
    note_f = '考勤确认异常处理（每日定时抓取《考勤确认及时率异常表》，抓取时间 %s）：标记「无故缺勤/没来上班」等剔除该天考勤数据；标记「未及时审批/有原因导致未及时确认」计为该天考勤及时确认。本次正式工应用 %d 条。' % (ts, stats['formal_applied'])
    note_l = '考勤确认异常处理（每日定时抓取《考勤确认及时率异常表》，抓取时间 %s）：标记「无故缺勤/没来上班」等剔除该天考勤数据；标记「未及时审批/有原因导致未及时确认」计为该天考勤及时确认。本次劳务工应用 %d 条。' % (ts, stats['labor_applied'])
    fp['noteHtml'] = patch_note(fp['noteHtml'], note_f)
    ap['noteHtml'] = patch_note(ap['noteHtml'], note_l)

    h2 = splice(h, 'formalAttPayload', fp)
    h2 = splice(h2, 'attendPayload', ap)
    open(OUT, 'w', encoding='utf-8').write(h2)
    shutil.copyfile(OUT, HTML)
    os.remove(OUT)

    md5 = hashlib.md5(open(EXC, 'rb').read()).hexdigest()
    state = {'md5': md5, 'last_applied': total_applied, 'ts': ts}
    json.dump(state, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    for d in details:
        print(' '.join(str(v) for v in d))
    print('STATS:', json.dumps(stats, ensure_ascii=False))
    if total_applied > 0:
        print('RESULT: applied %d (formal %d / labor %d) — need deploy' % (total_applied, stats['formal_applied'], stats['labor_applied']))
        sys.exit(0)
    else:
        print('RESULT: nothing applied (already applied / out of range / no matching row) — skip deploy')
        sys.exit(2)


if __name__ == '__main__':
    main()
