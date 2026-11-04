# -*- coding: utf-8 -*-
"""V16 增量注入 (2026-11-04):
(A) 劳务工考勤确认及时率: 增量加入 洛杉矶19号仓(TT) 2026-10-30~10.31 (LA19 夜班修正文件)。
    重建 10.30/10.31 日块 = 现有非LA19(已发布) + LA19; 累加 2026-10 月块;
    LA19 全部 已复核/正常 => 无新增 unconfirmed/ldk => empIndex/top 不变。
(B) 正式工考勤确认及时率: 新增「直接上级当天休假豁免」规则。
    根据 休假流程(已完成或审批中, 1h<=时长<=24h) + 花名册(直接上级工号) 匹配：
    若正式工某日考勤异常(untimely)且其直接上级当日休假 => 该异常不计(仅正式工)。
    从 empIndex 移除对应行, 并同步扣减 日块/月块/Top 的 untimely, 重算 timely。

外科手术式: 不重跑 gen_buqian_stats.py, 不抹除 6/7/8/9 月与既有 T+1 数据;
只改 attendPayload(劳务工) 与 formalAttPayload(正式工) 两个 const, 右->左替换。
"""
import json, re, shutil, os
import _inject_1025 as I25
import pandas as pd
from openpyxl import load_workbook
from collections import defaultdict, Counter

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
OUT = WS + r"\_injected_1104.html"
BAK = WS + r"\补签流程_补签统计_1104_bak.html"

LA19_FILE = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.30-10.31-及时性（仅洛杉矶19号仓）.xlsx"
NONLA19_1030 = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.30-10.31-及时性（不含洛杉矶19号仓）.xlsx"
F_LEAVE = r"D:\Documents\Downloads\休假流程-截止10.31.xlsx"
F_ROSTER = r"D:\Documents\Downloads\花名册 -截止11.4.xlsx"

LA19_WH = I25.LA19_WH
ATTEND_METRICS = I25.ATTEND_METRICS

# ---------------- 工具 ----------------
def extract(html, name):
    pre = "const %s = " % name; i = html.find(pre)
    if i < 0:
        pre = "var %s = " % name; i = html.find(pre)
    nl = html.find("\n", i)
    return json.loads(html[i:nl][len(pre):].rstrip().rstrip(";"))

def splice(html, name, obj):
    pre = "const %s = " % name; i = html.find(pre)
    if i < 0:
        pre = "var %s = " % name; i = html.find(pre)
    nl = html.find("\n", i)
    new_line = pre + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ";"
    return html[:i] + new_line + html[nl:]

def merge_labor_block(base, delta):
    for f in ATTEND_METRICS:
        base['total'][f] = base['total'].get(f, 0) + delta['total'].get(f, 0)
    tables = [('major', ['name']), ('detail', ['major', 'region']),
              ('warehouse', ['major', 'region', 'wh']), ('group', ['major', 'region', 'wh', 'group'])]
    for lvl, kf in tables:
        bmap = {tuple(e.get(x) for x in kf): e for e in base[lvl]}
        for de in delta[lvl]:
            k = tuple(de.get(x) for x in kf)
            if k in bmap:
                for f in ATTEND_METRICS:
                    bmap[k][f] = bmap[k].get(f, 0) + de.get(f, 0)
            else:
                base[lvl].append(dict(de))
    for store in (base['major'], base['detail'], base['warehouse'], base['group']):
        for e in store:
            e['unconfirmed'] = e.get('yqr', 0) - e.get('sjqr', 0)
    base['total']['unconfirmed'] = base['total']['yqr'] - base['total']['sjqr']
    return base

def _top_from(recs):
    top_unc = defaultdict(list); top_ldk = defaultdict(list)
    lg = defaultdict(lambda: {'name':'','gong':'','zg':'','wh':'','group':'','unc':0,'ldk':0})
    for r in recs:
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = lg[k]; a['name']=r['name']; a['gong']=r['gong']; a['zg']=r['zg']; a['wh']=r['wh']; a['group']=r['grp']
        a['unc'] += (r['yqr']-r['sjqr']); a['ldk'] += r['ldk']
    for (m,rg,w,g,gong), a in lg.items():
        ent = {'name':a['name'],'gong':gong,'zg':a['zg'],'wh':w,'group':g}
        if a['unc'] > 0:
            e1 = dict(ent); e1['unc'] = a['unc']; top_unc[f"{m}|{rg}"].append(e1)
        if a['ldk'] > 0:
            e2 = dict(ent); e2['ldk'] = a['ldk']; top_ldk[f"{m}|{rg}"].append(e2)
    return top_unc, top_ldk

# ---------------- 主流程 ----------------
def main():
    html = open(HTML, encoding='utf-8').read()
    if not os.path.exists(BAK):
        shutil.copy(HTML, BAK); print("备份 ->", BAK)
    fp = extract(html, "formalAttPayload"); ap = extract(html, "attendPayload")

    # ============================================================
    # (A) 劳务工 LA19 10.30~10.31 增量
    # ============================================================
    print("\n================ (A) 劳务工 LA19 10.30-10.31 ================")
    nonla19, _ = I25.read_labor_recs(NONLA19_1030, exclude_la19=False, read_only=True)
    la19, la19_untimely = I25.read_labor_recs(LA19_FILE, exclude_la19=False, read_only=False)
    la19 = [r for r in la19 if r['wh'] == LA19_WH]
    print("  NONLA19 行:", len(nonla19), " LA19(过滤后)行:", len(la19),
          " LA19 未确认(应=0):", sum(r['yqr']-r['sjqr'] for r in la19),
          " LA19 ldk:", sum(r['ldk'] for r in la19))
    for d in ('2026-10-30', '2026-10-31'):
        base = [r for r in nonla19 if r['date'] == d]
        add = [r for r in la19 if r['date'] == d]
        blk = I25.agg_attend_day(base + add)
        # 保真校验: 仅 nonLA19 部分 应等于现有线上块
        chk = I25.agg_attend_day(base)
        cur = ap['data'][d]['total']
        same = all(chk['total'].get(f)==cur.get(f) for f in ATTEND_METRICS)
        blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed',0)>0]
        blk['group'] = [g for g in blk['group'] if g.get('unconfirmed',0)>0]
        ap['data'][d] = blk
        print(f"  {d}: nonLA19保真={same}, 重建后 total.yqr={blk['total']['yqr']} unconfirmed={blk['total']['unconfirmed']} ldk={blk['total']['ldk']}")
    I25.ensure_region_order(ap['regionOrder'], la19)
    # 劳务工 attendPayload 月视图由前端聚合(无月块), 仅改日块即可; empIndex/top 不变(LA19 全确认)
    print("  LA19 untimely 明细(应空):", len(la19_untimely))

    # ============================================================
    # (B) 正式工 直接上级当天休假 豁免
    # ============================================================
    print("\n================ (B) 正式工 上级休假豁免 ================")
    # 1) 花名册: 工号 -> 直接上级工号 (仅正式员工)
    df_r = pd.read_excel(F_ROSTER, sheet_name=0)
    df_r['工号'] = df_r['工号'].astype(str).str.strip()
    df_r['直接上级工号'] = df_r['直接上级工号'].astype(str).str.strip()
    sup_map = {}
    for _, r in df_r[df_r['用工形式'] == '正式员工'].iterrows():
        g = r['工号']; s = r['直接上级工号']
        if g and s and s != 'nan':
            sup_map[g] = s
    print("  正式员工上级映射:", len(sup_map))
    # 2) 休假流程: (申请人工号, 日期) 合格集
    df_l = pd.read_excel(F_LEAVE, sheet_name=0)
    df_l['_st'] = pd.to_datetime(df_l['开始时间'], errors='coerce')
    df_l['_dur'] = pd.to_numeric(df_l['时长'].astype(str).str.replace('小时','',regex=False).str.strip(), errors='coerce')
    df_l['工号'] = df_l['工号'].astype(str).str.strip()
    ok = (df_l['审批状态'].isin(['已完成','审批中'])) & (df_l['_dur']>=1) & (df_l['_dur']<=24) & df_l['_st'].notna()
    leave_set = set()
    for _, r in df_l[ok].iterrows():
        leave_set.add((str(r['工号']).strip(), r['_st'].strftime('%Y-%m-%d')))
    print("  合格休假 (上级工号,日期):", len(leave_set))

    # 3) 计算豁免行, 并构建扣减
    exempt_rows = []  # (gk, gong, ds, ym, major, region, wh, grp)
    removed = 0
    for gk, rows in fp['empIndex'].items():
        parts = gk.split('|', 3)
        if len(parts) != 4: continue
        major, region, wh, grp = parts
        for row in rows:
            gong = str(row[1]).strip(); ds = str(row[5]).strip()[:10]
            sup = sup_map.get(gong)
            if sup and (sup, ds) in leave_set:
                exempt_rows.append((gk, gong, ds, ds[:7], major, region, wh, grp))
    print("  命中豁免行数:", len(exempt_rows))

    # 4) 应用扣减: empIndex 移除 + 日/月/Top 扣减
    # 收集每个 gk 需移除的 (gong,ds) 集合
    remove_map = defaultdict(set)
    for (gk, gong, ds, ym, m, rg, w, g) in exempt_rows:
        remove_map[gk].add((gong, ds))
    # empIndex 移除
    for gk, rs in remove_map.items():
        before = len(fp['empIndex'][gk])
        fp['empIndex'][gk] = [row for row in fp['empIndex'][gk]
                              if (str(row[1]).strip(), str(row[5]).strip()[:10]) not in rs]
        fp['empCount'][gk] = max(0, fp['empCount'].get(gk, 0) - (before - len(fp['empIndex'][gk])))
        fp['empIndex'][gk].sort(key=lambda e: e[-1], reverse=True)
        if len(fp['empIndex'][gk]) > 50:
            fp['empIndex'][gk] = fp['empIndex'][gk][:50]
        if not fp['empIndex'][gk]:
            del fp['empIndex'][gk]
            fp['empCount'].pop(gk, None)
    removed = sum(1 for _ in exempt_rows)
    print("  empIndex 移除行数:", removed)

    # —— 直接按每个豁免记录逐条扣减(精确) ——
    for (gk, gong, ds, ym, m, rg, w, g) in exempt_rows:
        # 日块
        if ds in fp['data']:
            _dec_entry(fp['data'][ds], m, rg, w, g)
        # 月块
        if ym in fp['data']:
            _dec_entry(fp['data'][ym], m, rg, w, g)
        # Top
        gk_region = f"{m}|{rg}"
        for tkey in (fp['topEmpIndex'], fp['topEmpIndexM'].get(ym, {})):
            lst = tkey.get(gk_region)
            if not lst: continue
            for e in lst:
                if e.get('gong')==gong and e.get('wh')==w and e.get('group')==g:
                    e['untimely'] = e.get('untimely',0) - 1

    # 重算所有日/月块 timely, 并过滤日块 warehouse/group(untimely>0)
    for k, blk in fp['data'].items():
        if not isinstance(blk, dict): continue
        blk['total']['timely'] = blk['total']['total'] - blk['total']['untimely']
        for lvl in ('major','detail','warehouse','group'):
            for e in blk.get(lvl, []):
                e['timely'] = e['total'] - e['untimely']
        if re.match(r'^\d{4}-\d{2}-\d{2}$', k):  # 仅日块过滤 warehouse/group
            blk['warehouse'] = [e for e in blk['warehouse'] if e.get('untimely',0)>0]
            blk['group'] = [e for e in blk['group'] if e.get('untimely',0)>0]
    # Top 重新过滤(untimely>3)并排序截断
    for tkey in (fp['topEmpIndex'],):
        for gk_region, lst in tkey.items():
            tkey[gk_region] = _refilter_top(lst)
    for ym, sub in fp['topEmpIndexM'].items():
        for gk_region, lst in sub.items():
            sub[gk_region] = _refilter_top(lst)

    # 月块 2026-10 校验
    print("  月块2026-10 untimely 扣减:", sum(1 for e in exempt_rows if e[3]=='2026-10'))
    print("  涉及日期:", dict(Counter(e[2] for e in exempt_rows)))
    print("  涉及 gk 数:", len(remove_map))

    # ============================================================
    # 写回 (右->左替换两个 const)
    # ============================================================
    print("\n================ 写回 ================")
    # 计算两个 const 在原始 html 中的位置, 右->左替换, 避免位置失效
    m_form = re.search(r"const formalAttPayload = ", html)
    m_lab = re.search(r"const attendPayload = ", html)
    matches = sorted([(m_form, fp), (m_lab, ap)], key=lambda x: x[0].start(), reverse=True)
    for m, obj in matches:
        i = html.find(m.group(0)); nl = html.find("\n", i)
        new_line = m.group(0) + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ";"
        html = html[:i] + new_line + html[nl:]
    open(OUT, "w", encoding="utf-8").write(html)
    print("  写出 ->", OUT, "大小:", os.path.getsize(OUT))

    # ============================================================
    # 校验
    # ============================================================
    print("\n================ 校验 ================")
    h2 = open(OUT, encoding='utf-8').read()
    fp2 = extract(h2, "formalAttPayload"); ap2 = extract(h2, "attendPayload")
    # 劳务工
    print("劳务工 days:", len(ap2['days']), "末3:", ap2['days'][-3:])
    print("  10.30/10.31 日块 total.yqr:", ap2['data']['2026-10-30']['total']['yqr'], ap2['data']['2026-10-31']['total']['yqr'])
    print("  10.30/10.31 unconfirmed:", ap2['data']['2026-10-30']['total']['unconfirmed'], ap2['data']['2026-10-31']['total']['unconfirmed'])
    la30 = next((e for e in ap2['data']['2026-10-30'].get('warehouse',[]) if e.get('wh')==LA19_WH), None)
    la31 = next((e for e in ap2['data']['2026-10-31'].get('warehouse',[]) if e.get('wh')==LA19_WH), None)
    print("  10.30 LA19 在 warehouse 列表(应无, unconfirmed=0):", la30, " 10.31:", la31)
    okl = all(d['yqr']==d['sjqr']+d['unconfirmed'] for d in ap2['data'].values() if isinstance(d,dict) and 'yqr' in d)
    print("  labor 自洽 yqr==sjqr+unconfirmed:", okl)
    jun = [d for d in ap2['days'] if d < '2026-10-01']
    print("  6/7/8/9月日块保留:", len(jun))
    # 正式工
    print("正式工 days:", len(fp2['days']), "末3:", fp2['days'][-3:])
    print("  月块2026-10 untimely:", fp2['data']['2026-10']['total']['untimely'], " timely:", fp2['data']['2026-10']['total']['timely'])
    okf = all(d['timely']==d['total']-d['untimely'] for d in fp2['data'].values() if isinstance(d,dict) and 'timely' in d)
    print("  formal 自洽 timely==total-untimely:", okf)
    print("  empIndex 总未确认行:", sum(len(v) for v in fp2['empIndex'].values()))
    # 验证豁免后: 抽样豁免员工不应再出现在 empIndex
    sample_g = exempt_rows[0][1] if exempt_rows else None
    if sample_g:
        still = [(gk,row[5]) for gk,rows in fp2['empIndex'].items() for row in rows if str(row[1]).strip()==sample_g]
        print(f"  样例豁免工号 {sample_g} 是否仍在 empIndex:", still)

def _dec_entry(blk, m, rg, w, g):
    blk['total']['untimely'] = blk['total'].get('untimely',0) - 1
    for lvl, kf in (('major',['name']),('detail',['major','region']),
                    ('warehouse',['major','region','wh']),('group',['major','region','wh','group'])):
        for e in blk.get(lvl, []):
            if lvl=='major' and e.get('name')==m:
                e['untimely'] -= 1
            elif lvl=='detail' and e.get('major')==m and e.get('region')==rg:
                e['untimely'] -= 1
            elif lvl=='warehouse' and e.get('major')==m and e.get('region')==rg and e.get('wh')==w:
                e['untimely'] -= 1
            elif lvl=='group' and e.get('major')==m and e.get('region')==rg and e.get('wh')==w and e.get('group')==g:
                e['untimely'] -= 1

def _refilter_top(lst):
    out = [e for e in lst if e.get('untimely',0) > 3]
    out.sort(key=lambda x: -x.get('untimely',0))
    return out[:10]

if __name__ == '__main__':
    main()
