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
仓库级（异常表仅有仓库名+日期、无工号）：对 该仓当天所有人 统一处理——CONFIRM 视为全部及时确认、EXCLUDE 视为整仓剔除；
聚合指标取自日块/月块 warehouse 条目（真实、无截断），empIndex 行仅用于删行与 top 减员；以该仓当天对应指标是否归零判等幂。
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


def wh_norm(s):
    s = (s or '').strip()
    s = re.sub(r'[（(].*?[)）]', '', s)  # 去 (TT)/(SN) 等后缀
    return s.strip()


def wh_match(a, b):
    """仓库名匹配：去后缀后相等，或互相包含（应对《异常表》与报表仓名微小差异）。"""
    a, b = wh_norm(a), wh_norm(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def is_warehouse_level(x):
    """无工号、但有仓库名 → 整仓级异常（按 仓库+日期 作用于该仓当天所有人）。"""
    return (not is_id(x.get('gong', ''))) and bool(x.get('wh', '').strip())


def _sub_metrics(e, action, we):
    """按 we(仓库级指标) 对某个聚合条目 e 做扣减/翻转；同时兼容正式工/劳务工字段。"""
    if action == 'EXCLUDE':
        for k in ('total', 'abnormal', 'untimely', 'yqr'):
            if k in e:
                e[k] = clamp(e[k] - we.get(k, 0))
        if 'unconfirmed' in e:
            e['unconfirmed'] = clamp(e['unconfirmed'] - we.get('unconfirmed', 0))
        if 'ldk' in e:
            e['ldk'] = clamp(e['ldk'] - we.get('ldk', 0))
        if 'timely' in e and 'total' in e:
            e['timely'] = clamp(e['total'] - e['untimely'])
    else:  # CONFIRM
        if 'untimely' in e:
            e['untimely'] = clamp(e['untimely'] - we.get('untimely', 0))
            if 'total' in e:
                e['timely'] = clamp(e['total'] - e['untimely'])
        if 'unconfirmed' in e:
            e['unconfirmed'] = clamp(e['unconfirmed'] - we.get('unconfirmed', 0))
        if 'sjqr' in e:
            e['sjqr'] = clamp(e['sjqr'] + we.get('unconfirmed', 0))


def wh_day_contrib(day, wh):
    """从 day 块提取 该仓当天 的分层贡献：total/major/detail/warehouse 用仓库聚合 we，
    group 按 (major,region,wh,group) 逐组记录。返回 (we_wh, w_entries, gmap)。
    同一份贡献同时作用于 day 与 month 块，保证月块仅减少该天贡献而非整月聚合。"""
    w_entries = [e for e in day.get('warehouse', []) if wh_match(wh, e.get('wh', ''))]
    we_wh = {'total': 0, 'abnormal': 0, 'untimely': 0, 'yqr': 0, 'unconfirmed': 0, 'ldk': 0}
    for e in w_entries:
        for kk in we_wh:
            we_wh[kk] += e.get(kk, 0)
    gmap = {}
    for g in day.get('group', []):
        if wh_match(wh, g.get('wh', '')):
            key = (g.get('major'), g.get('region'), g.get('wh'), g.get('group'))
            d = gmap.setdefault(key, {k: 0 for k in we_wh})
            for kk in d:
                d[kk] += g.get(kk, 0)
    return we_wh, w_entries, gmap


def apply_wh_contrib(block, action, we_wh, w_entries, gmap):
    """对某个块（day 或 month）施加同一份 day 级贡献。
    major/detail/warehouse/group 均在目标块内按 (major,region,wh[,group]) 查找后施加，
    不复用 day 块对象引用。"""
    _sub_metrics(block['total'], action, we_wh)
    for e in w_entries:
        maj, reg, whh = e.get('major'), e.get('region'), e.get('wh')
        for m in block['major']:
            if m['name'] == maj:
                _sub_metrics(m, action, we_wh); break
        for d in block['detail']:
            if d['major'] == maj and d['region'] == reg:
                _sub_metrics(d, action, we_wh); break
        for we in block['warehouse']:
            if we.get('major') == maj and we.get('region') == reg and wh_match(whh, we.get('wh', '')):
                _sub_metrics(we, action, we_wh); break
    for key, gwe in gmap.items():
        maj, reg, whh, grp = key
        for g in block.get('group', []):
            if g.get('major') == maj and g.get('region') == reg and wh_match(whh, g.get('wh', '')) and g.get('group') == grp:
                _sub_metrics(g, action, gwe); break


def collect_wh_rows(P, wh, date, kind):
    """收集 empIndex 中 仓库名(键第3段)匹配 且 日期(row)匹配 的所有行（仅用于删行+top减员）。"""
    date_i = 13 if kind == 'formal' else 11
    out = []
    for k, rows in P['empIndex'].items():
        parts = k.split('|')
        if len(parts) < 4:
            continue
        if not wh_match(wh, parts[2]):
            continue
        for r in rows:
            if len(r) > date_i and r[date_i] == date:
                out.append((k, r))
    return out


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
        P = fp
        if is_warehouse_level(x):
            # 整仓级：无工号、仅有仓库名+日期 → 该仓当天所有人 不算异常（计及时/确认）
            wh_w, date, action = x['wh'].strip(), x['date'], x['action']
            if date not in P['data']:
                stats['skip_out_range'] += 1; details.append(('SKIP-RANGE', 'formal', '(整仓)%s' % wh_w, date, action, x['reason'])); continue
            day = P['data'][date]
            we_wh, w_entries, gmap = wh_day_contrib(day, wh_w)
            # 幂等判据：该仓当天对应指标已为 0 → 已应用/无需处理
            ck = 'untimely' if action == 'CONFIRM' else 'total'
            if we_wh.get(ck, 0) == 0:
                stats['skip_no_row'] += 1; details.append(('SKIP-APPLIED', 'formal', '(整仓)%s' % wh_w, date, action, x['reason'])); continue
            month = date[:7]
            apply_wh_contrib(day, action, we_wh, w_entries, gmap)
            if month in P['data']:
                apply_wh_contrib(P['data'][month], action, we_wh, w_entries, gmap)
            # 删除该仓当天所有 empIndex 行（幂等 + 钻取列表同步）
            for k, r in collect_wh_rows(P, wh_w, date, 'formal'):
                parts = k.split('|'); maj, reg = parts[0], parts[1]; gong = r[1]
                rks = {maj + '|' + reg}
                adj_top(P['topEmpIndex'], gong, action, 1, rks)
                adj_top(P['topEmpIndexM'], gong, action, 1, rks, month=month)
                P['empIndex'][k] = [rr for rr in P['empIndex'][k] if rr is not r]
                if not P['empIndex'][k]:
                    del P['empIndex'][k]
            cnt = we_wh.get('untimely', 0) if action == 'CONFIRM' else we_wh.get('total', 0)
            stats['formal_applied'] += cnt
            details.append(('APPLY-WH', 'formal', '(整仓)%s' % wh_w, date, action, '整仓%d人 %s' % (cnt, x['reason'])))
            continue
        gong, date, action = x['gong'].strip(), x['date'], x['action']
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
        P = ap
        if is_warehouse_level(x):
            wh_w, date, action = x['wh'].strip(), x['date'], x['action']
            if date not in P['data']:
                stats['skip_out_range'] += 1; details.append(('SKIP-RANGE', 'labor', '(整仓)%s' % wh_w, date, action, x['reason'])); continue
            day = P['data'][date]
            we_wh, w_entries, gmap = wh_day_contrib(day, wh_w)
            ck = 'unconfirmed' if action == 'CONFIRM' else 'yqr'
            if we_wh.get(ck, 0) == 0:
                stats['skip_no_row'] += 1; details.append(('SKIP-APPLIED', 'labor', '(整仓)%s' % wh_w, date, action, x['reason'])); continue
            month = date[:7]
            apply_wh_contrib(day, action, we_wh, w_entries, gmap)
            if month in P['data']:
                apply_wh_contrib(P['data'][month], action, we_wh, w_entries, gmap)
            for k, r in collect_wh_rows(P, wh_w, date, 'labor'):
                parts = k.split('|'); maj, reg = parts[0], parts[1]; gong = r[1]
                rks = {maj + '|' + reg}
                adj_top(P['topEmpIndex'], gong, action, 1, rks)
                adj_top(P['topEmpIndexM'], gong, action, 1, rks, month=month)
                for kk in ('topEmpIndexLdk', 'topEmpIndexLdkM'):
                    if kk in P:
                        adj_top(P[kk], gong, action, 1, rks, month=None if kk == 'topEmpIndexLdk' else month)
                P['empIndex'][k] = [rr for rr in P['empIndex'][k] if rr is not r]
                if not P['empIndex'][k]:
                    del P['empIndex'][k]
            cnt = we_wh.get('unconfirmed', 0) if action == 'CONFIRM' else we_wh.get('yqr', 0)
            stats['labor_applied'] += cnt
            details.append(('APPLY-WH', 'labor', '(整仓)%s' % wh_w, date, action, '整仓%d人 %s' % (cnt, x['reason'])))
            continue
        gong, date, action = x['gong'].strip(), x['date'], x['action']
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
