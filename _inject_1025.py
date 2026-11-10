# -*- coding: utf-8 -*-
"""增量注入 2026-10-23~10.25 考勤确认及时率（正式工 + 劳务工）到已发布 HTML，
并修正劳务工 洛杉矶19号仓(TT) 10.1~10.22 夜班考勤数据（用专用晚班文件替换原 LA19 记录）。

关键修正（相对首版）：
 劳务工 attendPayload 实际含 83 个日块（2026-06-01~2026-10-22，含 6/7/8/9 月），
 绝不能全量重建（会误删 6/7/8/9 月数据）。故采用「外科手术式」修正：
  - 6/7/8/9 月日块与索引原样保留；
  - 10.1~10.22 日块用「旧文件剔除 LA19 + 专用晚班文件」重建替换（保真校验确认与原数据逐日一致，仅 LA19 变化）；
  - 10.23~10.25 单日增量注入（来自「不含洛杉矶19号仓」文件）；
  - empIndex / topEmpIndex / topEmpIndexLdk 仅对受影响的 美洲区|加州区 LA19 工号做「减去旧 LA19 贡献」调整
    （unc 旧>0、新=0 → 净减；ldk 旧=新 → 净 0），再增量合并 10.23-10.25。

不输出导出名单（用户要求）。输出 _injected_1025.html。
"""
import json, re, shutil, os
import pandas as pd
from collections import defaultdict
from openpyxl import load_workbook

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
OUT = WS + r"\_injected_1025.html"
BAK = WS + r"\补签流程_补签统计_1025_bak_20261027.html"

# ---------------- 文件路径 ----------------
FORMAL_XLS = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.23-10.25-及时性.xlsx"
LABOR_ADDL = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.23-10.25-及时性（不含洛杉矶19号仓）.xlsx"
LA19_XLS = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.01-10.22-及时性（仅洛杉矶19号仓）.xlsx"
LABOR_OLD_FILES = [
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.1-10.6-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.7-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.8-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.9-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.10-10.12-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.13-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.14-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.15-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.16-10.18-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.19-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.20-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.21-及时性.xlsx",
    r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.22-及时性.xlsx",
]

# ---------------- 口径常量（与 _inject_1022 一致） ----------------
FORMAL_ATT_SHEET = '考勤记录'
FORMAL_ATT_WHITELIST = {'zt0022905'}
FORMAL_ATT_EXCLUDE_OCT = {'zt0021903'}
FORMAL_ATT_EXCLUDE_EMPS = {'zt0022056'}
FORMAL_ATT_DATE_WHITELIST = {('zt0018104','2026-11-06'), ('zt0018494','2026-11-06'), ('zt0018560','2026-11-05'), ('zt0018560','2026-11-06'), ('zt0019658','2026-11-05'), ('zt0021018','2026-10-01'), ('zt0021093','2026-11-05'), ('zt0021269','2026-11-05'), ('zt0021465','2026-11-06'), ('zt0021467','2026-11-05'), ('zt0021467','2026-11-06'), ('zt0021580','2026-10-19'), ('zt0022559','2026-11-06'), ('zt0022871','2026-11-05'), ('zt0022976','2026-11-04'), ('zt0023226','2026-10-22'), ('zt0023226','2026-10-23'), ('zt18183','2026-11-05'), ('zt18183','2026-11-06'), ('zt18183','2026-11-09'), ('zt18561','2026-11-05'), ('zt18561','2026-11-06'), ('zt19696','2026-11-09'), ('zt20567','2026-11-06'), ('zt21645','2026-11-05'), ('zt21645','2026-11-06')}
# 加拿大区 3 仓(卡尔加里1号仓/温哥华2号仓/温哥华3号仓) 11月1-8日 考勤不算异常(计为正常/及时,保留在总数)
FORMAL_ATT_WH_EXCL = {'卡尔加里1号仓', '温哥华2号仓', '温哥华3号仓'}
FORMAL_ATT_WH_EXCL_REGION = '加拿大区'
FORMAL_ATT_WH_EXCL_FROM = '2026-11-01'
FORMAL_ATT_WH_EXCL_TO = '2026-11-08'
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
LA19_WH = '洛杉矶19号仓(TT)'

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

# ---------------- 正式工 recs ----------------
def build_formal_recs(path):
    recs = []; untimely_rows = []
    df = pd.read_excel(path, sheet_name=FORMAL_ATT_SHEET)
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
        if gong in FORMAL_ATT_EXCLUDE_EMPS:
            continue
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
        if (gong, d.strftime('%Y-%m-%d')) in FORMAL_ATT_DATE_WHITELIST:
            status = '正常'; is_abn = False; untimely = False
        if region == FORMAL_ATT_WH_EXCL_REGION and wh in FORMAL_ATT_WH_EXCL and FORMAL_ATT_WH_EXCL_FROM <= d.strftime('%Y-%m-%d') <= FORMAL_ATT_WH_EXCL_TO:
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

# ---------------- 劳务工 recs ----------------
def col(row, i, default=0):
    return row[i] if i < len(row) else default

def _s(v, t=False):
    if v is None: return '—'
    if isinstance(v, str): return v.strip() or '—'
    if t and hasattr(v, 'strftime'): return v.strftime('%H:%M')
    return str(v)

def _nz(v):
    return isinstance(v, str) and v.strip() != ''

def read_labor_recs(path, exclude_la19=False, read_only=True):
    wb = load_workbook(path, read_only=read_only, data_only=True)
    ws = wb['考勤']
    recs = []; untimely = []
    for row in ws.iter_rows(values_only=True):
        wh = col(row, 7); d = col(row, 10)
        if not (isinstance(wh, str) and wh) or not d: continue
        ds = str(d)[:10]
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', ds): continue
        if exclude_la19 and wh == LA19_WH: continue
        if str(col(row, 3)).strip() == 'zt0021903': continue
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
        k = (r['gong'], r['date']); uy, us = cap[k]
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

# ---------------- 合并工具（正式工增量 + 劳务工增量） ----------------
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
        lst = empIndex[gk]; lst.sort(key=lambda e: e[-1], reverse=True)
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

# 对已有 top 列表按 (gong,wh,group) 施加有符号 delta，重新过滤/排序/截断
def adjust_top_list(top_list, delta_map, metric, min_val=3):
    by_key = {}
    for e in top_list:
        by_key[(e.get('gong'), e.get('wh'), e.get('group'))] = dict(e)
    for k, delta in delta_map.items():
        if k in by_key:
            by_key[k][metric] = by_key[k].get(metric, 0) + delta
        # 不在列表中的 LA19 工号无需处理（原未进榜）
    out = [e for e in by_key.values() if e.get(metric, 0) > min_val]
    out.sort(key=lambda x: -x.get(metric, 0))
    return out[:10]

# ---------------- 主流程 ----------------
def main():
    html = open(HTML, encoding='utf-8').read()
    if not os.path.exists(BAK):
        shutil.copy(HTML, BAK); print("备份 ->", BAK)
    def extract(name):
        pre = "const %s = " % name; i = html.find(pre); nl = html.find("\n", i)
        return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))
    fp = extract("formalAttPayload"); ap = extract("attendPayload")

    # ============ 劳务工保真校验：用 13 旧文件原样重建 10.1~10.22 与线上逐日比对 ============
    print("\n=== 劳务工保真校验（10.1~10.22 原样重建 vs 线上，确认仅 LA19 会变）===")
    rebuilt = {}
    for _f in LABOR_OLD_FILES:
        recs, _ = read_labor_recs(_f, exclude_la19=False, read_only=True)
        for d in set(r['date'] for r in recs):
            rebuilt.setdefault(d, []).extend([r for r in recs if r['date'] == d])
    mism = 0
    for d in sorted(rebuilt.keys()):
        if d not in ap['data']:
            print("  WARN 线上缺日块:", d); mism += 1; continue
        blk = agg_attend_day(rebuilt[d]); t_new = blk['total']
        t_cur = ap['data'][d]['total']
        if {k: t_new.get(k) for k in ATTEND_METRICS} != {k: t_cur.get(k) for k in ATTEND_METRICS}:
            print(f"  MISMATCH {d}: 重建={ {k:t_new.get(k) for k in ATTEND_METRICS} } 线上={ {k:t_cur.get(k) for k in ATTEND_METRICS} }")
            mism += 1
    if mism:
        print(f"保真校验失败：{mism} 处不一致，中止写入！"); return
    print("  保真校验通过：10.1~10.22 原样重建与线上逐日总量完全一致。")

    # ============ (A) 正式工 10.23-10.25 增量 ============
    print("\n=== 正式工 10.23-10.25 增量 ===")
    frecs, f_untimely = build_formal_recs(FORMAL_XLS)
    print("  读取:", len(frecs), "行; 未及时:", sum(r['untimely'] for r in frecs))
    f_dates = sorted(set(r['date'] for r in frecs))
    f_new = [d for d in f_dates if d not in fp['days']]
    print("  文件日期:", f_dates, "新增:", f_new)
    for d in f_new:
        f_day = agg_formal([r for r in frecs if r['date'] == d])
        f_day['warehouse'] = [w for w in f_day['warehouse'] if w.get('untimely', 0) > 0]
        f_day['group'] = [g for g in f_day['group'] if g.get('untimely', 0) > 0]
        fp['data'][d] = f_day
        fp['days'] = sorted(set(fp['days']) | {d})
    f_delta = agg_formal([r for r in frecs if r['date'] in f_new])
    fp['data']['2026-10'] = merge_full_block(fp['data']['2026-10'], f_delta)
    fp['empIndex'], fp['empCount'] = merge_emp_index(fp['empIndex'], fp['empCount'], f_untimely)
    f_top_new = defaultdict(list)
    fg = defaultdict(lambda: {'name': '', 'gong': '', 'major': '', 'region': '', 'wh': '', 'group': '', 'untimely': 0})
    for r in frecs:
        if r['date'] not in f_new or r['untimely'] <= 0: continue
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = fg[k]; a['name'] = r['name']; a['gong'] = r['gong']; a['major'] = r['major']
        a['region'] = r['region']; a['wh'] = r['wh']; a['group'] = r['grp']; a['untimely'] += r['untimely']
    for (m, rg, w, g, gong), a in fg.items():
        ent = {'name': a['name'], 'gong': gong, 'major': m, 'region': rg, 'wh': w, 'group': g, 'untimely': a['untimely']}
        f_top_new[f"{m}|{rg}"].append(ent)
    fp['topEmpIndex'] = merge_top_index(fp['topEmpIndex'], f_top_new, 'untimely', min_val=3)
    f_ro_added = ensure_region_order(fp['regionOrder'], [r for r in frecs if r['date'] in f_new])

    # ============ (B)+(C) 劳务工外科手术式修正 ============
    print("\n=== 劳务工修正：保留 6/7/8/9，替换 10.1~10.22(LA19)，新增 10.23~10.25 ===")
    # 1) 10.1~10.22 修正日块（旧文件剔除 LA19 + 专用晚班文件）
    corr_recs = []
    for _f in LABOR_OLD_FILES:
        recs, _ = read_labor_recs(_f, exclude_la19=True, read_only=True)
        corr_recs.extend(recs)
    la19_recs, _ = read_labor_recs(LA19_XLS, exclude_la19=False, read_only=False)
    corr_recs.extend(la19_recs)
    print("  修正用 LA19 晚班 行:", len(la19_recs), "未确认:", sum(r['yqr'] - r['sjqr'] for r in la19_recs))
    corr_days = set(r['date'] for r in corr_recs)
    for d in corr_days:
        if d > '2026-10-22': continue
        blk = agg_attend_day([r for r in corr_recs if r['date'] == d])
        blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed', 0) > 0]
        blk['group'] = [g for g in blk['group'] if g.get('unconfirmed', 0) > 0]
        ap['data'][d] = blk
    ap['days'] = sorted(set(ap['days']) | corr_days)

    # 2) 旧 LA19（10.1~10.22）未确认明细集合 + 旧 LA19 工号级 unc/ldk 贡献
    old_la19_recs = []
    for _f in LABOR_OLD_FILES:
        recs, _ = read_labor_recs(_f, exclude_la19=False, read_only=True)
        old_la19_recs.extend([r for r in recs if r['wh'] == LA19_WH])
    old_la19_unc = defaultdict(int); old_la19_ldk = defaultdict(int); old_la19_untimely = set()
    for r in old_la19_recs:
        k = (r['gong'], r['wh'], r['grp'])
        old_la19_unc[k] += (r['yqr'] - r['sjqr'])
        old_la19_ldk[k] += r['ldk']
        if (r['yqr'] - r['sjqr']) > 0:
            old_la19_untimely.add((str(r['gong']), r['date']))
    # 新 LA19 工号级 ldk（用于 delta）
    new_la19_ldk = defaultdict(int)
    for r in la19_recs:
        new_la19_ldk[(r['gong'], r['wh'], r['grp'])] += r['ldk']
    delta_unc = {k: -v for k, v in old_la19_unc.items()}          # 旧>0 新=0 → 净减
    delta_ldk = {k: new_la19_ldk.get(k, 0) - v for k, v in old_la19_ldk.items()}
    print(f"  旧 LA19 未确认工号-日 明细数(将从 empIndex 移除): {len(old_la19_untimely)}")
    print(f"  受影响 LA19 工号数(unc贡献>0): {len(old_la19_unc)}")

    # 3) empIndex：移除旧 LA19 未确认明细（仅 10.1~10.22，保留 6/7/8/9 LA19）
    removed_emp = 0
    for gk in list(ap['empIndex'].keys()):
        if LA19_WH not in gk: continue
        rows = ap['empIndex'][gk]
        nr = [r for r in rows if (str(r[1]), r[-1]) not in old_la19_untimely]
        removed_emp += len(rows) - len(nr)
        nr.sort(key=lambda e: e[-1], reverse=True)
        if len(nr) > 50: nr = nr[:50]
        ap['empIndex'][gk] = nr
        if gk in ap.get('empCount', {}):
            ap['empCount'][gk] = max(0, ap['empCount'][gk] - (len(rows) - len(nr)))
    print("  empIndex 移除旧 LA19 记录数:", removed_emp)

    # 4) topEmpIndex / topEmpIndexM / Ldk / LdkM：对受影响的 美洲区|加州区 施加 delta
    aff_regions = set()
    for k in delta_unc:
        aff_regions.add('美洲区|加州区')  # LA19 固定 加州区
    for rgk in aff_regions:
        if rgk in ap['topEmpIndex']:
            ap['topEmpIndex'][rgk] = adjust_top_list(ap['topEmpIndex'][rgk], delta_unc, 'unc')
        if rgk in ap['topEmpIndexM'].get('2026-10', {}):
            ap['topEmpIndexM']['2026-10'][rgk] = adjust_top_list(ap['topEmpIndexM']['2026-10'][rgk], delta_unc, 'unc')
        if rgk in ap['topEmpIndexLdk']:
            ap['topEmpIndexLdk'][rgk] = adjust_top_list(ap['topEmpIndexLdk'][rgk], delta_ldk, 'ldk')
        if rgk in ap['topEmpIndexLdkM'].get('2026-10', {}):
            ap['topEmpIndexLdkM']['2026-10'][rgk] = adjust_top_list(ap['topEmpIndexLdkM']['2026-10'][rgk], delta_ldk, 'ldk')
    print("  top 索引调整区域:", aff_regions, " delta_ldk 非零项数(应=0，旧=新):", sum(1 for v in delta_ldk.values() if v != 0))

    # 5) 新增 10.23~10.25（增量注入，不含 LA19）
    addl_recs, addl_untimely = read_labor_recs(LABOR_ADDL, exclude_la19=False, read_only=True)
    print("  10.23-10.25 新增 行:", len(addl_recs), "未确认:", sum(r['yqr'] - r['sjqr'] for r in addl_recs))
    addl_days = sorted(set(r['date'] for r in addl_recs))
    for d in addl_days:
        blk = agg_attend_day([r for r in addl_recs if r['date'] == d])
        blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed', 0) > 0]
        blk['group'] = [g for g in blk['group'] if g.get('unconfirmed', 0) > 0]
        ap['data'][d] = blk
        ap['days'] = sorted(set(ap['days']) | {d})
    ap['empIndex'], ap['empCount'] = merge_emp_index(ap['empIndex'], ap['empCount'], addl_untimely)
    # top 增量
    l_top_new = defaultdict(list); l_top_ldk_new = defaultdict(list)
    lg = defaultdict(lambda: {'name': '', 'gong': '', 'zg': '', 'wh': '', 'group': '', 'unc': 0, 'ldk': 0})
    for r in addl_recs:
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = lg[k]; a['name'] = r['name']; a['gong'] = r['gong']; a['zg'] = r['zg']; a['wh'] = r['wh']; a['group'] = r['grp']
        a['unc'] += (r['yqr'] - r['sjqr']); a['ldk'] += r['ldk']
    for (m, rg, w, g, gong), a in lg.items():
        ent = {'name': a['name'], 'gong': gong, 'zg': a['zg'], 'wh': w, 'group': g}
        if a['unc'] > 0:
            e1 = dict(ent); e1['unc'] = a['unc']; l_top_new[f"{m}|{rg}"].append(e1)
        if a['ldk'] > 0:
            e2 = dict(ent); e2['ldk'] = a['ldk']; l_top_ldk_new[f"{m}|{rg}"].append(e2)
    ap['topEmpIndex'] = merge_top_index(ap['topEmpIndex'], l_top_new, 'unc', min_val=3)
    if '2026-10' in ap['topEmpIndexM']:
        ap['topEmpIndexM']['2026-10'] = merge_top_index(ap['topEmpIndexM']['2026-10'], l_top_new, 'unc', min_val=3)
    ap['topEmpIndexLdk'] = merge_top_index(ap['topEmpIndexLdk'], l_top_ldk_new, 'ldk', min_val=3)
    if '2026-10' in ap['topEmpIndexLdkM']:
        ap['topEmpIndexLdkM']['2026-10'] = merge_top_index(ap['topEmpIndexLdkM']['2026-10'], l_top_ldk_new, 'ldk', min_val=3)
    ensure_region_order(ap.get('regionOrder', {}), addl_recs)

    # ============ noteHtml 更新 ============
    fp['noteHtml'] = re.sub(r'10\.1–10\.\d{2}', '10.1–10.25', fp['noteHtml'])
    if '正式工-考勤记录-10.22-及时性.xlsx</code>' in fp['noteHtml']:
        fp['noteHtml'] = fp['noteHtml'].replace(
            '正式工-考勤记录-10.22-及时性.xlsx</code>',
            '正式工-考勤记录-10.22-及时性.xlsx</code>、<code>正式工-考勤记录-10.23-10.25-及时性.xlsx</code>')
    else:
        print("  WARN: 正式工 noteHtml 未找到 10.22 文件串")
    ap['noteHtml'] = re.sub(r'2026-10\.1–10\.\d{2}', '2026-10.1–10.25', ap['noteHtml'])
    if '、《劳务工-考勤记录-10.22-及时性》' in ap['noteHtml']:
        ap['noteHtml'] = ap['noteHtml'].replace(
            '、《劳务工-考勤记录-10.22-及时性》',
            '、《劳务工-考勤记录-10.22-及时性》、《劳务工-考勤记录-10.23-10.25-及时性（不含洛杉矶19号仓）》')
    else:
        print("  WARN: 劳务工 noteHtml 未找到 10.22 文件串")

    # ============ 写回 ============
    def splice(name, obj):
        nonlocal html
        pre = "const %s = " % name; i = html.find(pre); nl = html.find("\n", i)
        new_line = pre + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ";"
        html = html[:i] + new_line + html[nl:]
    splice("formalAttPayload", fp)
    splice("attendPayload", ap)
    open(OUT, "w", encoding="utf-8").write(html)

    # ============ 校验摘要 ============
    print("\n=== 校验摘要 ===")
    html2 = open(OUT, encoding='utf-8').read()
    def extract2(name):
        pre = "const %s = " % name; i = html2.find(pre); nl = html2.find("\n", i)
        return json.loads(html2[i:nl][len(pre):].rstrip().rstrip(";"))
    fp2 = extract2("formalAttPayload"); ap2 = extract2("attendPayload")
    print("正式工 days 末3:", fp2['days'][-3:], " 10月总量:", fp2['data']['2026-10']['total'])
    print("劳务工 days 数量:", len(ap2['days']), "范围:", ap2['days'][0], "~", ap2['days'][-1])
    # 6/7/8/9 月保留检查
    jun_sep = [d for d in ap2['days'] if d < '2026-10-01']
    print("  6/7/8/9 月日块保留数量(应与BAK一致):", len(jun_sep))
    print("  10.23-10.25 已加入:", [d for d in ('2026-10-23','2026-10-24','2026-10-25') if d in ap2['days']])
    # 法国区保留
    for d in ('2026-10-20', '2026-10-21'):
        fr = next((e for e in ap2['data'][d].get('detail', []) if e.get('region') == '法国区'), None)
        print(f"  劳务工 {d} 法国区 unconfirmed:", fr['unconfirmed'] if fr else None)
    # LA19 修正后
    la19_bad = 0
    for d in ap2['days']:
        if d > '2026-10-22': continue
        for e in ap2['data'][d].get('warehouse', []):
            if e.get('wh') == LA19_WH and e.get('unconfirmed', 0) > 0:
                la19_bad += 1
    print("  LA19 夜班修正后仍有未确认的日块数(应为0):", la19_bad)
    print("OUT size:", os.path.getsize(OUT))

if __name__ == '__main__':
    main()
