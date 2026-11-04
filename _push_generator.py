# -*- coding: utf-8 -*-
"""
FBU 考勤数据区域推送生成器
==========================
从已发布报表（补签流程_补签统计.html）解析 4 个 payload，按"接收人 -> 区域集合"
计算各区域指标，做变更检测，生成飞书交互卡片 JSON（Card 2.0），供 lark-cli 发送。

用法：
  python _push_generator.py --check-daily            # 考勤确认率按天变更检测+生成卡片（dry）
  python _push_generator.py --check-monthly          # 补签率按月变更检测+生成卡片（dry）
  python _push_generator.py --send-daily --to ou_xxx --region "欧洲区|波兰区,FBU HRBP Dept.|波兰区HRBP部"
  python _push_generator.py --send-monthly --to ou_xxx --region "..."

依赖：
  - 报表 HTML（默认当前目录 补签流程_补签统计.html）
  - 接收人映射文件 recipients.json（见 gen_recipients_template）
"""
import re
import json
import os
import sys
import hashlib
import argparse
import subprocess
from datetime import datetime, date

WS = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(WS, '补签流程_补签统计.html')
STATE_FILE = os.path.join(WS, '_push_state.json')
RECIPIENTS_FILE = os.path.join(WS, 'recipients.json')
LARK = r'C:\Users\zt25337\.workbuddy\binaries\node\cli-connector-packages\node_modules\@larksuite\cli\bin\lark-cli.exe'
DASH_URL = 'https://ztn.larkenterprise.com/page/RgGYm9pJkdaDGKafK8lc5pS1ntf'
LARK_ENV = {'SYSTEMROOT': os.environ.get('SYSTEMROOT', r'C:\Windows'),
            'COMSPEC': os.environ.get('COMSPEC', r'C:\Windows\system32\cmd.exe'),
            'PATH': os.environ.get('PATH', ''),
            'USERPROFILE': os.environ.get('USERPROFILE', ''),
            'APPDATA': os.environ.get('APPDATA', ''),
            'LOCALAPPDATA': os.environ.get('LOCALAPPDATA', ''),
            'TEMP': os.environ.get('TEMP', ''), 'TMP': os.environ.get('TMP', '')}

# ============ Payload 解析 ============

def grab_payload(html, name):
    m = re.search(r'const ' + name + r'\s*=\s*\{', html)
    if not m:
        raise RuntimeError(name + ' not found')
    i = m.end() - 1; depth = 0; start = i
    while i < len(html):
        c = html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    return html[start:i + 1]


def find_key(objtxt, key):
    m = re.search(r'(?:"' + re.escape(key) + r'"|' + re.escape(key) + r')\s*:\s*', objtxt)
    if not m:
        return None
    j = m.end()
    while j < len(objtxt) and objtxt[j] in ' \t\n\r':
        j += 1
    c = objtxt[j]
    if c == '{':
        depth = 0; s = j
        while j < len(objtxt):
            if objtxt[j] == '{':
                depth += 1
            elif objtxt[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return objtxt[s:j + 1]
    if c == '[':
        depth = 0; s = j
        while j < len(objtxt):
            if objtxt[j] == '[':
                depth += 1
            elif objtxt[j] == ']':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return objtxt[s:j + 1]
    return objtxt[j:j + len(re.match(r'[^\,\}\]]+', objtxt[j:]).group(0))]


def load_payloads():
    html = open(HTML, encoding='utf-8').read()
    out = {}
    for name in ['formalAttPayload', 'attendPayload', 'formalPayload', 'laborPayload']:
        obj = grab_payload(html, name)
        data = json.loads(find_key(obj, 'data'))
        ro = find_key(obj, 'regionOrder')
        out[name] = {'data': data, 'regionOrder': json.loads(ro) if ro else None}
    return out


# ============ 指标计算 ============

def region_metrics(payload_data, region_set, period):
    """对给定周期（day=YYYY-MM-DD 或 month=YYYY-MM）按区域集合聚合。
    返回 dict 或 None（无数据）。"""
    blk = payload_data.get(period)
    if not blk:
        return None
    det = [r for r in blk.get('detail', [])
           if (r['major'] + '|' + r['region']) in region_set]
    if not det:
        return None
    agg = {}
    for r in det:
        for f, v in r.items():
            if f in ('major', 'region'):
                continue
            if isinstance(v, (int, float)):
                agg[f] = agg.get(f, 0) + v
    return agg


def region_metrics_month(payload_data, region_set, ym):
    """按月累计：聚合 payload data 中所有前缀为 ym 的日块。返回 dict 或 None。"""
    days = sorted(k for k in payload_data.keys() if k.startswith(ym + '-'))
    if not days:
        return None
    agg = {}
    found = False
    for d in days:
        m = region_metrics(payload_data, region_set, d)
        if m is None:
            continue
        found = True
        for f, v in m.items():
            agg[f] = agg.get(f, 0) + v
    return agg if found else None


def fmt_att_rate(t):
    """formalAttPayload total -> 考勤总数/已确认/未及时/及时率"""
    total = t.get('total', 0)
    untimely = t.get('untimely', 0)
    confirmed = total - untimely
    rate = (confirmed / total * 100) if total else None
    return total, confirmed, untimely, rate


def fmt_labor_rate(t):
    """attendPayload total -> 考勤总数/已确认/未确认/及时率"""
    total = t.get('yqr', 0)
    unconfirmed = t.get('unconfirmed', 0)
    confirmed = t.get('sjqr', 0)
    rate = (confirmed / total * 100) if total else None
    return total, confirmed, unconfirmed, rate


def fmt_sign_rate(t):
    """formalPayload/laborPayload total(int) + detail rows -> total/done/rate"""
    return t  # 需配合 region_metrics 返回的 agg: total, 已完成


# ============ 变更检测 ============

def metrics_signature(payload_data, region_set, period):
    m = region_metrics(payload_data, region_set, period)
    if m is None:
        return None
    return hashlib.md5(json.dumps(m, sort_keys=True).encode()).hexdigest()


def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE, encoding='utf-8'))
    return {}


def save_state(st):
    json.dump(st, open(STATE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def check_changes(payloads, mode):
    """mode='daily' -> 考勤确认率按天（最新两天）；mode='monthly' -> 补签率按月（最新月）。
    返回 {region_key: {metric_sig, changed, periods}}"""
    state = load_state()
    result = {}
    if mode == 'daily':
        fa = payloads['formalAttPayload']['data']
        la = payloads['attendPayload']['data']
        days = sorted(set(list(fa.keys()) + list(la.keys())))
        periods = days[-2:] if len(days) >= 2 else days  # 最新一天为主，前一天对照
        per_payload = [('formalAttPayload', fa), ('attendPayload', la)]
    else:
        fp = payloads['formalPayload']['data']
        lp = payloads['laborPayload']['data']
        months = sorted(set(list(fp.keys()) + list(lp.keys())))
        periods = months[-1:]
        per_payload = [('formalPayload', fp), ('laborPayload', lp)]
    # 区域全集 = 所有 detail 出现过的 (major,region)
    all_regions = set()
    for _, d in per_payload:
        for k, blk in d.items():
            for r in blk.get('detail', []):
                all_regions.add(r['major'] + '|' + r['region'])
    for rk in sorted(all_regions):
        rs = {rk}
        sigs = {}
        for pname, d in per_payload:
            for p in periods:
                sig = metrics_signature(d, rs, p)
                if sig:
                    sigs[pname + '@' + p] = sig
        key = rk
        old = state.get(mode, {}).get(key)
        result[rk] = {'sigs': sigs, 'changed': (old != sigs), 'periods': periods}
    # update state
    st = state
    st.setdefault(mode, {})
    for rk, v in result.items():
        st[mode][rk] = v['sigs']
    save_state(st)
    return result


# ============ 卡片构造（Card 2.0） ============

def build_card(region_label, card_type, period_label, stats, url):
    """stats: list of (title, [(k, v), ...]) 分块指标；url = 区域看板链接"""
    elements = []
    blocks = []
    for bi, (title, fields) in enumerate(stats):
        md = '**' + title + '**\n'
        lines = []
        for k, v in fields:
            lines.append('- ' + k + '：**' + str(v) + '**')
        md += '\n'.join(lines)
        blocks.append({'tag': 'markdown', 'content': md})
    # 简洁版：单 markdown 拼两块 + hr + 按钮
    body_md = []
    for title, fields in stats:
        body_md.append('**' + title + '**')
        for k, v in fields:
            body_md.append('- ' + k + '：**' + str(v) + '**')
        body_md.append('')
    content = '\n'.join(body_md).rstrip()
    elements = [
        {'tag': 'markdown', 'content': content},
        {'tag': 'hr'},
        {'tag': 'button', 'text': {'tag': 'plain_text', 'content': '查看考勤看板'},
         'type': 'primary_filled', 'size': 'medium', 'width': 'fill',
         'behaviors': [{'type': 'open_url', 'default_url': url}]},
        {'tag': 'markdown', 'content': '<font color="grey">来自 FBU交付前台-考勤 · 数据若有更新将自动推送</font>', 'text_size': 'notation'},
    ]
    card = {
        'schema': '2.0',
        'config': {'width_mode': 'default', 'update_multi': True},
        'header': {
            'title': {'tag': 'plain_text', 'content': period_label + ' | ' + region_label},
            'subtitle': {'tag': 'plain_text', 'content': card_type},
            'template': 'blue',
        },
        'body': {'direction': 'vertical', 'padding': '12px 12px 16px 12px', 'elements': elements},
    }
    return card


# ============ lark-cli 发送 ============

def send_card(open_id, card):
    content = json.dumps(card, ensure_ascii=False)
    cmd = [LARK, 'im', '+messages-send', '--user-id', open_id,
           '--msg-type', 'interactive', '--content', content, '--as', 'bot']
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=LARK_ENV, timeout=60)
    return p


# ============ 主流程 ============

def gen_recipients_template():
    return {
        "_说明": "区域HRBP接收人映射。regions 数组每项为 '大区|区域'；open_id 为飞书用户 open_id（ou_ 开头）",
        "recipients": [
            {"name": "示例-波兰区HRBP", "open_id": "ou_xxxxxxxxxxxx",
             "regions": ["欧洲区|波兰区", "FBU HRBP Dept.|波兰区HRBP部"]},
        ]
    }


def send_to_region(payloads, open_id, regions, is_daily, dry_run=False):
    """为一个接收人（open_id + 区域集合）生成并发送卡片。is_daily=True 考勤确认率按天 / False 补签率按月。
    正式工卡片在多区域时额外展示「其中 HRBP」分项（HRBP 无数据则自动省略）。"""
    from urllib.parse import quote
    region_str = ','.join(regions)
    region_set = set(regions)
    _names = [x.split('|')[-1] for x in sorted(region_set)]
    region_label = next((n for n in _names if not any(s in n for s in ('HRBP', '行政部', '交付管理部', '支持组'))), _names[0] if _names else '')
    # HRBP 区域键（大区=FBU HRBP Dept. 且含 HRBP 的区域名）
    hbp_keys = {r for r in region_set if r.startswith('FBU HRBP Dept.|') and 'HRBP' in r.split('|')[-1]}
    biz_keys = region_set - hbp_keys
    _dash = lambda sec, wt: DASH_URL + '#region=' + quote(region_str, safe='') + '&wt=' + wt + '&sec=' + sec
    cards = []
    if is_daily:
        fa = payloads['formalAttPayload']['data']
        la = payloads['attendPayload']['data']
        # 月累计口径：取最新一天所属月份，整月聚合
        fday = max(fa.keys())
        fym = fday[:7]
        m1 = region_metrics_month(fa, region_set, fym)
        if m1:
            tot, conf, unt, rate = fmt_att_rate(m1)
            fields = [('考勤总数', f'{tot} 人日'), ('已确认', f'{conf} 人日'), ('未及时确认', f'{unt} 人日'), ('及时确认率', f'{rate:.2f}%')]
            # 分项：业务区域 + HRBP（两者都存在时才拆分显示）
            if hbp_keys and biz_keys:
                mh = region_metrics_month(fa, hbp_keys, fym)
                if mh:
                    ht, hc, hu, hr = fmt_att_rate(mh)
                    fields.insert(3, ('　· 其中 HRBP', f'{ht} 人日 / 未及时 {hu}'))
            cards.append(build_card(region_label, '正式工 考勤确认及时率（含HRBP）', fym,
                [('考勤确认及时率', fields)], _dash('att', 'formal')))
        lday = max(la.keys())
        lym = lday[:7]
        m2 = region_metrics_month(la, region_set, lym)
        if m2:
            tot, conf, unc, rate = fmt_labor_rate(m2)
            cards.append(build_card(region_label, '劳务工 考勤确认及时率', lym,
                [('考勤确认及时率', [('考勤总数', f'{tot} 人日'), ('已确认', f'{conf} 人日'), ('未确认', f'{unc} 人日'), ('及时确认率', f'{rate:.2f}%')])],
                _dash('att', 'labor')))
    else:
        fp = payloads['formalPayload']['data']
        lp = payloads['laborPayload']['data']
        fmon = max(fp.keys())
        m1 = region_metrics(fp, region_set, fmon)
        if m1:
            tot = m1.get('total', 0); done = m1.get('已完成', 0)
            rate = (done / tot * 100) if tot else None
            fields = [('考勤记录总数', f'{tot} 人日'), ('已补签数', f'{done} 人日'), ('补签率', f'{rate:.2f}%')]
            if hbp_keys and biz_keys:
                mh = region_metrics(fp, hbp_keys, fmon)
                if mh and mh.get('total'):
                    fields.insert(2, ('　· 其中 HRBP', f"{mh.get('total')} 人日 / 已补签 {mh.get('已完成', 0)}"))
            cards.append(build_card(region_label, '正式工 补签率（考勤为基，含HRBP）', fmon,
                [('补签率', fields)], _dash('sign', 'formal')))
        lmon = max(lp.keys())
        m2 = region_metrics(lp, region_set, lmon)
        if m2:
            tot = m2.get('total', 0); done = m2.get('已完成', 0)
            rate = (done / tot * 100) if tot else None
            cards.append(build_card(region_label, '劳务工 补签率（考勤为基）', lmon,
                [('补签率', [('考勤记录总数', f'{tot} 人日'), ('已补签数', f'{done} 人日'), ('补签率', f'{rate:.2f}%')])],
                _dash('sign', 'labor')))
    rc = 0
    for i, card in enumerate(cards):
        if dry_run:
            print(json.dumps(card, ensure_ascii=False, indent=2))
        else:
            p = send_card(open_id, card)
            print(f'  card#{i} rc={p.returncode}')
            if p.returncode != 0:
                rc = p.returncode
                if p.stderr:
                    print('  stderr:', p.stderr[:300])
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check-daily', action='store_true', help='检测考勤确认率按天变更（不发送）')
    ap.add_argument('--check-monthly', action='store_true', help='检测补签率按月变更（不发送）')
    ap.add_argument('--send-daily', action='store_true', help='生成并发送考勤确认率卡片')
    ap.add_argument('--send-monthly', action='store_true', help='生成并发送补签率卡片')
    ap.add_argument('--to', help='接收人 open_id（ou_xxx），配合 --send-* 单发')
    ap.add_argument('--region', help='区域集合，逗号分隔 "大区|区域"，配合 --send-*')
    ap.add_argument('--all', action='store_true', help='按 recipients.json 群发（仅数据有变更的接收人）')
    ap.add_argument('--force', action='store_true', help='忽略变更检测强制发送（配合 --all）')
    ap.add_argument('--gen-template', action='store_true', help='生成 recipients.json 模板')
    ap.add_argument('--dry-run', action='store_true', help='只打印卡片 JSON 不发送')
    args = ap.parse_args()

    if args.gen_template:
        if not os.path.exists(RECIPIENTS_FILE):
            json.dump(gen_recipients_template(), open(RECIPIENTS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print('template written:', RECIPIENTS_FILE)
        else:
            print('recipients.json exists, skip')
        return

    payloads = load_payloads()

    if args.all and (args.send_daily or args.send_monthly):
        mode = 'daily' if args.send_daily else 'monthly'
        if not os.path.exists(RECIPIENTS_FILE):
            print('ERROR: recipients.json 不存在，先 --gen-template 生成并填写')
            sys.exit(1)
        recs = json.load(open(RECIPIENTS_FILE, encoding='utf-8'))['recipients']
        sent = skipped = failed = 0
        for r in recs:
            oid = r.get('open_id', ''); regions = r.get('regions', [])
            if not oid or not regions:
                print('SKIP (缺 open_id/regions):', r.get('name'))
                skipped += 1
                continue
            changed = True
            if not args.force:
                # 变更检测：该接收人区域集任一签名相对 state 变化则推送
                rs = set(regions)
                state = load_state()
                sigs = {}
                if mode == 'daily':
                    for pname in ('formalAttPayload', 'attendPayload'):
                        d = payloads[pname]['data']
                        days = sorted(set(list(d.keys())))
                        for p in days[-2:]:
                            s = metrics_signature(d, rs, p)
                            if s:
                                sigs[pname + '@' + p] = s
                else:
                    for pname in ('formalPayload', 'laborPayload'):
                        d = payloads[pname]['data']
                        mons = sorted(set(list(d.keys())))
                        for p in mons[-1:]:
                            s = metrics_signature(d, rs, p)
                            if s:
                                sigs[pname + '@' + p] = s
                old = state.get(mode, {}).get('|'.join(regions))
                changed = (old != sigs)
                if changed:
                    st = load_state()
                    st.setdefault(mode, {})['|'.join(regions)] = sigs
                    save_state(st)
            if not changed:
                print('SKIP (无更新):', r.get('name'))
                skipped += 1
                continue
            rc = send_to_region(payloads, oid, regions, args.send_daily)
            if rc == 0:
                sent += 1
            else:
                failed += 1
        print(f'done: sent={sent} skipped={skipped} failed={failed}')
        return

    if args.check_daily or args.check_monthly:
        mode = 'daily' if args.check_daily else 'monthly'
        res = check_changes(payloads, mode)
        changed = {k: v for k, v in res.items() if v['changed']}
        print('total regions:', len(res), '| changed:', len(changed))
        for k in list(changed)[:20]:
            print(' CHANGED:', k, '| periods:', changed[k]['periods'])
        return

    if args.send_daily or args.send_monthly:
        if not (args.to and args.region):
            print('ERROR: --send-* 需要 --to 和 --region（或用 --all 按 recipients.json 群发）')
            sys.exit(1)
        regions = [x.strip() for x in args.region.split(',') if x.strip()]
        send_to_region(payloads, args.to, regions, args.send_daily, dry_run=args.dry_run)
        return

    ap.print_help()


if __name__ == '__main__':
    main()
