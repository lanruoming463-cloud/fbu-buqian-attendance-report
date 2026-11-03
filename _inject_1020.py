# -*- coding: utf-8 -*-
"""增量注入 2026-10-16~10.18 考勤确认及时率（正式工+劳务工）到已发布 HTML。
复用 _inject_1015.py 口径；读取桌面 10.16-10.18 文件，不触碰被安全中心拦截的 6/7 月【每月】文件。
输出 _injected_1016_18.html（验证后由部署脚本覆盖正式文件）。
"""
import json, re
import pandas as pd
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
OUT = WS + r"\_injected_1020.html"
FORMAL_XLS = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.20-及时性.xlsx"
LABOR_XLS = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.20-及时性.xlsx"

# ---------- 复制源码口径（与 _inject_1015.py 一致） ----------
FORMAL_ATT_SHEET = '考勤记录'
FORMAL_ATT_WHITELIST = {'zt0022905'}
# 离职剔除（用户 2026-10-22）：西班牙区 ZHANG NAN / zt0021903 已于 2026-09 底离职，剔除其 2026-10 全部考勤确认率数据
FORMAL_ATT_EXCLUDE_OCT = {'zt0021903'}
# 指定日期白名单（用户 2026-10-22）：特定员工特定日期考勤算作及时确认（保留记录、计为正常）
FORMAL_ATT_DATE_WHITELIST = {('zt0021580', '2026-10-19')}
# 劳务工指定日期剔除（用户 2026-10-22）：法国区四位劳务工对应日期考勤数据剔除
LABOR_ATT_EXCLUDE_DATES = {
    ('FR083014', '2026-10-19'), ('FR091493', '2026-10-18'),
    ('FR086719', '2026-10-14'), ('FR092791', '2026-10-14'),
    ('FR093742', '2026-10-20'), ('FR092978', '2026-10-21'),
}
FORMAL_HRBP_EXCLUDE = {'国内HRBP组', '美洲支持HRBP组', '美洲支持bp组', '欧亚支持bp组', '欧亚支持HRBP组'}
FORMAL_OTHER_MAJORS = {'海外销售部', '渠道管理部', 'LD 法务部', 'FBU技术部', '平台业务部', '品牌客户部'}
REGION_TO_MAJOR = {
    '亚特兰大区': '美洲区', '休斯顿区': '美洲区', '加州区': '美洲区', '加拿大区': '美洲区',
    '新泽西区': '美洲区', '芝加哥区': '美洲区', '萨凡纳区': '美洲区', '达拉斯区': '美洲区', '迈阿密区': '美洲区',
    '西雅图区': '美洲区', '诺福克区': '美洲区', '印第安纳区': '美洲区', '墨西哥区': '美洲区',
    '德国区': '欧洲区', '捷克区': '欧洲区', '法国区': '欧洲区', '波兰区': '欧洲区', '英国区': '欧洲区', '西班牙区': '欧洲区',
    '意大利区': '欧洲区',
    '澳洲区': '亚太区', '日本区': '亚太区', '韩国区': '亚太区',
}
FORMAL_ATT_KEYS = ['total', 'normal', 'abnormal', 'untimely']
ATTEND_METRICS = ['ydk', 'sjk', 'ybq', 'sjq', 'yqr', 'sjqr', 'ldk']

def _re_sub_major(l3, l4):
    l3 = str(l3).strip(); l4 = str(l4).strip()
    if l3 in ('欧洲区', '美洲区', '亚太区'): return l3
    core = re.sub(r'(HRBP部|行政部|渠道部|交付管理部|商务部|财务部)$', '', l4)
    if core in ('欧洲区', '美洲区', '亚太区'): return core
    if core in REGION_TO_MAJOR: return REGION_TO_MAJOR[core]
    for _maj in ('欧洲区', '美洲区', '亚太区'):
        if l4.startswith(_maj): return _maj
    return '其他'

def _fs(v):
    return str(v).strip() if pd.notna(v) else ''

# ---------- 正式工 recs（整文件，按 date 分组） ----------
def build_formal_recs():
    recs = []; untimely_rows = []
    df = pd.read_excel(FORMAL_XLS, sheet_name=FORMAL_ATT_SHEET)
    df['_d'] = pd.to_datetime(df['考勤日期'], errors='coerce')
    for _, r in df.iterrows():
        d = r['_d']
        if pd.isna(d): continue
        l3 = str(r['三级部门']).strip() if pd.notna(r['三级部门']) else ''
        l4 = str(r['四级部门']).strip() if pd.notna(r['四级部门']) else ''
        if ('财务部' in l3) or ('财务部' in l4): continue
        if l3 == 'FBU HRBP Dept.':
            if l4 in FORMAL_HRBP_EXCLUDE: continue
            major = 'FBU HRBP Dept.'; region = l4
        else:
            if not l4: continue
            major = _re_sub_major(l3, l4)
            if major == '其他' or l3 in FORMAL_OTHER_MAJORS: continue
            core = re.sub(r'(HRBP部|行政部|渠道部|交付管理部|商务部|财务部)$', '', l4)
            region = core if core else l4
        wh = str(r['五级部门']) if pd.notna(r['五级部门']) else '部门直属'
        grp = str(r['六级部门']) if pd.notna(r['六级部门']) else '部门直属'
        gong = str(r['工号']) if pd.notna(r['工号']) else ''
        # 离职剔除（用户 2026-10-22）：zt0021903 已于 2026-09 底离职，剔除其 2026-10 全部考勤确认率数据
        if gong in FORMAL_ATT_EXCLUDE_OCT and d.strftime('%Y-%m') == '2026-10':
            continue
        status = str(r['考勤状态'])
        is_abn = (status == '异常')
        untimely = False
        if is_abn:
            yc = str(r['异常备注']); bz = str(r['备注'])
            has_lc = ('迟到' in yc or '早退' in yc or '迟到' in bz or '早退' in bz)
            untimely = not has_lc
            if untimely and region == '捷克区':
                _fc = r['首打卡'] if pd.notna(r['首打卡']) else ''
                _lc = r['末打卡'] if pd.notna(r['末打卡']) else ''
                if not str(_fc).strip() and not str(_lc).strip(): untimely = False
            if untimely:
                _fc2 = _fs(r['首打卡']); _lc2 = _fs(r['末打卡']); _yc2 = _fs(r['异常备注'])
                if _fc2 and _lc2 and (_yc2 == '' or _yc2 == '空白'): untimely = False
        if gong in FORMAL_ATT_WHITELIST:
            status = '正常'; is_abn = False; untimely = False
        # 指定日期白名单（用户 2026-10-22）：特定员工特定日期考勤算作及时确认（保留记录、计为正常/及时）
        if (gong, d.strftime('%Y-%m-%d')) in FORMAL_ATT_DATE_WHITELIST:
            status = '正常'; is_abn = False; untimely = False
        ds = d.strftime('%Y-%m-%d'); ym = d.strftime('%Y-%m')
        recs.append({'major': major, 'region': region, 'wh': str(wh), 'grp': str(grp),
                     'name': str(r['姓名']) if pd.notna(r['姓名']) else '', 'gong': gong,
                     'date': ds, 'ym': ym, 'total': 1, 'normal': 1 if status == '正常' else 0,
                     'abnormal': 1 if is_abn else 0, 'untimely': 1 if untimely else 0})
        if untimely:
            untimely_rows.append({
                'gk': f"{major}|{region}|{str(wh)}|{str(grp)}",
                'row': [str(r['姓名']) if pd.notna(r['姓名']) else '', gong, l4, '—', '—',
                        ds, _fs(r['星期']), _fs(r['当前班次']), _fs(r['首打卡']), _fs(r['末打卡']),
                        _fs(r['考勤状态']), _fs(r['异常备注']), ym, ds],
            })
    return recs, untimely_rows

def agg_formal(recs):
    by_key = {'major': {}, 'detail': {}, 'warehouse': {}, 'group': {}}
    for r in recs:
        m, rg, w, g = r['major'], r['region'], r['wh'], r['grp']
        for key, st, base in (
            (m, by_key['major'], {'name': m}),
            (m + '|' + rg, by_key['detail'], {'major': m, 'region': rg}),
            (m + '|' + rg + '|' + w, by_key['warehouse'], {'major': m, 'region': rg, 'wh': w}),
            (m + '|' + rg + '|' + w + '|' + g, by_key['group'], {'major': m, 'region': rg, 'wh': w, 'group': g}),
        ):
            e = st.get(key)
            if e is None: e = dict(base); st[key] = e
            for kk in FORMAL_ATT_KEYS: e[kk] = e.get(kk, 0) + r[kk]
    tot = {kk: sum(x.get(kk, 0) for x in by_key['major'].values()) for kk in FORMAL_ATT_KEYS}
    blk = {'total': tot,
           'major': list(by_key['major'].values()),
           'detail': list(by_key['detail'].values()),
           'warehouse': list(by_key['warehouse'].values()),
           'group': list(by_key['group'].values())}
    blk['total']['timely'] = blk['total']['total'] - blk['total']['untimely']
    for _lvl in ('major', 'detail', 'warehouse', 'group'):
        for _r in blk[_lvl]:
            _r['timely'] = _r['total'] - _r['untimely']
    return blk

# ---------- 劳务工 recs ----------
def col(row, i, default=0):
    return row[i] if i < len(row) else default

def _s(v, t=False):
    if v is None: return '—'
    if isinstance(v, str): return v.strip() or '—'
    if t and hasattr(v, 'strftime'): return v.strftime('%H:%M')
    return str(v)

def _nz(v):
    return isinstance(v, str) and v.strip() != ''

def read_labor_recs():
    from openpyxl import load_workbook
    wb = load_workbook(LABOR_XLS, read_only=True, data_only=True)
    ws = wb['考勤']
    recs = []; untimely = []
    for row in ws.iter_rows(values_only=True):
        wh = col(row, 7); d = col(row, 10)
        if not (isinstance(wh, str) and wh) or not d: continue
        ds = str(d)[:10]
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', ds): continue
        # 离职剔除（用户 2026-10-22）：zt0021903 已于 2026-09 底离职，剔除其 2026-10 全部考勤确认率数据
        if str(col(row, 3)).strip() == 'zt0021903': continue
        # 指定日期剔除（用户 2026-10-22）：法国区四位劳务工对应日期考勤数据剔除
        if (str(col(row, 3)).strip(), ds) in LABOR_ATT_EXCLUDE_DATES: continue
        reg = col(row, 6) if isinstance(col(row, 6), str) else ''
        grp = col(row, 8) if isinstance(col(row, 8), str) and col(row, 8) else '部门直属'
        sjk = int(_nz(col(row, 20))) + int(_nz(col(row, 21)))
        sq = int(_nz(col(row, 31))) + int(_nz(col(row, 34)))
        qr = col(row, 35) if isinstance(col(row, 35), str) else ''
        recs.append({'date': ds, 'major': REGION_TO_MAJOR.get(reg, '其他'), 'region': reg,
                     'wh': wh, 'grp': grp, 'gong': col(row, 3), 'name': col(row, 2),
                     'zg': col(row, 4) if isinstance(col(row, 4), str) else '',
                     'ydk': 2, 'sjk': sjk, 'ybq': sq, 'sjq': sq,
                     'yqr': 1, 'sjqr': 1 if qr in ('已确认', '已复核') else 0, 'ldk': 2 - sjk})
        if qr not in ('已确认', '已复核'):
            untimely.append({'gk': f"{REGION_TO_MAJOR.get(reg,'其他')}|{reg}|{wh}|{grp}",
                             'row': [_s(col(row, 2)), _s(col(row, 3)), _s(col(row,4)), ds, _s(col(row, 18)),
                                     _s(col(row, 20), t=True), _s(col(row, 21), t=True), _s(qr),
                                     _s(col(row, 36)), _s(col(row, 38)), ds[:7], ds]})
    wb.close()
    cap = defaultdict(lambda: [0, 0]); out = []
    for r in recs:
        k = (r['gong'], r['date'])
        uy, us = cap[k]
        ny = min(uy + r['ybq'], 2); ns = min(us + r['sjq'], ny)
        rr = dict(r); rr['ybq'] = ny - uy; rr['sjq'] = ns - us
        cap[k] = [ny, ns]; out.append(rr)
    return out, untimely

def agg_attend_day(recs):
    major, detail, wh, grp = {}, {}, {}, {}
    for r in recs:
        m, rg, w, g = r['major'], r['region'], r['wh'], r['grp']
        for key, store, base in (
            (m, major, {'name': m}),
            ((m, rg), detail, {'major': m, 'region': rg}),
            ((m, rg, w), wh, {'major': m, 'region': rg, 'wh': w}),
            ((m, rg, w, g), grp, {'major': m, 'region': rg, 'wh': w, 'group': g}),
        ):
            e = store.get(key)
            if e is None: e = dict(base); store[key] = e
            for f in ATTEND_METRICS: e[f] = e.get(f, 0) + r[f]
    total = {f: sum(x.get(f, 0) for x in major.values()) for f in ATTEND_METRICS}
    for store in (major, detail, wh, grp):
        for e in store.values(): e['unconfirmed'] = e.get('yqr', 0) - e.get('sjqr', 0)
    total['unconfirmed'] = total['yqr'] - total['sjqr']
    return {'total': total, 'major': list(major.values()), 'detail': list(detail.values()),
            'warehouse': list(wh.values()), 'group': list(grp.values())}

# ---------- 合并工具 ----------
def add_timely(blk):
    blk['total']['timely'] = blk['total']['total'] - blk['total']['untimely']
    for _lvl in ('major', 'detail', 'warehouse', 'group'):
        for _r in blk[_lvl]: _r['timely'] = _r['total'] - _r['untimely']
    return blk

def merge_full_block(base, delta):
    def idx(lst, keyfields):
        d = {}
        for e in lst:
            d[tuple(e.get(f) for f in keyfields)] = e
        return d
    for kk in FORMAL_ATT_KEYS:
        base['total'][kk] = base['total'].get(kk, 0) + delta['total'].get(kk, 0)
    tables = [('major', ['name']), ('detail', ['major', 'region']),
              ('warehouse', ['major', 'region', 'wh']), ('group', ['major', 'region', 'wh', 'group'])]
    for lvl, kf in tables:
        bmap = idx(base[lvl], kf); dmap = idx(delta[lvl], kf)
        for k, de in dmap.items():
            if k in bmap:
                for kk in FORMAL_ATT_KEYS: bmap[k][kk] = bmap[k].get(kk, 0) + de.get(kk, 0)
            else:
                base[lvl].append(dict(de))
    add_timely(base)
    return base

def merge_emp_index(empIndex, empCount, additions):
    for a in additions:
        gk = a['gk']; row = a['row']
        empIndex.setdefault(gk, []).append(row)
        empCount[gk] = empCount.get(gk, 0) + 1
    for gk in list(empIndex.keys()):
        lst = empIndex[gk]
        lst.sort(key=lambda e: e[-1], reverse=True)  # e[-1] = ymd
        if len(lst) > 50: empIndex[gk] = lst[:50]
    return empIndex, empCount

def merge_top_index(topIdx, new_by_gk, metric, min_val=0):
    for gk, news in new_by_gk.items():
        exist = topIdx.get(gk, [])
        by_key = {}
        for e in exist:
            by_key[(e.get('gong'), e.get('wh'), e.get('group'))] = dict(e)
        for ne in news:
            k = (ne.get('gong'), ne.get('wh'), ne.get('group'))
            if k in by_key:
                by_key[k][metric] = by_key[k].get(metric, 0) + ne.get(metric, 0)
            else:
                by_key[k] = dict(ne)
        merged = list(by_key.values())
        # 与基构建/补签 Top10 口径一致：仅展示指标 > min_val 的员工（用户 2026-10-22：未确认数>3）
        merged = [x for x in merged if x.get(metric, 0) > min_val]
        merged.sort(key=lambda x: -x.get(metric, 0))
        topIdx[gk] = merged[:10]
    return topIdx

def ensure_region_order(regionOrder, recs):
    added = []
    for r in recs:
        m = r['major']; rg = r['region']
        if m in regionOrder:
            if rg not in regionOrder[m]:
                regionOrder[m].append(rg); added.append((m, rg))
        else:
            regionOrder[m] = [rg]; added.append((m, rg))
    return added

# ---------- 主流程 ----------
FORMAL_FILES = [
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.16-10.18-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.19-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.20-及时性.xlsx",
]
LABOR_FILES = [
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.16-10.18-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.19-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.20-及时性.xlsx",
]

def main():
    html = open(HTML, encoding='utf-8').read()
    def extract(name):
        pre = "const %s = " % name; i = html.find(pre); nl = html.find("\n", i)
        return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))
    fp = extract("formalAttPayload"); ap = extract("attendPayload")

    # 正式工（合并 10.16-10.18 / 10.19 / 10.20 三个文件，补齐昨日重生成时丢失的日块）
    global FORMAL_XLS
    _all_frecs = []; _all_f_untimely = []
    for _f in FORMAL_FILES:
        FORMAL_XLS = _f
        frs, fu = build_formal_recs()
        _all_frecs.extend(frs); _all_f_untimely.extend(fu)
        print("正式工 read:", _f.split('\\')[-1], len(frs), "行")
    frecs, f_untimely = _all_frecs, _all_f_untimely
    f_dates = sorted(set(r['date'] for r in frecs))
    f_new = [d for d in f_dates if d not in fp['days']]
    print("正式工 文件日期:", f_dates, "新增:", f_new)
    for d in f_new:
        f_day = agg_formal([r for r in frecs if r['date'] == d])
        f_day['warehouse'] = [w for w in f_day['warehouse'] if w.get('untimely', 0) > 0]
        f_day['group'] = [g for g in f_day['group'] if g.get('untimely', 0) > 0]
        fp['data'][d] = f_day
        fp['days'] = sorted(set(fp['days']) | {d})
    f_delta = agg_formal([r for r in frecs if r['date'] in f_new])
    fp['data']['2026-10'] = merge_full_block(fp['data']['2026-10'], f_delta)
    fp['empIndex'], fp['empCount'] = merge_emp_index(fp['empIndex'], fp['empCount'], f_untimely)
    f_top_new = defaultdict(list); f_top_m_new = defaultdict(lambda: defaultdict(list))
    fg = defaultdict(lambda: {'name':'','gong':'','major':'','region':'','wh':'','group':'','untimely':0})
    for r in frecs:
        if r['date'] not in f_new: continue
        if r['untimely'] <= 0: continue
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = fg[k]; a['name']=r['name']; a['gong']=r['gong']; a['major']=r['major']
        a['region']=r['region']; a['wh']=r['wh']; a['group']=r['grp']; a['untimely']+=r['untimely']
    for (m,rg,w,g,gong), a in fg.items():
        ent = {'name':a['name'],'gong':gong,'major':m,'region':rg,'wh':w,'group':g,'untimely':a['untimely']}
        f_top_new[f"{m}|{rg}"].append(ent)
        f_top_m_new[r['ym']][f"{m}|{rg}"].append(ent)
    fp['topEmpIndex'] = merge_top_index(fp['topEmpIndex'], f_top_new, 'untimely', min_val=3)
    for ym in f_top_m_new:
        if ym in fp['topEmpIndexM']:
            fp['topEmpIndexM'][ym] = merge_top_index(fp['topEmpIndexM'][ym], f_top_m_new[ym], 'untimely', min_val=3)
    f_ro_added = ensure_region_order(fp['regionOrder'], [r for r in frecs if r['date'] in f_new])

    # 劳务工（合并 10.16-10.18 / 10.19 / 10.20 三个文件）
    global LABOR_XLS
    _all_lrecs = []; _all_l_untimely = []
    for _f in LABOR_FILES:
        LABOR_XLS = _f
        lrs, lu = read_labor_recs()
        _all_lrecs.extend(lrs); _all_l_untimely.extend(lu)
        print("劳务工 read:", _f.split('\\')[-1], len(lrs), "行")
    lrecs, l_untimely = _all_lrecs, _all_l_untimely
    l_dates = sorted(set(r['date'] for r in lrecs))
    l_new = [d for d in l_dates if d not in ap['days']]
    print("劳务工 文件日期:", l_dates, "新增:", l_new)
    for d in l_new:
        l_day = agg_attend_day([r for r in lrecs if r['date'] == d])
        l_day['warehouse'] = [w for w in l_day['warehouse'] if w.get('unconfirmed', 0) > 0]
        l_day['group'] = [g for g in l_day['group'] if g.get('unconfirmed', 0) > 0]
        ap['data'][d] = l_day
        ap['days'] = sorted(set(ap['days']) | {d})
    ap['empIndex'], ap['empCount'] = merge_emp_index(ap['empIndex'], ap['empCount'], l_untimely)
    l_top_new = defaultdict(list); l_top_m_new = defaultdict(lambda: defaultdict(list))
    l_top_ldk_new = defaultdict(list); l_top_ldk_m_new = defaultdict(lambda: defaultdict(list))
    lg = defaultdict(lambda: {'name':'','gong':'','zg':'','wh':'','group':'','unc':0,'ldk':0})
    for r in lrecs:
        if r['date'] not in l_new: continue
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = lg[k]; a['name']=r['name']; a['gong']=r['gong']; a['zg']=r['zg']; a['wh']=r['wh']; a['group']=r['grp']
        a['unc'] += (r['yqr'] - r['sjqr']); a['ldk'] += r['ldk']
    for (m,rg,w,g,gong), a in lg.items():
        ent = {'name':a['name'],'gong':gong,'zg':a['zg'],'wh':w,'group':g}
        if a['unc'] > 0:
            e1 = dict(ent); e1['unc']=a['unc']; l_top_new[f"{m}|{rg}"].append(e1); l_top_m_new['2026-10'][f"{m}|{rg}"].append(e1)
        if a['ldk'] > 0:
            e2 = dict(ent); e2['ldk']=a['ldk']; l_top_ldk_new[f"{m}|{rg}"].append(e2); l_top_ldk_m_new['2026-10'][f"{m}|{rg}"].append(e2)
    ap['topEmpIndex'] = merge_top_index(ap['topEmpIndex'], l_top_new, 'unc', min_val=3)
    for ym in l_top_m_new:
        if ym in ap['topEmpIndexM']:
            ap['topEmpIndexM'][ym] = merge_top_index(ap['topEmpIndexM'][ym], l_top_m_new[ym], 'unc', min_val=3)
    ap['topEmpIndexLdk'] = merge_top_index(ap['topEmpIndexLdk'], l_top_ldk_new, 'ldk', min_val=3)
    for ym in l_top_ldk_m_new:
        if ym in ap['topEmpIndexLdkM']:
            ap['topEmpIndexLdkM'][ym] = merge_top_index(ap['topEmpIndexLdkM'][ym], l_top_ldk_m_new[ym], 'ldk', min_val=3)
    l_ro_added = ensure_region_order(ap['regionOrder'], [r for r in lrecs if r['date'] in l_new])

    # noteHtml：日期范围 -> 10.20；文件列表追加 10.16-10.18 / 10.19 / 10.20
    fp['noteHtml'] = re.sub(r'10\.1–10\.\d{2}', '10.1–10.20', fp['noteHtml'])
    fp['noteHtml'] = fp['noteHtml'].replace(
        '正式工-考勤记录-10.15-及时性.xlsx</code>',
        '正式工-考勤记录-10.15-及时性.xlsx</code>、<code>正式工-考勤记录-10.16-10.18-及时性.xlsx</code>、<code>正式工-考勤记录-10.19-及时性.xlsx</code>、<code>正式工-考勤记录-10.20-及时性.xlsx</code>')
    ap['noteHtml'] = re.sub(r'10\.1–10\.\d{2}', '10.1–10.20', ap['noteHtml'])
    ap['noteHtml'] = ap['noteHtml'].replace(
        '劳务工-考勤记录-10.15-及时性》',
        '劳务工-考勤记录-10.15-及时性》、《劳务工-考勤记录-10.16-10.18-及时性》、《劳务工-考勤记录-10.19-及时性》、《劳务工-考勤记录-10.20-及时性》')

    def splice(name, obj):
        nonlocal html
        pre = "const %s = " % name; i = html.find(pre); nl = html.find("\n", i)
        new_line = pre + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ";"
        html = html[:i] + new_line + html[nl:]
    splice("formalAttPayload", fp)
    splice("attendPayload", ap)
    open(OUT, "w", encoding="utf-8").write(html)

    # 校验摘要
    print("\n=== 正式工 ===")
    for d in f_new:
        print(f"  day {d} total:", fp['data'][d]['total'])
    print("  month 2026-10 total(更新后):", fp['data']['2026-10']['total'])
    print("  days 末6:", fp['days'][-6:])
    print("  新增 regionOrder:", f_ro_added)
    print("=== 劳务工 ===")
    for d in l_new:
        print(f"  day {d} total:", ap['data'][d]['total'])
    print("  days 末6:", ap['days'][-6:])
    print("  新增 regionOrder:", l_ro_added)
    import os
    print("OUT size:", os.path.getsize(OUT))

if __name__ == '__main__':
    main()
