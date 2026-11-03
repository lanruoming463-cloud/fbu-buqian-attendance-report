# -*- coding: utf-8 -*-
"""增量注入 2026-10.30~10.31 正式工 + 劳务工 10.29(LA19夜班修正) + 10.30~10.31(非LA19) 到已发布 HTML (V14)。

数据来源:
  - 正式工-考勤记录-10.30-10.31-及时性.xlsx                          (formal, 2026-10-30/31 新日)
  - 劳务工-考勤记录-10.29-及时性（仅洛杉矶19号仓）.xlsx              (labor LA19, 2026-10-29 修正)
  - 劳务工-考勤记录-10.30-10.31-及时性（不含洛杉矶19号仓）.xlsx      (labor 非LA19, 2026-10-30/31 新日)
  - (复用) 劳务工-考勤记录-10.29-及时性（不含洛杉矶19号仓）.xlsx     (labor 非LA19, 2026-10-29 已有块, 用于重建 10.29 = 非LA19+LA19)

外科手术式:
  - 6/7/8/9 月 + 10.1-10.29 既有数据(含 V13 已注入的 10.29 非LA19)全部保留;
  - 劳务工 10.29 重建 = 现有非LA19块(V13) 与 LA19 10.29 修正文件合并(重建日块 + empIndex/tops 仅增量并入 LA19);
  - 劳务工 10.30 + 10.31 新增日块(非LA19);
  - 正式工 10.30 + 10.31 新增日块 + 月块(2026-10)累加；
  - 正式工 zt0023229 全10月剔除(V12已剔除 10.1-10.29；此处过滤其 10.30/31 记录，本文件已无此人记录，保险起见仍过滤)。
复用 _inject_1025 函数与口径。
"""
import json, re, shutil, os
import _inject_1025 as I25
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
OUT = WS + r"\_injected_1030.html"
BAK = WS + r"\补签流程_补签统计_1030_bak.html"

NONLA19_1029 = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.29-及时性（不含洛杉矶19号仓）.xlsx"
LA19_1029    = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.29-及时性（仅洛杉矶19号仓）.xlsx"
NONLA19_1030 = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.30-10.31-及时性（不含洛杉矶19号仓）.xlsx"
FORMAL_1030  = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.30-10.31-及时性.xlsx"

LA19_WH = I25.LA19_WH
EXCL_GONG = 'zt0023229'   # 剔除该人 10月考勤(保险过滤，本文件已无该人记录)

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

def main():
    html = open(HTML, encoding='utf-8').read()
    if not os.path.exists(BAK):
        shutil.copy(HTML, BAK); print("备份 ->", BAK)
    fp = extract(html, "formalAttPayload"); ap = extract(html, "attendPayload")

    # ============ (A) 劳务工 10.29 重建 = 现有非LA19块 + LA19 10.29 ============
    print("\n=== (A) 劳务工 10.29 合并 LA19 修正 ===")
    nonla19_recs, _ = I25.read_labor_recs(NONLA19_1029, exclude_la19=False, read_only=True)
    la19_recs, la19_untimely = I25.read_labor_recs(LA19_1029, exclude_la19=False, read_only=False)
    d = '2026-10-29'
    n29 = [r for r in nonla19_recs if r['date']==d]
    l29 = [r for r in la19_recs if r['date']==d]
    print("  非LA19(10.29) 行:", len(n29), " LA19(10.29) 行:", len(l29),
          " LA19 未确认:", sum(r['yqr']-r['sjqr'] for r in l29), " LA19 ldk:", sum(r['ldk'] for r in l29))
    day_recs = n29 + l29
    blk = I25.agg_attend_day(day_recs)
    blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed',0)>0]
    blk['group'] = [g for g in blk['group'] if g.get('unconfirmed',0)>0]
    ap['data'][d] = blk
    # empIndex: V13 已有非LA19 10.29 行；仅增量并入 LA19(全确认则 untimely 为空)
    ap['empIndex'], ap['empCount'] = I25.merge_emp_index(ap['empIndex'], ap['empCount'], la19_untimely)
    la19_unc, la19_ldk = _top_from(l29)
    ap['topEmpIndex'] = I25.merge_top_index(ap['topEmpIndex'], la19_unc, 'unc', min_val=3)
    if '2026-10' in ap.get('topEmpIndexM', {}):
        ap['topEmpIndexM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexM']['2026-10'], la19_unc, 'unc', min_val=3)
    ap['topEmpIndexLdk'] = I25.merge_top_index(ap['topEmpIndexLdk'], la19_ldk, 'ldk', min_val=3)
    if '2026-10' in ap.get('topEmpIndexLdkM', {}):
        ap['topEmpIndexLdkM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexLdkM']['2026-10'], la19_ldk, 'ldk', min_val=3)
    I25.ensure_region_order(ap.get('regionOrder', {}), l29)
    la_w = next((e for e in blk.get('warehouse',[]) if e.get('wh')==LA19_WH), None)
    print("  10.29 合并后 yqr=%d sjqr=%d unconfirmed=%d ldk=%d  LA19 unconfirmed=%s" % (
        blk['total']['yqr'], blk['total']['sjqr'], blk['total']['unconfirmed'], blk['total']['ldk'],
        la_w['unconfirmed'] if la_w else "(无 LA19)"))

    # ============ (B) 劳务工 10.30 + 10.31 新增(非LA19) ============
    print("\n=== (B) 劳务工 10.30-10.31 新增 ===")
    l30_recs, l30_untimely = I25.read_labor_recs(NONLA19_1030, exclude_la19=False, read_only=True)
    l30_dates = sorted(set(r['date'] for r in l30_recs))
    print("  行:", len(l30_recs), "未确认:", sum(r['yqr']-r['sjqr'] for r in l30_recs), "日期:", l30_dates)
    for d in l30_dates:
        blk = I25.agg_attend_day([r for r in l30_recs if r['date']==d])
        blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed',0)>0]
        blk['group'] = [g for g in blk['group'] if g.get('unconfirmed',0)>0]
        ap['data'][d] = blk
        ap['days'] = sorted(set(ap['days']) | {d})
    ap['empIndex'], ap['empCount'] = I25.merge_emp_index(ap['empIndex'], ap['empCount'], l30_untimely)
    l30_unc, l30_ldk = _top_from(l30_recs)
    ap['topEmpIndex'] = I25.merge_top_index(ap['topEmpIndex'], l30_unc, 'unc', min_val=3)
    if '2026-10' in ap.get('topEmpIndexM', {}):
        ap['topEmpIndexM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexM']['2026-10'], l30_unc, 'unc', min_val=3)
    ap['topEmpIndexLdk'] = I25.merge_top_index(ap['topEmpIndexLdk'], l30_ldk, 'ldk', min_val=3)
    if '2026-10' in ap.get('topEmpIndexLdkM', {}):
        ap['topEmpIndexLdkM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexLdkM']['2026-10'], l30_ldk, 'ldk', min_val=3)
    I25.ensure_region_order(ap.get('regionOrder', {}), l30_recs)
    print("  新增日块:", [d for d in l30_dates if d in ap['days']])

    # ============ (C) 正式工 10.30 + 10.31 新增 ============
    print("\n=== (C) 正式工 10.30-10.31 新增 ===")
    frecs, f_untimely = I25.build_formal_recs(FORMAL_1030)
    # 过滤 zt0023229(10月全剔除)，保险起见
    n_z = sum(1 for r in frecs if r['gong'] == EXCL_GONG)
    frecs = [r for r in frecs if r['gong'] != EXCL_GONG]
    f_untimely = [u for u in f_untimely if not u['row'][1].endswith(EXCL_GONG) and u['row'][1] != EXCL_GONG]
    f_dates = sorted(set(r['date'] for r in frecs))
    print("  读取:", len(frecs)+n_z, "行(剔除 zt0023229 %d 行); 未及时:" % n_z, sum(r['untimely'] for r in frecs), "日期:", f_dates)
    for d in f_dates:
        f_day = I25.agg_formal([r for r in frecs if r['date'] == d])
        f_day['warehouse'] = [w for w in f_day['warehouse'] if w.get('untimely',0)>0]
        f_day['group'] = [g for g in f_day['group'] if g.get('untimely',0)>0]
        fp['data'][d] = f_day
        fp['days'] = sorted(set(fp['days']) | {d})
    fp['data']['2026-10'] = I25.merge_full_block(fp['data']['2026-10'], I25.agg_formal(frecs))
    fp['empIndex'], fp['empCount'] = I25.merge_emp_index(fp['empIndex'], fp['empCount'], f_untimely)
    f_top_new = defaultdict(list)
    fg = defaultdict(lambda: {'name':'','gong':'','major':'','region':'','wh':'','group':'','untimely':0})
    for r in frecs:
        if r['untimely'] <= 0: continue
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = fg[k]; a['name']=r['name']; a['gong']=r['gong']; a['major']=r['major']; a['region']=r['region']; a['wh']=r['wh']; a['group']=r['grp']; a['untimely']+=r['untimely']
    for (m,rg,w,g,gong), a in fg.items():
        ent = {'name':a['name'],'gong':gong,'major':m,'region':rg,'wh':w,'group':g,'untimely':a['untimely']}
        f_top_new[f"{m}|{rg}"].append(ent)
    fp['topEmpIndex'] = I25.merge_top_index(fp['topEmpIndex'], f_top_new, 'untimely', min_val=3)
    I25.ensure_region_order(fp.get('regionOrder', {}), frecs)
    print("  10.30-10.31 total=%d untimely=%d ; 月块2026-10 total=%s" % (
        sum(fp['data'][d]['total']['total'] for d in f_dates),
        sum(fp['data'][d]['total']['untimely'] for d in f_dates),
        fp['data']['2026-10']['total']))

    # ============ 写回 ============
    html = splice(html, "formalAttPayload", fp)
    html = splice(html, "attendPayload", ap)
    open(OUT, "w", encoding="utf-8").write(html)

    # ============ 校验 ============
    print("\n=== 校验摘要 ===")
    h2 = open(OUT, encoding='utf-8').read()
    fp2 = extract(h2, "formalAttPayload"); ap2 = extract(h2, "attendPayload")
    print("正式工 days:", len(fp2['days']), "末3:", fp2['days'][-3:], " 10.30/10.31 in:",
          '2026-10-30' in fp2['days'], '2026-10-31' in fp2['days'])
    print("  月块 2026-10 total:", fp2['data']['2026-10']['total'])
    print("劳务工 days:", len(ap2['days']), "末3:", ap2['days'][-3:], " 10.29/10.30/10.31 in:",
          '2026-10-29' in ap2['days'], '2026-10-30' in ap2['days'], '2026-10-31' in ap2['days'])
    jun = [d for d in ap2['days'] if d < '2026-10-01']
    print("  6/7/8/9月日块保留:", len(jun))
    la = next((e for e in ap2['data']['2026-10-29'].get('warehouse',[]) if e.get('wh')==LA19_WH), None)
    print("  10.29 LA19 unconfirmed:", la['unconfirmed'] if la else "(无 LA19)", "; 10.29 总量:", ap2['data']['2026-10-29']['total'])
    print("  zt0023229 10月剩余 empIndex 行:", sum(1 for k,rs in fp2['empIndex'].items() for r in rs if r[1]==EXCL_GONG and r[13].startswith('2026-10')))
    # 自洽
    ok=all(d['timely']==d['total']-d['untimely'] for d in fp2['data'].values() if 'timely' in d)
    okl=all(d['yqr']==d['sjqr']+d['unconfirmed'] for d in ap2['data'].values() if 'yqr' in d)
    print("  formal 所有块 timely==total-untimely:", ok)
    print("  labor 所有块 yqr==sjqr+unconfirmed:", okl)
    print("OUT size:", os.path.getsize(OUT))

if __name__ == '__main__':
    main()
