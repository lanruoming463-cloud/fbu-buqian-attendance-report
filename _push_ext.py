# -*- coding: utf-8 -*-
"""扩展卡片：考勤确认率 + 补签率 + 双 Top10 补签员工（正式工从 allEmp 聚合 / 劳务工从 topEmpIndexM）
用法: python _push_ext.py --dry-run   （发送则去掉 --dry-run，--to 指定 open_id）"""
import sys, json, argparse
sys.path.insert(0, '.')
from _push_generator import (load_payloads, grab_payload, find_key,
                             region_metrics, region_metrics_month,
                             fmt_att_rate, fmt_labor_rate, build_card, send_card, DASH_URL)
from collections import defaultdict
from urllib.parse import quote

WS = '.'
TOP_TH = 3   # 补签次数>3 才算

# ---------- Top10 计算 ----------
def top10_formal(all_emp, region_set, ym='2026-10'):
    """formalPayload.allEmp 按员工聚合指定月份的补签次数，过滤 top_exclude，取 Top10。
    region_set: {(major,region)}；HRBP 行 region 以 HRBP部 结尾，按用户原 regions 传入。"""
    agg = {}
    for e in all_emp:
        if e.get('ym') != ym:
            continue
        if e.get('top_exclude'):
            continue
        key = (e['major'], e['region'])
        if key not in region_set:
            continue
        gk = e['工号']
        a = agg.setdefault(gk, {'name': e['姓名'], 'count': 0,
                                'major': e['major'], 'region': e['region'],
                                'wh': e.get('wh', ''), 'group': e.get('group', ''),
                                'positions': set()})
        a['count'] += 1
        if e.get('职位'):
            a['positions'].add(e['职位'])
    out = []
    for gk, a in agg.items():
        if a['count'] > TOP_TH:
            a['工号'] = gk
            a['职位'] = ' / '.join(sorted(a['positions']))[:40]
            out.append(a)
    out.sort(key=lambda x: -x['count'])
    return out[:10]

def top10_labor(topM, region_set_pairs, ym='2026-10'):
    """laborPayload.topEmpIndexM[ym][gk_region] 直接取。region_set_pairs: {(major,region)} tuple 集合。"""
    inner = topM.get(ym, {})
    out = []
    for rk, lst in inner.items():
        if tuple(rk.split('|', 1)) in region_set_pairs:
            for e in lst:
                if e.get('count', 0) > TOP_TH:
                    out.append(e)
    out.sort(key=lambda x: -x.get('count', 0))
    return out[:10]

# ---------- 卡片块 ----------
def md_top_block(title, rows, empty_msg='该区域无补签次数大于3次的员工'):
    if not rows:
        return '**' + title + '**\n- ' + empty_msg
    lines = ['**' + title + '**']
    for i, e in enumerate(rows, 1):
        lines.append(f"{i}. {e['name']}（{e.get('工号') or e.get('gong')}）· {e.get('wh','')} {e.get('group','')} · **补签 {e['count']} 次**")
    return '\n'.join(lines)

def dash(sec, wt, region_str):
    return DASH_URL + '#region=' + quote(region_str, safe='') + '&wt=' + wt + '&sec=' + sec

def build_ext_card(region_label, blocks, url):
    elements = []
    for i, b in enumerate(blocks):
        elements.append({'tag': 'markdown', 'content': b})
        if i < len(blocks) - 1:
            elements.append({'tag': 'hr'})
    elements.append({'tag': 'button', 'text': {'tag': 'plain_text', 'content': '查看考勤看板'},
                     'type': 'primary_filled', 'size': 'medium', 'width': 'fill',
                     'behaviors': [{'type': 'open_url', 'default_url': url}]})
    elements.append({'tag': 'markdown',
                     'content': '<font color="grey">来自 FBU交付前台-考勤 · 数据若有更新将自动推送</font>',
                     'text_size': 'notation'})
    return {
        'schema': '2.0',
        'config': {'width_mode': 'default', 'update_multi': True},
        'header': {'title': {'tag': 'plain_text', 'content': '2026-10 月度考勤汇总 | ' + region_label},
                   'subtitle': {'tag': 'plain_text', 'content': '考勤确认及时率 + 补签率 + Top10 补签员工'},
                   'template': 'blue'},
        'body': {'direction': 'vertical', 'padding': '12px 12px 16px 12px', 'elements': elements},
    }

def send_to_region_ext(payloads, open_id, regions, dry_run=False, quiet=False):
    region_str = ','.join(regions)
    region_set = set(regions)                      # "major|region" 字符串，供 region_metrics 用
    region_set_pairs = set()
    for r in regions:
        if '|' in r:
            region_set_pairs.add(tuple(r.split('|', 1)))   # 供 allEmp 逐行匹配用
    _names = [x.split('|')[-1] for x in sorted(region_set)]
    region_label = next((n for n in _names if not any(s in n for s in ('HRBP', '行政部', '交付管理部', '支持组'))), _names[0] if _names else '')
    hbp_keys = {tuple(r.split('|', 1)) for r in regions if r.startswith('FBU HRBP Dept.|')}
    biz_keys = region_set_pairs - hbp_keys
    cards = []
    fa = payloads['formalAttPayload']['data']
    la = payloads['attendPayload']['data']
    fp = payloads['formalPayload']
    lp = payloads['laborPayload']

    blocks = []
    r_att_f = r_att_l = r_sign_f = r_sign_l = None
    # ---- 考勤确认及时率：正式工(含HRBP) ----
    fday = max(fa.keys()); fym = fday[:7]
    m1 = region_metrics_month(fa, region_set, fym)
    if m1:
        tot, conf, unt, rate = fmt_att_rate(m1)
        r_att_f = rate
        b = f"**正式工 考勤确认及时率（{fym}，含HRBP）**\n- 考勤总数：**{tot} 人日**\n- 已确认：**{conf} 人日**\n- 未及时确认：**{unt} 人日**\n- 及时确认率：**{rate:.2f}%**"
        if hbp_keys and biz_keys:
            mh = region_metrics_month(fa, hbp_keys, fym)
            if mh:
                ht, hc, hu, hr = fmt_att_rate(mh)
                b += f"\n- 　· 其中 HRBP：{ht} 人日 / 未及时 {hu}"
        blocks.append(b)
    # ---- 考勤确认及时率：劳务工 ----
    lday = max(la.keys()); lym = lday[:7]
    m2 = region_metrics_month(la, region_set, lym)
    if m2:
        tot, conf, unc, rate = fmt_labor_rate(m2)
        r_att_l = rate
        blocks.append(f"**劳务工 考勤确认及时率（{lym}）**\n- 考勤总数：**{tot} 人日**\n- 已确认：**{conf} 人日**\n- 未确认：**{unc} 人日**\n- 及时确认率：**{rate:.2f}%**")
    # ---- 补签率：正式工 ----
    fmon = max(fp['data'].keys())
    m3 = region_metrics(fp['data'], region_set, fmon)
    if m3 and m3.get('total'):
        tot = m3['total']; done = m3.get('已完成', 0)
        r_sign_f = done / tot * 100
        b = f"**正式工 补签率（{fmon}，考勤为基，含HRBP）**\n- 考勤记录总数：**{tot} 人日**\n- 已补签数：**{done} 人日**\n- 补签率：**{r_sign_f:.2f}%**"
        if hbp_keys and biz_keys:
            mh = region_metrics(fp['data'], hbp_keys, fmon)
            if mh and mh.get('total'):
                b += f"\n- 　· 其中 HRBP：{mh['total']} 人日 / 已补签 {mh.get('已完成',0)}"
        blocks.append(b)
    # ---- 补签率：劳务工 ----
    lmon = max(lp['data'].keys())
    m4 = region_metrics(lp['data'], region_set, lmon)
    if m4 and m4.get('total'):
        tot = m4['total']; done = m4.get('已完成', 0)
        r_sign_l = done / tot * 100
        blocks.append(f"**劳务工 补签率（{lmon}，考勤为基）**\n- 考勤记录总数：**{tot} 人日**\n- 已补签数：**{done} 人日**\n- 补签率：**{r_sign_l:.2f}%**")
    # ---- Top10 补签员工：正式工 ----
    html = open('补签流程_补签统计.html', encoding='utf-8').read()
    fobj = grab_payload(html, 'formalPayload')
    all_emp = json.loads(find_key(fobj, 'allEmp'))
    t10f = top10_formal(all_emp, region_set_pairs)
    blocks.append(md_top_block(f'正式工 补签Top10（{fmon}）', t10f))
    # ---- Top10 补签员工：劳务工 ----
    lobj = grab_payload(html, 'laborPayload')
    topM = json.loads(find_key(lobj, 'topEmpIndexM'))
    t10l = top10_labor(topM, region_set_pairs)
    blocks.append(md_top_block(f'劳务工 补签Top10（{lmon}）', t10l))

    # ---- 最前面：整体指标（正式工+劳务工 算术平均，与"整体及时率"同口径） ----
    ov_att = (r_att_f + r_att_l) / 2 if (r_att_f is not None and r_att_l is not None) else None
    ov_sign = (r_sign_f + r_sign_l) / 2 if (r_sign_f is not None and r_sign_l is not None) else None
    ov = [f"**整体指标（{fym}）=（正式工 + 劳务工）÷ 2**"]
    if ov_att is not None:
        ov.append(f"- 整体考勤确认率：**{ov_att:.2f}%**（正式工 {r_att_f:.2f}% / 劳务工 {r_att_l:.2f}%）")
    if ov_sign is not None:
        ov.append(f"- 整体补签率：**{ov_sign:.2f}%**（正式工 {r_sign_f:.2f}% / 劳务工 {r_sign_l:.2f}%）")
    if len(ov) > 1:
        blocks.insert(0, '\n'.join(ov))

    card = build_ext_card(region_label, blocks, dash('att', 'formal', region_str))
    if dry_run:
        if quiet:
            print(f'  [{region_label}] 块数={len(blocks)} ov_att={ov_att and "%.2f" % ov_att} ov_sign={ov_sign and "%.2f" % ov_sign}')
        else:
            print(json.dumps(card, ensure_ascii=False, indent=1))
        return 0
    p = send_card(open_id, card)
    print(f'rc={p.returncode}')
    if p.returncode != 0 and p.stderr:
        print('stderr:', p.stderr[:300])
    return p.returncode

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--to', help='接收人 open_id（配合单发）')
    ap.add_argument('--region', help='逗号分隔 大区|区域（配合单发）')
    ap.add_argument('--all', action='store_true', help='按 recipients.json 群发（每接收人一张合并卡片）')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    P = load_payloads()
    if a.all:
        recs = json.load(open('recipients.json', encoding='utf-8'))['recipients']
        sent = failed = skipped = 0
        for r in recs:
            oid = r.get('open_id'); regions = r.get('regions', [])
            if not oid or not regions:
                print('SKIP(缺 open_id/regions):', r.get('name')); skipped += 1; continue
            print('=== %s (%s) ===' % (r.get('name'), oid))
            rc = send_to_region_ext(P, oid, regions, dry_run=a.dry_run, quiet=a.dry_run)
            if rc == 0: sent += 1
            else: failed += 1
        print(f'done: sent={sent} skipped={skipped} failed={failed}')
    else:
        if not (a.to and a.region):
            print('ERROR: 单发需 --to + --region，或改用 --all 群发'); sys.exit(1)
        send_to_region_ext(P, a.to, [x.strip() for x in a.region.split(',')], dry_run=a.dry_run)
