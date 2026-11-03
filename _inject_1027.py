# -*- coding: utf-8 -*-
"""增量注入 2026-10-27（正式工） + 2026-10-26/10.27（劳务工）到已发布 HTML (V11)。

数据来源:
  - 正式工-考勤记录-10.27-及时性.xlsx                              (formal, 2026-10-27 新日)
  - 劳务工-考勤记录-10.26-及时性（仅洛杉矶19号仓）.xlsx            (labor LA19, 2026-10-26)
  - 劳务工-考勤记录-10.27-及时性（不含洛杉矶19号仓）.xlsx          (labor 非LA19, 2026-10-27 新日)
  - (复用) 劳务工-考勤记录-10.26-及时性（不含洛杉矶19号仓）.xlsx   (labor 非LA19, 2026-10-26 已有块, 用于重建 10.26 = 非LA19+LA19)

外科手术式（绝不重建全量）:
  - 6/7/8/9 月 + 10.1-10.25 + 10.26(非LA19) 既有数据全部保留;
  - 劳务工 10.26 = 现有非LA19块 与 LA19 10.26 合并(empIndex/top 仅增量并入 LA19 部分, 防重复);
  - 劳务工 10.27 新增日块;
  - 正式工 10.27 新增日块 + 月块(2026-10)累加。
复用 _inject_1025 的函数与口径常量。
"""
import json, re, shutil, os
import _inject_1025 as I25
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
HTML = WS + r"\补签流程_补签统计.html"
OUT = WS + r"\_injected_1027.html"
BAK = WS + r"\补签流程_补签统计_1027_bak.html"

FORMAL_1027 = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\正式工\正式工-考勤记录-10.27-及时性.xlsx"
LA19_1026   = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.26-及时性（仅洛杉矶19号仓）.xlsx"
LABOR_1027  = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.27-及时性（不含洛杉矶19号仓）.xlsx"
NONLA19_1026 = r"D:\Documents\Desktop\AI做每月人力数据\T+1确认及时性\劳务工\劳务工-考勤记录-10.26-及时性（不含洛杉矶19号仓）.xlsx"

LA19_WH = I25.LA19_WH

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

def _top_from(recs, metric_unc='unc', metric_ldk='ldk'):
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

    # ============ (A) 劳务工 10.26 重建 = 现有非LA19块 + LA19 10.26 ============
    print("\n=== (A) 劳务工 10.26 合并 LA19 ===")
    nonla19_recs, _ = I25.read_labor_recs(NONLA19_1026, exclude_la19=False, read_only=True)
    la19_recs, la19_untimely = I25.read_labor_recs(LA19_1026, exclude_la19=False, read_only=False)
    print("  非LA19(10.26) 行:", len([r for r in nonla19_recs if r['date']=='2026-10-26']),
          " LA19(10.26) 行:", len([r for r in la19_recs if r['date']=='2026-10-26']),
          " LA19 未确认:", sum(r['yqr']-r['sjqr'] for r in la19_recs if r['date']=='2026-10-26'))
    day_recs = [r for r in nonla19_recs if r['date']=='2026-10-26'] + [r for r in la19_recs if r['date']=='2026-10-26']
    blk = I25.agg_attend_day(day_recs)
    blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed',0)>0]
    blk['group'] = [g for g in blk['group'] if g.get('unconfirmed',0)>0]
    ap['data']['2026-10-26'] = blk
    # empIndex/top 仅增量并入 LA19 部分(非LA19已在当前块内, 防重复)
    ap['empIndex'], ap['empCount'] = I25.merge_emp_index(ap['empIndex'], ap['empCount'], la19_untimely)
    la19_unc, la19_ldk = _top_from(la19_recs)
    ap['topEmpIndex'] = I25.merge_top_index(ap['topEmpIndex'], la19_unc, 'unc', min_val=3)
    if '2026-10' in ap.get('topEmpIndexM', {}):
        ap['topEmpIndexM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexM']['2026-10'], la19_unc, 'unc', min_val=3)
    ap['topEmpIndexLdk'] = I25.merge_top_index(ap['topEmpIndexLdk'], la19_ldk, 'ldk', min_val=3)
    if '2026-10' in ap.get('topEmpIndexLdkM', {}):
        ap['topEmpIndexLdkM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexLdkM']['2026-10'], la19_ldk, 'ldk', min_val=3)
    I25.ensure_region_order(ap.get('regionOrder', {}), la19_recs)
    la_w = next((e for e in blk.get('warehouse',[]) if e.get('wh')==LA19_WH), None)
    print("  10.26 合并后 yqr=%d unconfirmed=%d  LA19 unconfirmed=%s" % (
        blk['total']['yqr'], blk['total']['unconfirmed'], la_w['unconfirmed'] if la_w else "(无 LA19)"))

    # ============ (B) 劳务工 10.27 新增 ============
    print("\n=== (B) 劳务工 10.27 新增 ===")
    l27_recs, l27_untimely = I25.read_labor_recs(LABOR_1027, exclude_la19=False, read_only=True)
    print("  10.27 行:", len(l27_recs), "未确认:", sum(r['yqr']-r['sjqr'] for r in l27_recs))
    d = '2026-10-27'
    blk = I25.agg_attend_day(l27_recs)
    blk['warehouse'] = [w for w in blk['warehouse'] if w.get('unconfirmed',0)>0]
    blk['group'] = [g for g in blk['group'] if g.get('unconfirmed',0)>0]
    ap['data'][d] = blk
    ap['days'] = sorted(set(ap['days']) | {d})
    ap['empIndex'], ap['empCount'] = I25.merge_emp_index(ap['empIndex'], ap['empCount'], l27_untimely)
    l27_unc, l27_ldk = _top_from(l27_recs)
    ap['topEmpIndex'] = I25.merge_top_index(ap['topEmpIndex'], l27_unc, 'unc', min_val=3)
    if '2026-10' in ap.get('topEmpIndexM', {}):
        ap['topEmpIndexM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexM']['2026-10'], l27_unc, 'unc', min_val=3)
    ap['topEmpIndexLdk'] = I25.merge_top_index(ap['topEmpIndexLdk'], l27_ldk, 'ldk', min_val=3)
    if '2026-10' in ap.get('topEmpIndexLdkM', {}):
        ap['topEmpIndexLdkM']['2026-10'] = I25.merge_top_index(ap['topEmpIndexLdkM']['2026-10'], l27_ldk, 'ldk', min_val=3)
    I25.ensure_region_order(ap.get('regionOrder', {}), l27_recs)
    print("  10.27 yqr=%d unconfirmed=%d" % (blk['total']['yqr'], blk['total']['unconfirmed']))

    # ============ (C) 正式工 10.27 新增 ============
    print("\n=== (C) 正式工 10.27 新增 ===")
    frecs, f_untimely = I25.build_formal_recs(FORMAL_1027)
    print("  10.27 行:", len(frecs), "未及时:", sum(r['untimely'] for r in frecs))
    f_day = I25.agg_formal([r for r in frecs if r['date']=='2026-10-27'])
    f_day['warehouse'] = [w for w in f_day['warehouse'] if w.get('untimely',0)>0]
    f_day['group'] = [g for g in f_day['group'] if g.get('untimely',0)>0]
    fp['data']['2026-10-27'] = f_day
    fp['days'] = sorted(set(fp['days']) | {'2026-10-27'})
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
    print("  10.27 total=%d untimely=%d ; 月块2026-10 total=%s" % (
        f_day['total']['total'], f_day['total']['untimely'], fp['data']['2026-10']['total']))

    # ============ 写回 ============
    html = splice(html, "formalAttPayload", fp)
    html = splice(html, "attendPayload", ap)
    open(OUT, "w", encoding="utf-8").write(html)

    # ============ 校验 ============
    print("\n=== 校验摘要 ===")
    h2 = open(OUT, encoding='utf-8').read()
    fp2 = extract(h2, "formalAttPayload"); ap2 = extract(h2, "attendPayload")
    print("正式工 days:", len(fp2['days']), "末3:", fp2['days'][-3:], " 10.27 in:", '2026-10-27' in fp2['days'])
    print("  月块 2026-10 total:", fp2['data']['2026-10']['total'])
    print("劳务工 days:", len(ap2['days']), "末3:", ap2['days'][-3:], " 10.26/10.27 in:",
          '2026-10-26' in ap2['days'], '2026-10-27' in ap2['days'])
    jun = [d for d in ap2['days'] if d < '2026-10-01']
    print("  6/7/8/9月日块保留:", len(jun), "(应与BAK一致)")
    la = next((e for e in ap2['data']['2026-10-26'].get('warehouse',[]) if e.get('wh')==LA19_WH), None)
    print("  10.26 合并后 LA19 unconfirmed:", la['unconfirmed'] if la else "(无 LA19)")
    # 法国区保留检查
    for d in ('2026-10-20','2026-10-21'):
        if d in ap2['data']:
            fr = next((e for e in ap2['data'][d].get('detail',[]) if e.get('region')=='法国区'), None)
            print("  劳务工 %s 法国区 unconfirmed:" % d, fr['unconfirmed'] if fr else None)
    print("OUT size:", os.path.getsize(OUT))

if __name__ == '__main__':
    main()
