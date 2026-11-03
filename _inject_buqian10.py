# -*- coding: utf-8 -*-
"""
手术式注入 2026-10 正式工/劳务工 补签率（考勤为基）。
- 正式工：重算 6-9+10 全部月份（前端从 allEmp 客户端聚合 Top10/明细），整体替换 formalPayload。
- 劳务工：重算 6-9+10 全部月份（empIndex/topEmpIndex 为累计结构必须全量重算），整体替换 laborPayload。
- 注入前校验：重算的 6-9 月份 data 块必须与线上 HTML 现有块逐字段一致，否则中止（保证不破坏既有数据）。
- Excel：重算并重写 13 个补签率 sheet（7 正式工 + 6 劳务工），保留 3 个考勤确认及时性 sheet。
"""
import pandas as pd, numpy as np, json, re, os, warnings, datetime as _dt
from datetime import datetime, time as dt_time
from openpyxl import load_workbook
warnings.filterwarnings('ignore')

WORK = r"C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58"
D = r"D:/Documents/Downloads"
OUT_HTML = os.path.join(WORK, "补签流程_补签统计.html")
OUT_XLSX = os.path.join(WORK, "补签流程_补签统计.xlsx")
BACKUP_HTML = os.path.join(WORK, "补签流程_补签统计_1103_bak.html")

# ===================== helpers（与 gen_buqian_stats.py / _gen_formal_attend_rate.py 完全一致） =====================
MAJOR_ORDER = ['美洲区', '欧洲区', '亚太区', 'FBU HRBP Dept.']
REGION_ORDER = {
    '美洲区': ['新泽西区', '加州区', '亚特兰大区', '芝加哥区', '萨凡纳区', '达拉斯区', '迈阿密区',
             '休斯顿区', '西雅图区', '诺福克区', '印第安纳区', '加拿大区', '墨西哥区',
             '美洲区行政部', '美洲区交付管理部'],
    '欧洲区': ['英国区', '德国区', '捷克区', '法国区', '波兰区', '西班牙区', '意大利区',
             '欧洲区行政部', '欧洲区交付管理部'],
    '亚太区': ['澳洲区', '日本区', '韩国区'],
    'FBU HRBP Dept.': ['新泽西区HRBP部', '加州区HRBP部', '亚特兰大区HRBP部', '芝加哥区HRBP部',
                     '萨凡纳区HRBP部', '达拉斯区HRBP部', '迈阿密区HRBP部', '休斯顿区HRBP部',
                     '西雅图区HRBP部', '诺福克区HRBP部', '印第安纳区HRBP部', '加拿大区HRBP部',
                     '墨西哥区HRBP部', '美洲支持HRBP组',
                     '英国区HRBP部', '德国区HRBP部', '捷克区HRBP部', '法国区HRBP部',
                     '波兰区HRBP部', '西班牙区HRBP部', '意大利区HRBP部',
                     '澳洲区HRBP部', '日本区HRBP部', '韩国区HRBP部'],
}
MAJOR_IDX = {m: i for i, m in enumerate(MAJOR_ORDER)}
EXCLUDE_MAJORS = ['海外销售部', 'FBU财务部', '渠道管理部', 'LD 法务部', 'FBU技术部', '平台业务部', '品牌客户部']
EXCLUDE_REGIONS = ['国内HRBP组', '美洲支持HRBP组', '美洲支持bp组', '欧亚支持bp组', '欧亚支持HRBP组']
OBJ_PATTERNS = [
    r'没有打卡机', r'无打卡机', r'没有考勤机', r'无考勤机',
    r'no\s*clock', r'no\s*punch', r'no\s*attend', r'no\s*badge', r'no\s*id\b', r'not\s*id',
    r'(打卡机|考勤机|闸机).{0,4}(异常|故障|坏|问题|没反应|损坏|失灵|坏了)',
    r'(clock|punch|time\s*clock|attendance)\s*machine.{0,20}(issue|problem|fault|error|fail|broken|not working|didn.?t work|malfunction)',
    r'系统问题', r'系统故障', r'系统异常',
    r'system\s*(issue|problem|error|down|fail|crash|not working)',
    r'无法打卡', r'暂时无法打卡', r'不能打卡', r'没法打卡', r'未能正常打卡', r'无法签到', r'无法上班打卡', r'无法考勤',
    r'cannot\s*clock', r'can.?t\s*clock', r'unable\s*to\s*clock', r'fail\s*to\s*clock', r'no\s*clock\s*in',
    r'消防',
    r'nuevo\s*ingreso', r'\bingreso\b', r'司机在外', r'在外跑业务', r'在外面跑业务', r'在外跑单',
    r'id\s*card', r'inactive\s*id', r'lost\s*card', r'forgot\s*card',
    r'工[牌卡].{0,6}(没|未|丢失|丢)', r'(没|未|丢失|丢).{0,4}工[牌卡]', r'没有工[牌卡]', r'无工[牌卡]',
]
OBJ_RE = [re.compile(p, re.I) for p in OBJ_PATTERNS]
_HRBP = 'FBU HRBP Dept.'

def is_top_exclude(reason, remark):
    reason = '' if pd.isna(reason) else str(reason).strip()
    if reason == '入职当天':
        return True
    if pd.isna(remark):
        return False
    r = str(remark).strip().lower()
    if not r:
        return False
    return any(p.search(r) for p in OBJ_RE)

def norm_id(v):
    if pd.isna(v):
        return ''
    s = str(v).strip()
    if re.fullmatch(r'\d+\.0', s):
        s = s[:-2]
    return s

def region_idx(major, region, major_order=MAJOR_ORDER, region_order=REGION_ORDER):
    if major not in major_order:
        return len(major_order)
    if region not in region_order.get(major, []):
        return len(region_order.get(major, []))
    return region_order[major].index(region)

def wh_num(name):
    m = re.search(r'(\d+)', str(name))
    return int(m.group(1)) if m else 10**9

# ===================== 正式工 补签率（考勤为基） =====================
ROSTER = os.path.join(D, "花名册 - 2026-08-24T185145.634.xlsx")
roster = pd.read_excel(ROSTER, usecols=['工号', '职位', '职级'])
roster = roster.dropna(subset=['工号', '职位']).drop_duplicates('工号', keep='first')
pos_map = roster.set_index('工号')['职位'].to_dict()

FORMAL_MONTHS = {
    '2026-06': {'att': [os.path.join(D, '正式工-6月考勤记录.xlsx')], 'proc': os.path.join(D, '补签流程-6月.xlsx')},
    '2026-07': {'att': [os.path.join(D, '正式工-7月考勤记录.xlsx')], 'proc': os.path.join(D, '补签流程-7月.xlsx')},
    '2026-08': {'att': [os.path.join(D, '正式工-8月考勤日报表-20261010.xlsx')], 'proc': os.path.join(D, '补签流程-8月-正式工.xlsx')},
    '2026-09': {'att': [os.path.join(D, '考勤记录 -9月.xlsx'), os.path.join(D, '考勤记录 - 9.1-9.3.xlsx')], 'proc': os.path.join(D, '补签流程-9月-正式工.xlsx')},
    '2026-10': {'att': [os.path.join(D, '考勤记录 - 正式工-10月.xlsx')], 'proc': os.path.join(D, '补签-正式工-10月.xlsx')},
}

def load_att(files):
    dfs = []
    for f in files:
        if '8月考勤日报表' in f:
            cols = ['考勤日期', '姓名', '工号', '二级部门', '三级部门', '四级部门', '五级部门', '六级部门',
                    '封存状态', '考勤状态', '首打卡时间', '末打卡时间', '补签首打卡时间', '补签末打卡时间']
            df = pd.read_excel(f, sheet_name=0, usecols=lambda c: c in cols)
            df = df.rename(columns={'首打卡时间': '首打卡', '末打卡时间': '末打卡',
                                    '补签首打卡时间': '补签首打卡', '补签末打卡时间': '补签末打卡'})
        else:
            df = pd.read_excel(f, sheet_name=0)
            keep = ['姓名', '工号', '二级部门', '三级部门', '四级部门', '五级部门', '六级部门', '考勤日期',
                    '封存状态', '考勤状态', '补签状态', '首打卡', '末打卡', '补签首打卡', '补签末打卡', '备注']
            df = df[[c for c in keep if c in df.columns]]
        for c in ['工号']:
            df[c] = df[c].map(norm_id)
        dfs.append(df)
    out = pd.concat(dfs, ignore_index=True)
    out = out.drop_duplicates(subset=['工号', '考勤日期'], keep='first').copy()
    out['考勤日期'] = pd.to_datetime(out['考勤日期'], errors='coerce')
    return out

def build_formal_month(ym):
    cfg = FORMAL_MONTHS[ym]
    att = load_att(cfg['att'])
    n0 = len(att)
    att = att[~att['三级部门'].isin(EXCLUDE_MAJORS)]
    att = att[~att['四级部门'].isin(EXCLUDE_REGIONS)]
    att['三级部门'] = att['三级部门'].astype(str).str.strip()
    att['四级部门'] = att['四级部门'].astype(str).str.strip()
    att['五级部门'] = att['五级部门'].astype(str).str.strip()
    att['六级部门'] = att['六级部门'].astype(str).str.strip()
    att['工号'] = att['工号'].map(norm_id)
    n1 = len(att)
    proc = pd.read_excel(cfg['proc'], sheet_name=0)
    proc['工号'] = proc['工号'].map(norm_id)
    proc['补签日期'] = pd.to_datetime(proc['补签日期'], errors='coerce')
    proc['审批状态'] = proc['审批状态'].astype(str).str.strip()
    proc['补签事由'] = proc['补签事由'].astype(str).str.strip()
    appr = proc[proc['审批状态'] == '已完成'].copy()
    adict = {}
    for _, r in appr.iterrows():
        k = (r['工号'], r['补签日期'].normalize() if pd.notna(r['补签日期']) else None)
        if k[1] is None:
            continue
        adict[k] = (r['补签事由'], r['备注'] if pd.notna(r['备注']) else '')
    att['_date'] = att['考勤日期'].map(lambda x: x.normalize() if pd.notna(x) else None)
    att['_k'] = list(zip(att['工号'], att['_date']))
    res = att['_k'].map(lambda k: adict.get(k, (None, '')))
    att['_reason'] = res.map(lambda t: t[0])
    att['_remark'] = res.map(lambda t: t[1])
    att['is_appr'] = att['_k'].isin(set(adict.keys()))
    spain_other = (att['四级部门'] == '西班牙区') & (att['_reason'] == '其他')
    obj_excl = att.apply(lambda x: is_top_exclude(x['_reason'], x['_remark']), axis=1)
    att['is_resign'] = att['is_appr'] & ~spain_other & ~obj_excl
    den = len(att); num = int(att['is_resign'].sum())
    def agg(keys):
        g = att.groupby(keys).agg(num=('is_resign', 'sum'), den=('is_resign', 'size')).reset_index()
        g['num'] = g['num'].astype(int); g['den'] = g['den'].astype(int)
        g['rate'] = (g['num'] / g['den'] * 100).round(1)
        return g
    major = agg(['三级部门']).rename(columns={'三级部门': 'name'})
    major['pct_total'] = (major['num'] / den * 100).round(1)
    major['__o'] = major['name'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    major = major.sort_values('__o').drop(columns='__o').reset_index(drop=True)
    detail = agg(['三级部门', '四级部门']).rename(columns={'三级部门': 'major', '四级部门': 'region'})
    major_tot = major.set_index('name')['num'].to_dict(); major_den = major.set_index('name')['den'].to_dict()
    detail['pct_major'] = (detail['num'] / detail['major'].map(major_tot).replace(0, np.nan) * 100).round(1)
    detail['__mo'] = detail['major'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    detail['__ro'] = [REGION_ORDER.get(m, []).index(r) if r in REGION_ORDER.get(m, []) else len(REGION_ORDER.get(m, [])) for m, r in zip(detail['major'], detail['region'])]
    detail = detail.sort_values(['__mo', '__ro']).drop(columns=['__mo', '__ro']).reset_index(drop=True)
    wh = agg(['三级部门', '四级部门', '五级部门']).rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh'})
    reg_den = detail.set_index(['major', 'region'])['den'].to_dict()
    wh['pct_region'] = (wh['num'] / wh.apply(lambda r: reg_den.get((r['major'], r['region']), np.nan), axis=1).replace(0, np.nan) * 100).round(1)
    wh['__mo'] = wh['major'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    wh['__ro'] = [REGION_ORDER.get(m, []).index(r) if r in REGION_ORDER.get(m, []) else len(REGION_ORDER.get(m, [])) for m, r in zip(wh['major'], wh['region'])]
    wh['__wo'] = wh['wh'].map(wh_num)
    wh = wh.sort_values(['__mo', '__ro', '__wo']).drop(columns=['__mo', '__ro', '__wo']).reset_index(drop=True)
    grp = agg(['三级部门', '四级部门', '五级部门', '六级部门']).rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh', '六级部门': 'group'})
    wh_den = wh.set_index(['major', 'region', 'wh'])['den'].to_dict()
    grp['pct_wh'] = (grp['num'] / grp.apply(lambda r: wh_den.get((r['major'], r['region'], r['wh']), np.nan), axis=1).replace(0, np.nan) * 100).round(1)
    grp['__mo'] = grp['major'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    grp['__ro'] = [REGION_ORDER.get(m, []).index(r) if r in REGION_ORDER.get(m, []) else len(REGION_ORDER.get(m, [])) for m, r in zip(grp['major'], grp['region'])]
    grp['__wo'] = grp['wh'].map(wh_num); grp['__go'] = grp['group'].map(wh_num)
    grp = grp.sort_values(['__mo', '__ro', '__wo', '__go']).drop(columns=['__mo', '__ro', '__wo', '__go']).reset_index(drop=True)
    er = att[att['is_resign']].groupby(['工号', '姓名', '三级部门', '四级部门', '五级部门', '六级部门']).size().reset_index(name='days')
    emp = {}
    for _, r in er.iterrows():
        g = r['工号']; nm = r['姓名']; key = (g, nm)
        if key not in emp:
            emp[key] = {'gong': g, 'name': nm, 'major': r['三级部门'], 'region': r['四级部门'], 'wh': r['五级部门'], 'group': r['六级部门'], 'days': 0}
        emp[key]['days'] += int(r['days'])
    emp_list = sorted(emp.values(), key=lambda e: (-e['days'], e['gong']))
    dr = att[att['is_resign']]
    emp_detail = []
    for _, r in dr.iterrows():
        emp_detail.append({
            'gong': str(r['工号']), 'name': str(r['姓名']), 'major': str(r['三级部门']), 'region': str(r['四级部门']),
            'wh': str(r['五级部门']), 'group': str(r['六级部门']),
            'date': r['_date'].strftime('%Y-%m-%d') if pd.notna(r['_date']) else '',
            'reason': str(r['_reason']) if r['_reason'] else '', 'remark': str(r['_remark'] or ''),
        })
    emp_detail.sort(key=lambda e: (e['major'], e['region'], e['wh'], e['group'], e['gong'], e['date']))
    block = {
        'total': {'num': num, 'den': den, 'rate': round(num / den * 100, 1) if den else 0, 'raw_rows': n0, 'inscope': n1},
        'major': major.to_dict('records'), 'detail': detail.to_dict('records'),
        'warehouse': wh.to_dict('records'), 'group': grp.to_dict('records'),
        'emp': emp_list, 'emp_detail': emp_detail,
    }
    print(f"[正式工 {ym}] raw={n0} inscope={n1} den={den} num={num} rate={block['total']['rate']}%  emp={len(emp_list)} detail={len(emp_detail)}")
    return block

def att_block(block):
    out = {'total': block['total']['den'], 'done': block['total']['num'], 'ing': 0, 'rate': block['total']['rate']}
    out['major'] = [{'name': r['name'], '已完成': r['num'], '审批中': 0, 'total': r['den'], 'pct': r['pct_total'], 'rate': r['rate']} for r in block['major']]
    out['detail'] = [{'major': r['major'], 'region': r['region'], '已完成': r['num'], '审批中': 0, 'total': r['den'], 'pctMajor': r['pct_major'], 'rate': r['rate']} for r in block['detail']]
    out['warehouse'] = [{'major': r['major'], 'region': r['region'], 'wh': r['wh'], '已完成': r['num'], '审批中': 0, 'total': r['den'], 'pctRegion': r['pct_region'], 'rate': r['rate']} for r in block['warehouse'] if r['major'] != _HRBP]
    out['group'] = [{'major': r['major'], 'region': r['region'], 'wh': r['wh'], 'group': r['group'], '已完成': r['num'], '审批中': 0, 'total': r['den'], 'pctWh': r['pct_wh'], 'rate': r['rate']} for r in block['group'] if r['major'] != _HRBP]
    return out

# ===================== 劳务工 补签率（考勤为基） =====================
LABOR_FILES = [
    (os.path.join(D, '劳务工补签-6月.xlsx'), '劳务工-考勤表'),
    (os.path.join(D, '劳务工补签-7月.xlsx'), '劳务工-考勤表'),
    (os.path.join(D, '考勤确认及时性劳务工（08.01-08.31）-.xlsx'), '劳务工-考勤表'),
    (os.path.join(D, '考勤确认及时性劳务工（09.01-09.30）.xlsx'), '劳务工-考勤表'),
    (r'D:/【每月数据处理！！】/3.工时数据处理/2026/10月（新）/1 数据收集/2.劳务工工时-20261102.xlsx', '考勤'),
]
# 补签记录文件（OTWS）跨月映射：月份 -> 文件
LABOR_BUQIAN_REC = {
    '2026-09': os.path.join(D, '劳务工-补签记录-9月.xls'),
    '2026-10': os.path.join(D, '补签-劳务工-10月.xls'),
}

def build_labor_full():
    EUROPE_BASE = {'英国', '德国', '捷克', '法国', '波兰', '西班牙', '意大利'}
    APAC_BASE = {'澳洲', '日本', '韩国'}
    MAJOR_ORDER_L = ['美洲区', '欧洲区', '亚太区']
    def region_to_major(r):
        r = str(r).strip()
        base = r[:-1] if r.endswith('区') else r
        if base in EUROPE_BASE: return '欧洲区'
        if base in APAC_BASE: return '亚太区'
        return '美洲区'
    _labor_cols = ['工号', '员工名称', '工种', '区域', '仓库', '组', '考勤日期', '班次',
                   '首打卡补签时间', '末打卡补签时间', '休息开始补签时间', '休息结束补签时间',
                   '异常原因', '修改原因', '实际补签数', '应打卡数', '应补签数']
    frames = []
    for f, sh in LABOR_FILES:
        wb = load_workbook(f, read_only=True, data_only=True)
        ws = wb[sh]
        it = ws.iter_rows(values_only=True)
        header = list(next(it))
        cidx = {name: i for i, name in enumerate(header)}
        present = [c for c in _labor_cols if c in cidx]
        recs = {c: [] for c in _labor_cols}
        for row in it:
            for c in present:
                recs[c].append(row[cidx[c]] if cidx[c] < len(row) else None)
        wb.close()
        # 缺失列（如 10月文件无 实际补签数/应打卡数/应补签数）补 None 至等长
        if present:
            _n = len(recs[present[0]])
            for c in _labor_cols:
                if len(recs[c]) != _n:
                    recs[c] = [None] * _n
        frames.append(pd.DataFrame(recs))
    L = pd.concat(frames, ignore_index=True)
    # 缺失数值列补 0（10月文件无 实际补签数/应打卡数/应补签数）
    for c in ['实际补签数', '应打卡数', '应补签数']:
        if c not in L.columns:
            L[c] = 0
        else:
            L[c] = pd.to_numeric(L[c], errors='coerce').fillna(0)
    L['三级部门'] = L['区域'].astype(str).map(region_to_major)
    all_regions_set = set(L['区域'].dropna().astype(str).unique())
    major_order_l = [m for m in MAJOR_ORDER_L if m in set(L['三级部门'])]
    region_order_l = {}
    for m in major_order_l:
        ordered = [r for r in REGION_ORDER.get(m, []) if r in all_regions_set]
        extras = [r for r in all_regions_set if region_to_major(r) == m and r not in ordered]
        extras.sort(); region_order_l[m] = ordered + extras
    L = L.rename(columns={'区域': '四级部门', '仓库': '五级部门', '组': '六级部门',
                          '员工名称': '姓名', '工种': '职位', '异常原因': '补签事由', '修改原因': '备注'})
    L['六级部门'] = L['六级部门'].fillna('部门直属')
    L['五级部门'] = L['五级部门'].fillna('部门直属')
    L['补签事由'] = L['补签事由'].fillna('')
    L['备注'] = L['备注'].fillna('')
    L['职位'] = L['职位'].fillna('—')
    L['班次'] = L['班次'].fillna('')
    L['工号'] = L['工号'].map(norm_id)
    _time_cols = ['首打卡补签时间', '末打卡补签时间', '休息开始补签时间', '休息结束补签时间']
    def _fmt_time(v):
        if pd.isna(v) or v is None or v == '':
            return ''
        if isinstance(v, (datetime, dt_time)):
            return v.strftime('%H:%M')
        s = str(v).strip()
        if s.lower() in ('', 'nan', 'none'):
            return ''
        if re.match(r'^\d{1,2}:\d{2}:\d{2}$', s):
            return s[:-3]
        return s
    for c in _time_cols:
        L[c] = L[c].apply(_fmt_time)
    L = L.sort_values(['工号', '考勤日期']).reset_index(drop=True)
    _g = L.groupby(['工号', '考勤日期'])['应补签数']
    _cum = _g.cumsum(); _prev = _cum - L['应补签数']
    L['应补签数'] = np.minimum((2 - _prev).clip(lower=0), L['应补签数'])
    L['实际补签数'] = np.minimum(L['实际补签数'], L['应补签数'])
    L['is_record'] = (L['应补签数'] > 0) | (L['实际补签数'] > 0)
    L['dt'] = pd.to_datetime(L['考勤日期'], errors='coerce')
    L['ym'] = L['dt'].dt.strftime('%Y-%m')
    L['ymd'] = L['dt'].dt.strftime('%Y-%m-%d')
    L['is_repair'] = ((L['首打卡补签时间'].astype(str).str.strip() != '') | (L['末打卡补签时间'].astype(str).str.strip() != ''))
    L['top_exclude'] = L.apply(lambda x: is_top_exclude(x['补签事由'], x['备注']), axis=1)
    L['done_repair'] = L['is_repair'] & (~L['top_exclude'])

    # 跨月补签记录文件剔除口径（9月 / 10月）
    for ym, rec_file in LABOR_BUQIAN_REC.items():
        if not os.path.exists(rec_file):
            continue
        def _clean_reason(v):
            s = '' if pd.isna(v) else str(v).strip()
            return '' if s in ('--', 'nan', 'None') else s
        _br = pd.read_excel(rec_file, sheet_name='OTWS - 打卡数据')
        _br = _br[_br['打卡方式'].astype(str).str.strip() == '补签'].copy()
        _br['_kd'] = pd.to_datetime(_br['打卡时间'], errors='coerce').dt.strftime('%Y-%m-%d')
        _br = _br[_br['_kd'].astype(str).str.startswith(ym)]
        _s = L[L['ym'] == ym]
        _att_key = set(); _region_key = {}
        for _g, _d, _rg, _h1, _h2 in zip(_s['工号'].astype(str).str.strip(), _s['ymd'],
                                         _s['四级部门'].astype(str).str.strip(),
                                         _s['首打卡补签时间'].astype(str), _s['末打卡补签时间'].astype(str)):
            _k = (_g, _d); _region_key[_k] = _rg
            if _h1.strip() not in ('', 'nan', 'None') or _h2.strip() not in ('', 'nan', 'None'):
                _att_key.add(_k)
        _ONBOARD = {'入职当天', '初次报道', '首次报道', '新人报道', '报道'}
        _valid = set(); _excl = {}
        for _g, _kd, _reason, _remark in zip(_br['工号'].astype(str).str.strip(), _br['_kd'],
                                             _br['补签原因'], _br['备注']):
            _k = (_g, _kd)
            if _k not in _att_key:
                continue
            _rg = _region_key.get(_k, '')
            _rr = _clean_reason(_reason)
            if _rr in _ONBOARD:
                _excl['入职当天/报道'] = _excl.get('入职当天/报道', 0) + 1; continue
            if _rg == '西班牙区' and _rr == '其他':
                _excl['西班牙区-其他'] = _excl.get('西班牙区-其他', 0) + 1; continue
            if _rg == '日本区' and _rr == '提前打卡':
                _excl['日本区-提前打卡'] = _excl.get('日本区-提前打卡', 0) + 1; continue
            if is_top_exclude(_reason, _remark):
                _excl['备注客观因素'] = _excl.get('备注客观因素', 0) + 1; continue
            _valid.add(_k)
        _mask = (L['ym'] == ym)
        _keys = list(zip(L.loc[_mask, '工号'].astype(str).str.strip(), L.loc[_mask, 'ymd']))
        L.loc[_mask, 'done_repair'] = [k in _valid for k in _keys]
        print(f"[劳务工 {ym} 新口径] 匹配考勤行且有补签时间后剔除: {_excl}；有效补签人日(全区域去重): {len(_valid)}")

    def agg_period_labor_att(sub):
        MAJOR_IDX_L = {m: i for i, m in enumerate(major_order_l)}
        def _spct(num, den):
            return round(num / den * 100, 1) if den else 0.0
        total = int(len(sub)); done = int(sub['done_repair'].sum())
        out = {'total': total, 'done': done, 'ing': 0, 'rate': _spct(done, total)}
        den_m = sub.groupby('三级部门').size(); num_m = sub.groupby('三级部门')['done_repair'].sum()
        major = []
        for name in den_m.index:
            dn = int(den_m[name]); nm = int(num_m.get(name, 0))
            major.append({'name': name, '已完成': nm, '审批中': 0, 'total': dn, 'pct': _spct(nm, total), 'rate': _spct(nm, dn)})
        major_map = {r['name']: r['total'] for r in major}
        major.sort(key=lambda r: (MAJOR_IDX_L.get(r['name'], len(major_order_l)), -r['total']))
        den_d = sub.groupby(['三级部门', '四级部门']).size(); num_d = sub.groupby(['三级部门', '四级部门'])['done_repair'].sum()
        detail = []
        for (mj, rg) in den_d.index:
            dn = int(den_d[(mj, rg)]); nm = int(num_d.get((mj, rg), 0))
            detail.append({'major': mj, 'region': rg, '已完成': nm, '审批中': 0, 'total': dn, 'pctMajor': _spct(nm, major_map.get(mj, 0)), 'rate': _spct(nm, dn)})
        region_map = {(r['major'], r['region']): r['total'] for r in detail}
        detail.sort(key=lambda r: (MAJOR_IDX_L.get(r['major'], len(major_order_l)), region_idx(r['major'], r['region'], major_order_l, region_order_l)))
        sub_w = sub.copy(); sub_w['五级部门'] = sub_w['五级部门'].fillna('部门直属')
        den_w = sub_w.groupby(['三级部门', '四级部门', '五级部门']).size(); num_w = sub_w.groupby(['三级部门', '四级部门', '五级部门'])['done_repair'].sum()
        warehouse = []
        for (mj, rg, wh) in den_w.index:
            dn = int(den_w[(mj, rg, wh)]); nm = int(num_w.get((mj, rg, wh), 0))
            warehouse.append({'major': mj, 'region': rg, 'wh': wh, '已完成': nm, '审批中': 0, 'total': dn, 'pctRegion': _spct(nm, region_map.get((mj, rg), 0)), 'rate': _spct(nm, dn)})
        wh_map = {(r['major'], r['region'], r['wh']): r['total'] for r in warehouse}
        warehouse.sort(key=lambda r: (MAJOR_IDX_L.get(r['major'], len(major_order_l)), region_idx(r['major'], r['region'], major_order_l, region_order_l), wh_num(r['wh']), -r['total']))
        sub_g = sub.copy(); sub_g['五级部门'] = sub_g['五级部门'].fillna('部门直属'); sub_g['六级部门'] = sub_g['六级部门'].fillna('部门直属')
        den_g = sub_g.groupby(['三级部门', '四级部门', '五级部门', '六级部门']).size(); num_g = sub_g.groupby(['三级部门', '四级部门', '五级部门', '六级部门'])['done_repair'].sum()
        groupp = []
        for (mj, rg, wh, gp) in den_g.index:
            dn = int(den_g[(mj, rg, wh, gp)]); nm = int(num_g.get((mj, rg, wh, gp), 0))
            groupp.append({'major': mj, 'region': rg, 'wh': wh, 'group': gp, '已完成': nm, '审批中': 0, 'total': dn, 'pctWh': _spct(nm, wh_map.get((mj, rg, wh), 0)), 'rate': _spct(nm, dn)})
        groupp.sort(key=lambda r: (MAJOR_IDX_L.get(r['major'], len(major_order_l)), region_idx(r['major'], r['region'], major_order_l, region_order_l), r['wh'], -r['total']))
        out['major'] = major; out['detail'] = detail; out['warehouse'] = warehouse; out['group'] = groupp
        return out

    months_l = sorted(L['ym'].dropna().unique())
    days_l = []
    data_l = {m: agg_period_labor_att(L[L['ym'] == m]) for m in months_l}
    L_done = L[L['done_repair']].copy()
    def _join_time(s):
        return '; '.join(sorted(set(x for x in s if x)))
    empagg = L_done.groupby(['三级部门', '四级部门', '五级部门', '六级部门', '姓名', '工号', '职位', '考勤日期', '班次'], as_index=False).agg(
        首打卡补签时间=('首打卡补签时间', _join_time), 末打卡补签时间=('末打卡补签时间', _join_time))
    empagg['考勤日期'] = empagg['考勤日期'].astype(str)
    empagg = empagg.sort_values('考勤日期', ascending=False)
    EMP_DETAIL_CAP = 50
    empIndex = {}; empCount = {}
    for _, r in empagg.iterrows():
        k = f"{r['三级部门']}|{r['四级部门']}|{r['五级部门']}|{r['六级部门']}"
        empCount[k] = empCount.get(k, 0) + 1
        if len(empIndex.get(k, [])) < EMP_DETAIL_CAP:
            empIndex.setdefault(k, []).append([r['姓名'], r['工号'], r['职位'], r['考勤日期'], r['班次'], r['首打卡补签时间'], r['末打卡补签时间']])
    topagg = L_done.groupby(['三级部门', '四级部门', '工号', '姓名', '职位']).agg(
        补签天数=('done_repair', 'sum'), 主属仓=('五级部门', lambda s: s.value_counts().sort_index().idxmax()), 主属组=('六级部门', lambda s: s.value_counts().sort_index().idxmax())).reset_index()
    topEmpIndex = {}
    for (maj, reg), g in topagg.groupby(['三级部门', '四级部门']):
        g = g[g['补签天数'] > 3].sort_values('补签天数', ascending=False).head(10)
        topEmpIndex[f"{maj}|{reg}"] = [{'count': int(rr['补签天数']), 'done': int(rr['补签天数']), 'ing': 0, 'name': rr['姓名'], 'gong': rr['工号'], 'gongzhong': rr['职位'], 'wh': rr['主属仓'], 'group': rr['主属组']} for _, rr in g.iterrows()]
    topEmpIndexM = {}
    for ym_, sub_m in L_done.groupby('ym'):
        tg_m = sub_m.groupby(['三级部门', '四级部门', '工号', '姓名', '职位']).agg(
            补签天数=('done_repair', 'sum'), 主属仓=('五级部门', lambda s: s.value_counts().sort_index().idxmax()), 主属组=('六级部门', lambda s: s.value_counts().sort_index().idxmax())).reset_index()
        idx_m = {}
        for (maj, reg), g in tg_m.groupby(['三级部门', '四级部门']):
            g = g[g['补签天数'] > 3].sort_values('补签天数', ascending=False).head(10)
            idx_m[f"{maj}|{reg}"] = [{'count': int(rr['补签天数']), 'done': int(rr['补签天数']), 'ing': 0, 'name': rr['姓名'], 'gong': rr['工号'], 'gongzhong': rr['职位'], 'wh': rr['主属仓'], 'group': rr['主属组']} for _, rr in g.iterrows()]
        topEmpIndexM[ym_] = idx_m
    # 全量聚合（Excel 用）
    _full = agg_period_labor_att(L)
    _emp_detail = L_done[['三级部门', '四级部门', '五级部门', '六级部门', '姓名', '工号', '职位', '考勤日期', '补签事由', '备注']].copy()
    _emp_detail['五级部门'] = _emp_detail['五级部门'].replace(['', 'nan', 'None', 'NaN'], '部门直属')
    _emp_detail['六级部门'] = _emp_detail['六级部门'].replace(['', 'nan', 'None', 'NaN'], '部门直属')
    _emp_detail['备注'] = _emp_detail['备注'].replace(['nan', 'None', 'NaN'], '')
    _emp_detail = _emp_detail.rename(columns={'三级部门': '大区', '四级部门': '区域', '五级部门': '仓', '六级部门': '组', '姓名': '姓名', '工号': '工号', '职位': '职位', '考勤日期': '考勤日期', '补签事由': '补签事由', '备注': '备注'})
    _emp_detail['审批状态'] = '已完成'
    att_excel = {'major': _full['major'], 'detail': _full['detail'], 'warehouse': _full['warehouse'], 'group': _full['group'], 'emp_detail': _emp_detail.to_dict('records'), 'top': topEmpIndex}
    print(f"[劳务工 全量] den={_full['total']} done={_full['done']} rate={_full['rate']}% 月份={months_l}")
    return {'months': months_l, 'days': days_l, 'data': data_l, 'empIndex': empIndex, 'empCount': empCount,
            'topEmpIndex': topEmpIndex, 'topEmpIndexM': topEmpIndexM, 'att_excel': att_excel}

# ===================== 主流程 =====================
print("== 计算正式工 6-9+10 ==")
formal_blocks = {ym: build_formal_month(ym) for ym in FORMAL_MONTHS}
formal_data = {ym: att_block(formal_blocks[ym]) for ym in FORMAL_MONTHS}
formal_months = sorted(FORMAL_MONTHS.keys())
allEmp = []
def _clean(v):
    v = str(v).strip(); return '' if v in ('nan', 'None', 'NaN') else v
for ym in formal_months:
    for _e in formal_blocks[ym]['emp_detail']:
        _g = str(_e['gong'])
        allEmp.append({'major': _e['major'], 'region': _e['region'], 'wh': _clean(_e['wh']) or '部门直属', 'group': _clean(_e['group']) or '部门直属',
                       '姓名': _e['name'], '工号': _g, '职位': pos_map.get(_g, '—'), '补签日期': _e['date'], '补签事由': _clean(_e['reason']), '备注': _clean(_e['remark']),
                       '考勤日期': _e['date'], 'ym': ym, 'ymd': _e['date'], 'weight': 1, '审批状态': '已完成', 'top_exclude': False})
print(f"[正式工 allEmp] 总明细条数={len(allEmp)}")

print("== 计算劳务工 6-9+10 ==")
labor = build_labor_full()

# ===================== 读取线上 HTML 并校验 =====================
with open(OUT_HTML, encoding='utf-8') as f:
    html = f.read()
def get_const(name):
    m = re.search(r'const ' + re.escape(name) + r' = (\{.*\})\s*;', html)
    if not m:
        raise RuntimeError('未找到 ' + name)
    return m, json.loads(m.group(1))
m_form, existing_formal = get_const('formalPayload')
m_lab, existing_labor = get_const('laborPayload')

# 校验：重算的 6-9 月份 data 块必须与线上一致（逐字段比对 done/total/rate 及各级聚合条数）
def _norm_block(b):
    return json.dumps(b, ensure_ascii=False, sort_keys=True)
print("== 校验正式工 6-9 与线上一致 ==")
for ym in ['2026-06', '2026-07', '2026-08', '2026-09']:
    if _norm_block(formal_data[ym]) != _norm_block(existing_formal['data'][ym]):
        raise RuntimeError(f"正式工 {ym} 重算块与线上不一致，中止（避免破坏既有数据）")
print("  正式工 6-9 校验通过")
print("== 校验劳务工 6-9 与线上一致 ==")
for ym in ['2026-06', '2026-07', '2026-08', '2026-09']:
    if _norm_block(labor['data'][ym]) != _norm_block(existing_labor['data'][ym]):
        raise RuntimeError(f"劳务工 {ym} 重算块与线上不一致，中止（避免破坏既有数据）")
print("  劳务工 6-9 校验通过")

# ===================== 构造新 payload 并替换 =====================
new_formal = {
    'months': formal_months, 'days': existing_formal['days'],
    'data': formal_data, 'allEmp': allEmp,
    'empKeys': existing_formal['empKeys'], 'empHeaders': existing_formal['empHeaders'],
    'type': 'formal', 'subtitle': existing_formal['subtitle'],
}
new_labor = {
    'months': labor['months'], 'days': labor['days'], 'data': labor['data'],
    'empIndex': labor['empIndex'], 'empCount': labor['empCount'],
    'topEmpIndex': labor['topEmpIndex'], 'topEmpIndexM': labor['topEmpIndexM'],
    'empKeys': existing_labor['empKeys'], 'empHeaders': existing_labor['empHeaders'],
    'type': 'labor', 'subtitle': existing_labor['subtitle'], 'noteHtml': existing_labor['noteHtml'],
}
new_formal_json = json.dumps(new_formal, ensure_ascii=False, separators=(',', ':'))
new_labor_json = json.dumps(new_labor, ensure_ascii=False, separators=(',', ':'))

# 备份
import shutil
shutil.copy2(OUT_HTML, BACKUP_HTML)
print("已备份 HTML ->", BACKUP_HTML)

# 右->左替换，保证前一次替换不改变后一次匹配的位置
_matches = sorted([(m_form, new_formal_json), (m_lab, new_labor_json)], key=lambda x: x[0].start(1), reverse=True)
for _m, _nj in _matches:
    html = html[:_m.start(1)] + _nj + html[_m.end(1):]
with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)
print("已写回 HTML（formalPayload/laborPayload 已含 2026-10）")

# ===================== Excel：重写 13 个补签率 sheet =====================
import openpyxl
XL_SHEETS = ['说明', '大区汇总', '大区_区域明细', '区域_仓明细', '区域_仓_组明细', '组下员工明细', '各区补签Top10员工',
             '劳务工_大区汇总', '劳务工_大区_区域明细', '劳务工_区域_仓明细', '劳务工_区域_仓_组明细', '劳务工_组下员工明细', '劳务工_各区补签Top10员工']
wb = openpyxl.load_workbook(OUT_XLSX)
for s in XL_SHEETS:
    if s in wb.sheetnames:
        del wb[s]
wb.save(OUT_XLSX)

_LMAJOR_ORDER = ['美洲区', '欧洲区', '亚太区']
_lmaj_idx = {m: i for i, m in enumerate(_LMAJOR_ORDER)}
with pd.ExcelWriter(OUT_XLSX, engine='openpyxl', mode='a', if_sheet_exists='new') as xw:
    # ---- 正式工 7 个 sheet ----
    _MONTHS = formal_months
    _maj, _det, _wh, _gp = {}, {}, {}, {}
    _emps = []
    for ym in _MONTHS:
        _b = formal_blocks[ym]
        for r in _b['major']:
            a = _maj.setdefault(r['name'], {'num': 0, 'den': 0}); a['num'] += r['num']; a['den'] += r['den']
        for r in _b['detail']:
            a = _det.setdefault((r['major'], r['region']), {'num': 0, 'den': 0}); a['num'] += r['num']; a['den'] += r['den']
        for r in _b['warehouse']:
            if r['major'] == _HRBP: continue
            a = _wh.setdefault((r['major'], r['region'], r['wh']), {'num': 0, 'den': 0}); a['num'] += r['num']; a['den'] += r['den']
        for r in _b['group']:
            if r['major'] == _HRBP: continue
            a = _gp.setdefault((r['major'], r['region'], r['wh'], r['group']), {'num': 0, 'den': 0}); a['num'] += r['num']; a['den'] += r['den']
        for _e in _b['emp']:
            _emps.append({'major': _e['major'], 'region': _e['region'], 'wh': _e['wh'], 'group': _e['group'], 'gong': str(_e['gong']), 'name': _e['name'], 'days': _e['days']})
    note = pd.DataFrame({'说明': [
        '数据来源：补签流程 6~10月 与 考勤记录（6~10月）按(工号,考勤日期) JOIN；口径（考勤为基）见下。',
        f'生成时间：{_dt.datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '【正式工补签率板块（考勤为基）】分母 = 范围内考勤总记录数（人日，含封存，按 工号+考勤日期 去重）；分子 = 考勤记录中「已补签通过」的人日（JOIN 补签流程 审批状态=已完成），并剔除：① 西班牙区 补签事由=其他（整体）；② 客观原因（考勤机故障/网络/工牌/系统/消防/司机在外/入职当天等）。',
        '补签率 = 已补签数 ÷ 考勤记录总数 × 100%。跨 2026-06~10 累加（10月为本次新增）。',
        '已剔除大区（整类）：海外销售部、FBU财务部、渠道管理部、LD 法务部、FBU技术部、平台业务部、品牌客户部；已剔除区域（HRBP部内）：国内HRBP组、美洲支持HRBP组、美洲支持bp组、欧亚支持bp组、欧亚支持HRBP组。',
        '维度：三级部门（大区）× 四级部门（区域）× 五级部门（仓）× 六级部门（组）。加拿大区归入美洲区。',
        '组下员工明细（考勤为基，日级）：每条=该员工某天被补签通过的考勤人日，含补签日期/补签事由/备注，职位取自花名册，审批状态=已完成。',
        '各区补签 Top10 员工（考勤为基）：按 大区×区域×工号 聚合补签天数（>3 天），各区取前 10，并标主属仓/主属组。',
    ]})
    note.to_excel(xw, sheet_name='说明', index=False)
    _rows = []
    for name, v in _maj.items():
        _rows.append({'大区': name, '考勤记录总数': v['den'], '已补签数': v['num'], '补签率': round(v['num']/v['den']*100, 1) if v['den'] else 0})
    _g = pd.DataFrame(_rows); _g['__o'] = _g['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    _g = _g.sort_values('__o').drop(columns='__o').reset_index(drop=True); _g.to_excel(xw, sheet_name='大区汇总', index=False)
    _rows = []
    for (maj, reg), v in _det.items():
        _rows.append({'大区': maj, '区域': reg, '考勤记录总数': v['den'], '已补签数': v['num'], '补签率': round(v['num']/v['den']*100, 1) if v['den'] else 0})
    _c = pd.DataFrame(_rows); _c['__mo'] = _c['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    _c['__ro'] = [region_idx(m, r) for m, r in zip(_c['大区'], _c['区域'])]
    _c = _c.sort_values(['__mo', '__ro']).drop(columns=['__mo', '__ro']).reset_index(drop=True); _c.to_excel(xw, sheet_name='大区_区域明细', index=False)
    _rows = []
    for (maj, reg, wh), v in _wh.items():
        _rows.append({'大区': maj, '区域': reg, '仓': wh, '考勤记录总数': v['den'], '已补签数': v['num'], '补签率': round(v['num']/v['den']*100, 1) if v['den'] else 0})
    _w = pd.DataFrame(_rows); _w['__mo'] = _w['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    _w['__ro'] = [region_idx(m, r) for m, r in zip(_w['大区'], _w['区域'])]
    _w = _w.sort_values(['__mo', '__ro', '已补签数'], ascending=[True, True, False]).drop(columns=['__mo', '__ro']).reset_index(drop=True); _w.to_excel(xw, sheet_name='区域_仓明细', index=False)
    _rows = []
    for (maj, reg, wh, gp), v in _gp.items():
        _rows.append({'大区': maj, '区域': reg, '仓': wh, '组': gp, '考勤记录总数': v['den'], '已补签数': v['num'], '补签率': round(v['num']/v['den']*100, 1) if v['den'] else 0})
    _p = pd.DataFrame(_rows); _p['__mo'] = _p['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    _p['__ro'] = [region_idx(m, r) for m, r in zip(_p['大区'], _p['区域'])]
    _p = _p.sort_values(['__mo', '__ro', '仓', '已补签数'], ascending=[True, True, True, False]).drop(columns=['__mo', '__ro']).reset_index(drop=True); _p.to_excel(xw, sheet_name='区域_仓_组明细', index=False)
    _edet = []
    for ym in _MONTHS:
        for _e in formal_blocks[ym]['emp_detail']:
            _g = str(_e['gong'])
            _edet.append({'大区': _e['major'], '区域': _e['region'], '仓': _e['wh'], '组': _e['group'], '姓名': _e['name'], '工号': _g, '职位': pos_map.get(_g, '—'), '补签日期': _e['date'], '补签事由': _e['reason'], '备注': _e['remark'], '审批状态': '已完成'})
    _ed = pd.DataFrame(_edet); _ed['仓'] = _ed['仓'].replace(['nan', 'None', 'NaN', ''], '部门直属')
    _ed['组'] = _ed['组'].replace(['nan', 'None', 'NaN', ''], '部门直属'); _ed['备注'] = _ed['备注'].replace(['nan', 'None', 'NaN'], '')
    _ed['__mo'] = _ed['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    _ed['__ro'] = [region_idx(m, r) for m, r in zip(_ed['大区'], _ed['区域'])]
    _ed = _ed.sort_values(['__mo', '__ro', '仓', '组', '工号', '补签日期']).drop(columns=['__mo', '__ro']).reset_index(drop=True); _ed.to_excel(xw, sheet_name='组下员工明细', index=False)
    _top = {}
    for e in _emps:
        k = (e['major'], e['region'], e['gong'], e['name']); o = _top.setdefault(k, {'days': 0, 'wh': {}, 'gp': {}})
        o['days'] += e['days']; o['wh'][e['wh']] = o['wh'].get(e['wh'], 0) + e['days']; o['gp'][e['group']] = o['gp'].get(e['group'], 0) + e['days']
    def _pick(obj):
        best, bc = '', -1
        for kk, vv in obj.items():
            if vv > bc or (vv == bc and str(kk) < str(best)):
                best, bc = kk, vv
        return best
    _by_reg = {}
    for (maj, reg, gong, name), o in _top.items():
        _by_reg.setdefault((maj, reg), []).append({'大区': maj, '区域': reg, '姓名': name, '工号': gong, '职位': pos_map.get(gong, '—'), '主属仓': _pick(o['wh']), '主属组': _pick(o['gp']), '补签天数': o['days']})
    _tp = []
    for (maj, reg), lst in _by_reg.items():
        lst = sorted([x for x in lst if x['补签天数'] > 3], key=lambda x: (-x['补签天数'], x['姓名']))[:10]
        for idx, x in enumerate(lst, 1):
            x['排名'] = idx
        _tp.extend(lst)
    _td = pd.DataFrame(_tp) if _tp else pd.DataFrame(columns=['大区', '区域', '排名', '姓名', '工号', '职位', '主属仓', '主属组', '补签天数'])
    if not _td.empty:
        _td['__mo'] = _td['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
        _td['__ro'] = [region_idx(m, r) for m, r in zip(_td['大区'], _td['区域'])]
        _td = _td.sort_values(['__mo', '__ro', '排名']).drop(columns=['__mo', '__ro']).reset_index(drop=True)
    _td.to_excel(xw, sheet_name='各区补签Top10员工', index=False)
    print("正式工 7 个补签率 sheet 已写")

    # ---- 劳务工 6 个 sheet ----
    _lx = labor['att_excel']
    _lm = pd.DataFrame([{'大区': r['name'], '考勤记录总数': r['total'], '已补签数': r['已完成'], '补签率': r['rate']} for r in _lx['major']])
    _lm['__o'] = _lm['大区'].map(_lmaj_idx).fillna(len(_LMAJOR_ORDER)).astype(int)
    _lm = _lm.sort_values('__o').drop(columns='__o').reset_index(drop=True); _lm.to_excel(xw, sheet_name='劳务工_大区汇总', index=False)
    _ld = pd.DataFrame([{'大区': r['major'], '区域': r['region'], '考勤记录总数': r['total'], '已补签数': r['已完成'], '补签率': r['rate']} for r in _lx['detail']])
    _ld['__o'] = _ld['大区'].map(_lmaj_idx).fillna(len(_LMAJOR_ORDER)).astype(int)
    _ld = _ld.sort_values(['__o', '区域']).drop(columns='__o').reset_index(drop=True); _ld.to_excel(xw, sheet_name='劳务工_大区_区域明细', index=False)
    _lw = pd.DataFrame([{'大区': r['major'], '区域': r['region'], '仓': r['wh'], '考勤记录总数': r['total'], '已补签数': r['已完成'], '补签率': r['rate']} for r in _lx['warehouse']])
    _lw['__o'] = _lw['大区'].map(_lmaj_idx).fillna(len(_LMAJOR_ORDER)).astype(int)
    _lw = _lw.sort_values(['__o', '区域', '仓']).drop(columns='__o').reset_index(drop=True); _lw.to_excel(xw, sheet_name='劳务工_区域_仓明细', index=False)
    _lg = pd.DataFrame([{'大区': r['major'], '区域': r['region'], '仓': r['wh'], '组': r['group'], '考勤记录总数': r['total'], '已补签数': r['已完成'], '补签率': r['rate']} for r in _lx['group']])
    _lg['__o'] = _lg['大区'].map(_lmaj_idx).fillna(len(_LMAJOR_ORDER)).astype(int)
    _lg = _lg.sort_values(['__o', '区域', '仓', '组']).drop(columns='__o').reset_index(drop=True); _lg.to_excel(xw, sheet_name='劳务工_区域_仓_组明细', index=False)
    _le = pd.DataFrame(_lx['emp_detail'])
    if not _le.empty:
        _le['__o'] = _le['大区'].map(_lmaj_idx).fillna(len(_LMAJOR_ORDER)).astype(int)
        _le = _le.sort_values(['__o', '区域', '仓', '组', '工号', '考勤日期']).drop(columns='__o').reset_index(drop=True)
    _le.to_excel(xw, sheet_name='劳务工_组下员工明细', index=False)
    _lt = []
    for rk, emps in _lx['top'].items():
        maj, reg = rk.split('|')
        for i, e in enumerate(emps, 1):
            _lt.append({'大区': maj, '区域': reg, '排名': i, '姓名': e['name'], '工号': e['gong'], '职位': e.get('gongzhong', '—'), '主属仓': e['wh'], '主属组': e['group'], '补签天数': e['count']})
    _lt_df = pd.DataFrame(_lt) if _lt else pd.DataFrame(columns=['大区', '区域', '排名', '姓名', '工号', '职位', '主属仓', '主属组', '补签天数'])
    if not _lt_df.empty:
        _lt_df['__o'] = _lt_df['大区'].map(_lmaj_idx).fillna(len(_LMAJOR_ORDER)).astype(int)
        _lt_df = _lt_df.sort_values(['__o', '区域', '排名']).drop(columns='__o').reset_index(drop=True)
    _lt_df.to_excel(xw, sheet_name='劳务工_各区补签Top10员工', index=False)
    print("劳务工 6 个补签率 sheet 已写")

print("Excel 已更新:", OUT_XLSX)
print("DONE")
