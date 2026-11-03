# -*- coding: utf-8 -*-
"""
正式工补签率（考勤为基）6-9月 计算 + 独立 HTML 报表生成。
口径：
  分母 = 该区域(三级/四级部门)考勤总记录数（人日），剔除 EXCLUDE_MAJORS / EXCLUDE_REGIONS 整类。
  分子 = 考勤记录中「已补签通过」的人日：
         - 与补签流程按 (工号, 考勤日期) JOIN，取 审批状态='已完成' 的已批补签；
         - 再剔除：① 西班牙区 补签事由='其他'（整体剔除）；② 备注/事由属客观原因（考勤机故障、网络不好、工牌、系统、消防、司机在外、入职当天等）。
  天然按 (工号,考勤日期) 去重（考勤记录人日唯一）。
"""
import pandas as pd, numpy as np, json, re, warnings, os
warnings.filterwarnings('ignore')

D = r"D:/Documents/Downloads"
OUT_DIR = r"C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58"

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

MONTHS = {
    '2026-06': {'att': [os.path.join(D, '正式工-6月考勤记录.xlsx')],
                'proc': os.path.join(D, '补签流程-6月.xlsx'), 'label': '6月'},
    '2026-07': {'att': [os.path.join(D, '正式工-7月考勤记录.xlsx')],
                'proc': os.path.join(D, '补签流程-7月.xlsx'), 'label': '7月'},
    '2026-08': {'att': [os.path.join(D, '正式工-8月考勤日报表-20261010.xlsx')],
                'proc': os.path.join(D, '补签流程-8月-正式工.xlsx'), 'label': '8月'},
    '2026-09': {'att': [os.path.join(D, '考勤记录 -9月.xlsx'), os.path.join(D, '考勤记录 - 9.1-9.3.xlsx')],
                'proc': os.path.join(D, '补签流程-9月-正式工.xlsx'), 'label': '9月'},
}

def load_att(files):
    dfs = []
    for f in files:
        if '8月考勤日报表' in f:
            cols = ['考勤日期','姓名','工号','二级部门','三级部门','四级部门','五级部门','六级部门',
                    '封存状态','考勤状态','首打卡时间','末打卡时间','补签首打卡时间','补签末打卡时间']
            df = pd.read_excel(f, sheet_name=0, usecols=lambda c: c in cols)
            df = df.rename(columns={'首打卡时间':'首打卡','末打卡时间':'末打卡',
                                    '补签首打卡时间':'补签首打卡','补签末打卡时间':'补签末打卡'})
        else:
            df = pd.read_excel(f, sheet_name=0)
            keep = ['姓名','工号','二级部门','三级部门','四级部门','五级部门','六级部门','考勤日期',
                    '封存状态','考勤状态','补签状态','首打卡','末打卡','补签首打卡','补签末打卡','备注']
            df = df[[c for c in keep if c in df.columns]]
        for c in ['工号']:
            df[c] = df[c].map(norm_id)
        dfs.append(df)
    out = pd.concat(dfs, ignore_index=True)
    out = out.drop_duplicates(subset=['工号','考勤日期'], keep='first').copy()
    out['考勤日期'] = pd.to_datetime(out['考勤日期'], errors='coerce')
    return out

def build_month(ym):
    cfg = MONTHS[ym]
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
    # 补签流程
    proc = pd.read_excel(cfg['proc'], sheet_name=0)
    proc['工号'] = proc['工号'].map(norm_id)
    proc['补签日期'] = pd.to_datetime(proc['补签日期'], errors='coerce')
    proc['审批状态'] = proc['审批状态'].astype(str).str.strip()
    proc['补签事由'] = proc['补签事由'].astype(str).str.strip()
    appr = proc[proc['审批状态'] == '已完成'].copy()
    # approved dict: (工号, date) -> (事由, 备注)
    adict = {}
    for _, r in appr.iterrows():
        k = (r['工号'], r['补签日期'].normalize() if pd.notna(r['补签日期']) else None)
        if k[1] is None:
            continue
        adict[k] = (r['补签事由'], r['备注'] if pd.notna(r['备注']) else '')
    att['_date'] = att['考勤日期'].map(lambda x: x.normalize() if pd.notna(x) else None)
    att['_k'] = list(zip(att['工号'], att['_date']))
    def resolve(k):
        if k in adict:
            return adict[k]
        return (None, '')
    res = att['_k'].map(resolve)
    att['_reason'] = res.map(lambda t: t[0])
    att['_remark'] = res.map(lambda t: t[1])
    att['is_appr'] = att['_k'].isin(set(adict.keys()))
    spain_other = (att['四级部门'] == '西班牙区') & (att['_reason'] == '其他')
    obj_excl = att.apply(lambda x: is_top_exclude(x['_reason'], x['_remark']), axis=1)
    att['is_resign'] = att['is_appr'] & ~spain_other & ~obj_excl
    # aggregations
    den = len(att); num = int(att['is_resign'].sum())
    def agg(keys):
        g = att.groupby(keys).agg(num=('is_resign','sum'), den=('is_resign','size')).reset_index()
        g['num'] = g['num'].astype(int)
        g['den'] = g['den'].astype(int)
        g['rate'] = (g['num']/g['den']*100).round(1)
        return g
    major = agg(['三级部门']).rename(columns={'三级部门':'name'})
    major['pct_total'] = (major['num']/den*100).round(1)
    major['__o'] = major['name'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    major = major.sort_values('__o').drop(columns='__o').reset_index(drop=True)
    detail = agg(['三级部门','四级部门']).rename(columns={'三级部门':'major','四级部门':'region'})
    major_tot = major.set_index('name')['num'].to_dict()
    major_den = major.set_index('name')['den'].to_dict()
    detail['pct_major'] = (detail['num']/detail['major'].map(major_tot).replace(0,np.nan)*100).round(1)
    detail['__mo'] = detail['major'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    detail['__ro'] = [REGION_ORDER.get(m,[]).index(r) if r in REGION_ORDER.get(m,[]) else len(REGION_ORDER.get(m,[])) for m,r in zip(detail['major'],detail['region'])]
    detail = detail.sort_values(['__mo','__ro']).drop(columns=['__mo','__ro']).reset_index(drop=True)
    wh = agg(['三级部门','四级部门','五级部门']).rename(columns={'三级部门':'major','四级部门':'region','五级部门':'wh'})
    reg_den = detail.set_index(['major','region'])['den'].to_dict()
    wh['pct_region'] = (wh['num']/wh.apply(lambda r: reg_den.get((r['major'],r['region']),np.nan),axis=1).replace(0,np.nan)*100).round(1)
    wh['__mo'] = wh['major'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    wh['__ro'] = [REGION_ORDER.get(m,[]).index(r) if r in REGION_ORDER.get(m,[]) else len(REGION_ORDER.get(m,[])) for m,r in zip(wh['major'],wh['region'])]
    wh['__wo'] = wh['wh'].map(lambda n: int(re.search(r'(\d+)',str(n)).group(1)) if re.search(r'(\d+)',str(n)) else 10**9)
    wh = wh.sort_values(['__mo','__ro','__wo']).drop(columns=['__mo','__ro','__wo']).reset_index(drop=True)
    grp = agg(['三级部门','四级部门','五级部门','六级部门']).rename(columns={'三级部门':'major','四级部门':'region','五级部门':'wh','六级部门':'group'})
    wh_den = wh.set_index(['major','region','wh'])['den'].to_dict()
    grp['pct_wh'] = (grp['num']/grp.apply(lambda r: wh_den.get((r['major'],r['region'],r['wh']),np.nan),axis=1).replace(0,np.nan)*100).round(1)
    grp['__mo'] = grp['major'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    grp['__ro'] = [REGION_ORDER.get(m,[]).index(r) if r in REGION_ORDER.get(m,[]) else len(REGION_ORDER.get(m,[])) for m,r in zip(grp['major'],grp['region'])]
    grp['__wo'] = grp['wh'].map(lambda n: int(re.search(r'(\d+)',str(n)).group(1)) if re.search(r'(\d+)',str(n)) else 10**9)
    grp['__go'] = grp['group'].map(lambda n: int(re.search(r'(\d+)',str(n)).group(1)) if re.search(r'(\d+)',str(n)) else 10**9)
    grp = grp.sort_values(['__mo','__ro','__wo','__go']).drop(columns=['__mo','__ro','__wo','__go']).reset_index(drop=True)
    # employee detail (考勤为基明细)
    er = att[att['is_resign']].groupby(['工号','姓名','三级部门','四级部门','五级部门','六级部门']).size().reset_index(name='days')
    emp = {}
    for _, r in er.iterrows():
        g = r['工号']; nm = r['姓名']
        key = (g, nm)
        if key not in emp:
            emp[key] = {'gong':g,'name':nm,'major':r['三级部门'],'region':r['四级部门'],'wh':r['五级部门'],'group':r['六级部门'],'days':0}
        emp[key]['days'] += int(r['days'])
    emp_list = list(emp.values())
    emp_list.sort(key=lambda e: (-e['days'], e['gong']))
    # 日级明细（供主报表组下员工展开：补签日期/事由/备注）
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
        'total': {'num': num, 'den': den, 'rate': round(num/den*100,1) if den else 0, 'raw_rows': n0, 'inscope': n1},
        'major': major.to_dict('records'),
        'detail': detail.to_dict('records'),
        'warehouse': wh.to_dict('records'),
        'group': grp.to_dict('records'),
        'emp': emp_list,
        'emp_detail': emp_detail,
    }
    print(f"[{ym}] raw={n0} inscope={n1} den={den} num={num} rate={block['total']['rate']}%  emp={len(emp_list)} detail={len(emp_detail)}")
    return block

data = {}
for ym in MONTHS:
    data[ym] = build_month(ym)

# 汇总 (6-9月合并)
def combine(yms):
    tot_num = sum(data[y]['total']['num'] for y in yms)
    tot_den = sum(data[y]['total']['den'] for y in yms)
    def combine_dim(field, keys):
        rows = []
        cache = {}
        for y in yms:
            for r in data[y][field]:
                k = tuple(r[k] for k in keys)
                if k not in cache:
                    cache[k] = {kk: r[kk] for kk in keys}
                    cache[k]['num'] = 0; cache[k]['den'] = 0
                cache[k]['num'] += r['num']; cache[k]['den'] += r['den']
        for k,v in cache.items():
            v['rate'] = round(v['num']/v['den']*100,1) if v['den'] else 0
            rows.append(v)
        return rows
    major = combine_dim('major', ['name'])
    major.sort(key=lambda r: (MAJOR_IDX.get(r['name'],99), -r['num']))
    for r in major: r['pct_total'] = round(r['num']/tot_den*100,1)
    detail = combine_dim('detail', ['major','region'])
    detail.sort(key=lambda r: (MAJOR_IDX.get(r['major'],99), r['region']))
    mt = {r['name']:r['num'] for r in major}
    for r in detail: r['pct_major'] = round(r['num']/mt.get(r['major'],0)*100,1) if mt.get(r['major'],0) else 0
    wh = combine_dim('warehouse', ['major','region','wh'])
    wh.sort(key=lambda r: (MAJOR_IDX.get(r['major'],99), r['region'], r['wh']))
    rd = {(r['major'],r['region']):r['den'] for r in detail}
    for r in wh: r['pct_region'] = round(r['num']/rd.get((r['major'],r['region']),0)*100,1) if rd.get((r['major'],r['region']),0) else 0
    grp = combine_dim('group', ['major','region','wh','group'])
    grp.sort(key=lambda r: (MAJOR_IDX.get(r['major'],99), r['region'], r['wh'], r['group']))
    wd = {(r['major'],r['region'],r['wh']):r['den'] for r in wh}
    for r in grp: r['pct_wh'] = round(r['num']/wd.get((r['major'],r['region'],r['wh']),0)*100,1) if wd.get((r['major'],r['region'],r['wh']),0) else 0
    emp = {}
    for y in yms:
        for e in data[y]['emp']:
            k = (e['gong'], e['name'])
            if k not in emp: emp[k] = dict(e)
            else: emp[k]['days'] += e['days']
    emp_list = sorted(emp.values(), key=lambda e:(-e['days'], e['gong']))
    # 日级明细合并（带月份前缀避免跨月键冲突；major 取首见）
    det = {}
    for y in yms:
        for e in data[y]['emp_detail']:
            k = (e['gong'], e['date'])
            if k in det: continue
            det[k] = dict(e)
    detail_list = sorted(det.values(), key=lambda e:(e['major'], e['region'], e['wh'], e['group'], e['gong'], e['date']))
    return {'total':{'num':tot_num,'den':tot_den,'rate':round(tot_num/tot_den*100,1),'raw_rows':sum(data[y]['total']['raw_rows'] for y in yms),'inscope':tot_den},
            'major':major,'detail':detail,'warehouse':wh,'group':grp,'emp':emp_list,'emp_detail':detail_list}

data['2026-06~09'] = combine(['2026-06','2026-07','2026-08','2026-09'])
print(f"[汇总] den={data['2026-06~09']['total']['den']} num={data['2026-06~09']['total']['num']} rate={data['2026-06~09']['total']['rate']}%")

payload = {
    'meta': {
        'scope': '正式工；剔除整类：' + '、'.join(EXCLUDE_MAJORS) + '；剔除区域：' + '、'.join(EXCLUDE_REGIONS),
        'numerator': "考勤记录中「已补签通过」的人日 = 与补签流程按(工号,考勤日期) JOIN 取 审批状态='已完成'，再剔除：西班牙区 补签事由='其他'（整体） + 备注/事由属客观原因（考勤机故障/网络不好/工牌/系统/消防/司机在外/入职当天等）",
        'denominator': '该区域考勤总记录数（人日），即范围内全部考勤行（含封存），按(工号,考勤日期)天然去重',
        'months': ['2026-06','2026-07','2026-08','2026-09','2026-06~09'],
        'months_label': {'2026-06':'6月','2026-07':'7月','2026-08':'8月','2026-09':'9月','2026-06~09':'汇总(6-9月)'},
        'major_order': MAJOR_ORDER,
        'region_order': REGION_ORDER,
    },
    'data': data,
}
with open(os.path.join(OUT_DIR, '_formal_attend_rate.json'), 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False)
print("JSON written.")
