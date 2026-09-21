import pandas as pd
import numpy as np
import json
import re
from datetime import datetime, time as dt_time

SRCS = [r"D:/Documents/Downloads/补签流程-6月.xlsx", r"D:/Documents/Downloads/补签流程-7月.xlsx"]
ROSTER = r"D:/Documents/Downloads/花名册 - 2026-08-24T185145.634.xlsx"
OUT_XLSX = r"C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.xlsx"
OUT_HTML = r"C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html"

KEEP = ['已完成', '审批中']
WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

# 架构排序（用户指定）：大区顺序 + 各区域顺序
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
def region_idx(major, region, major_order=MAJOR_ORDER, region_order=REGION_ORDER):
    lst = region_order.get(major, [])
    return lst.index(region) if region in lst else len(lst)

def wh_num(name):
    """从仓/组名称（如 '新泽西10号仓'、'美东5号仓'、'部门直属'）提取内嵌数字用于自然排序。
    有数字则取第一个整数；无数字（如部门直属）返回极大值以排末尾。"""
    m = re.search(r'(\d+)', str(name))
    return int(m.group(1)) if m else 10**9

def agg_period(df, major_order=MAJOR_ORDER, region_order=REGION_ORDER):
    MAJOR_IDX_L = {m: i for i, m in enumerate(major_order)}
    total = len(df)
    done = int((df['审批状态'] == '已完成').sum())
    ing = int((df['审批状态'] == '审批中').sum())
    major = df.groupby('三级部门')['审批状态'].value_counts().unstack(fill_value=0)
    for s in KEEP:
        if s not in major.columns:
            major[s] = 0
    major['total'] = major['已完成'] + major['审批中']
    major = major.reset_index()
    major['__o'] = major['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    major = major.sort_values(['__o', 'total'], ascending=[True, False]).drop(columns='__o').reset_index(drop=True)
    major['pct'] = (major['total'] / total * 100).round(1) if total else 0.0
    major_map = major.set_index('三级部门')['total'].to_dict()

    det = df.groupby(['三级部门', '四级部门', '审批状态']).size().unstack(fill_value=0)
    for s in KEEP:
        if s not in det.columns:
            det[s] = 0
    det['total'] = det['已完成'] + det['审批中']
    det = det.reset_index()
    det['pctMajor'] = (det['total'] / det['三级部门'].map(major_map) * 100).round(1)
    det['__mo'] = det['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    det['__ro'] = [region_idx(m, r, major_order, region_order) for m, r in zip(det['三级部门'], det['四级部门'])]
    det = det.sort_values(['__mo', '__ro']).drop(columns=['__mo', '__ro']).reset_index(drop=True)

    # 仓维度（五级部门）：空值统一归为“部门直属”；第三版块不展示 HRBP 数据
    wdf = df[df['三级部门'] != 'FBU HRBP Dept.'].copy()
    wdf['五级部门'] = wdf['五级部门'].fillna('部门直属')
    wh = wdf.groupby(['三级部门', '四级部门', '五级部门', '审批状态']).size().unstack(fill_value=0)
    for s in KEEP:
        if s not in wh.columns:
            wh[s] = 0
    wh['total'] = wh['已完成'] + wh['审批中']
    wh = wh.reset_index()
    region_full_tot = df.groupby(['三级部门', '四级部门']).size().rename('region_full')
    wh = wh.merge(region_full_tot.reset_index(), on=['三级部门', '四级部门'], how='left')
    wh['pctRegion'] = (wh['total'] / wh['region_full'] * 100).round(1)
    wh['__mo'] = wh['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    wh['__ro'] = [region_idx(m, r, major_order, region_order) for m, r in zip(wh['三级部门'], wh['四级部门'])]
    wh['__wn'] = wh['五级部门'].map(wh_num)
    wh = wh.sort_values(['__mo', '__ro', '__wn', 'total'], ascending=[True, True, True, False]).drop(columns=['__mo', '__ro', '__wn', 'region_full']).reset_index(drop=True)
    warehouse = wh.rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh'}).to_dict('records')

    # 组维度（六级部门）：空值统一归为“部门直属”；第四版块不展示 HRBP 数据
    gdf = df[df['三级部门'] != 'FBU HRBP Dept.'].copy()
    gdf['六级部门'] = gdf['六级部门'].fillna('部门直属')
    grp = gdf.groupby(['三级部门', '四级部门', '五级部门', '六级部门', '审批状态']).size().unstack(fill_value=0)
    for s in KEEP:
        if s not in grp.columns:
            grp[s] = 0
    grp['total'] = grp['已完成'] + grp['审批中']
    grp = grp.reset_index()
    wh_full = gdf.groupby(['三级部门', '四级部门', '五级部门']).size().rename('wh_full')
    grp = grp.merge(wh_full.reset_index(), on=['三级部门', '四级部门', '五级部门'], how='left')
    grp['pctWh'] = (grp['total'] / grp['wh_full'] * 100).round(1)
    grp['__mo'] = grp['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    grp['__ro'] = [region_idx(m, r, major_order, region_order) for m, r in zip(grp['三级部门'], grp['四级部门'])]
    grp = grp.sort_values(['__mo', '__ro', '五级部门', 'total'], ascending=[True, True, True, False]).drop(columns=['__mo', '__ro', 'wh_full']).reset_index(drop=True)
    groupp = grp.rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh', '六级部门': 'group'}).to_dict('records')

    return {
        'total': total, 'done': done, 'ing': ing,
        'major': major.rename(columns={'三级部门': 'name'}).to_dict('records'),
        'detail': det.rename(columns={'三级部门': 'major', '四级部门': 'region'}).to_dict('records'),
        'warehouse': warehouse,
        'group': groupp
    }

def agg_period_labor(df, major_order=MAJOR_ORDER, region_order=REGION_ORDER):
    """劳务工专用聚合（求和口径）。

    补签合计 = Σ应补签数
    已完成   = Σ已补签数（实际补签数）
    未完成   = 补签合计 − 已完成 = Σ应补签数 − Σ实际补签数
    输出结构与 agg_period 完全一致（保留 '已完成'/'审批中'/'total' 键），
    供 JS aggRange 直接复用，无需改动前端聚合逻辑。
    """
    MAJOR_IDX_L = {m: i for i, m in enumerate(major_order)}
    def _spct(num, den):
        return round(num / den * 100, 1) if den else 0.0
    total = float(df['应补签数'].sum())
    done = float(df['实际补签数'].sum())
    ing = total - done

    # major
    g = df.groupby('三级部门').agg(ybq=('应补签数', 'sum'), ybj=('实际补签数', 'sum'))
    g['已完成'] = g['ybj']; g['审批中'] = g['ybq'] - g['ybj']; g['total'] = g['ybq']
    g = g.reset_index()
    g['__o'] = g['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    g = g.sort_values(['__o', 'total'], ascending=[True, False]).drop(columns='__o').reset_index(drop=True)
    g['pct'] = g.apply(lambda r: _spct(r['total'], total), axis=1)
    major_map = g.set_index('三级部门')['total'].to_dict()

    # detail
    gd = df.groupby(['三级部门', '四级部门']).agg(ybq=('应补签数', 'sum'), ybj=('实际补签数', 'sum'))
    gd['已完成'] = gd['ybj']; gd['审批中'] = gd['ybq'] - gd['ybj']; gd['total'] = gd['ybq']
    gd = gd.reset_index()
    gd['pctMajor'] = gd.apply(lambda r: _spct(r['total'], major_map.get(r['三级部门'], 0)), axis=1)
    gd['__mo'] = gd['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    gd['__ro'] = [region_idx(m, r, major_order, region_order) for m, r in zip(gd['三级部门'], gd['四级部门'])]
    gd = gd.sort_values(['__mo', '__ro']).drop(columns=['__mo', '__ro']).reset_index(drop=True)

    # warehouse（劳务工无 HRBP 部门，不做剔除）
    wdf = df.copy()
    wdf['五级部门'] = wdf['五级部门'].fillna('部门直属')
    gw = wdf.groupby(['三级部门', '四级部门', '五级部门']).agg(ybq=('应补签数', 'sum'), ybj=('实际补签数', 'sum'))
    gw['已完成'] = gw['ybj']; gw['审批中'] = gw['ybq'] - gw['ybj']; gw['total'] = gw['ybq']
    gw = gw.reset_index()
    region_full = df.groupby(['三级部门', '四级部门']).agg(rf=('应补签数', 'sum')).reset_index()
    region_full_map = region_full.set_index(['三级部门', '四级部门'])['rf'].to_dict()
    gw['pctRegion'] = gw.apply(lambda r: _spct(r['total'], region_full_map.get((r['三级部门'], r['四级部门']), 0)), axis=1)
    gw['__mo'] = gw['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    gw['__ro'] = [region_idx(m, r, major_order, region_order) for m, r in zip(gw['三级部门'], gw['四级部门'])]
    gw['__wn'] = gw['五级部门'].map(wh_num)
    gw = gw.sort_values(['__mo', '__ro', '__wn', 'total'], ascending=[True, True, True, False]).drop(columns=['__mo', '__ro', '__wn']).reset_index(drop=True)
    warehouse = gw.rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh'}).to_dict('records')

    # group
    gdf = df.copy()
    gdf['六级部门'] = gdf['六级部门'].fillna('部门直属')
    gg = gdf.groupby(['三级部门', '四级部门', '五级部门', '六级部门']).agg(ybq=('应补签数', 'sum'), ybj=('实际补签数', 'sum'))
    gg['已完成'] = gg['ybj']; gg['审批中'] = gg['ybq'] - gg['ybj']; gg['total'] = gg['ybq']
    gg = gg.reset_index()
    wh_full = gdf.groupby(['三级部门', '四级部门', '五级部门']).agg(wf=('应补签数', 'sum')).reset_index()
    wh_full_map = wh_full.set_index(['三级部门', '四级部门', '五级部门'])['wf'].to_dict()
    gg['pctWh'] = gg.apply(lambda r: _spct(r['total'], wh_full_map.get((r['三级部门'], r['四级部门'], r['五级部门']), 0)), axis=1)
    gg['__mo'] = gg['三级部门'].map(MAJOR_IDX_L).fillna(len(major_order)).astype(int)
    gg['__ro'] = [region_idx(m, r, major_order, region_order) for m, r in zip(gg['三级部门'], gg['四级部门'])]
    gg = gg.sort_values(['__mo', '__ro', '五级部门', 'total'], ascending=[True, True, True, False]).drop(columns=['__mo', '__ro']).reset_index(drop=True)
    groupp = gg.rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh', '六级部门': 'group'}).to_dict('records')

    return {
        'total': total, 'done': done, 'ing': ing,
        'major': g.rename(columns={'三级部门': 'name'}).to_dict('records'),
        'detail': gd.rename(columns={'三级部门': 'major', '四级部门': 'region'}).to_dict('records'),
        'warehouse': warehouse,
        'group': groupp
    }

# load (合并 6月 + 7月 两份数据源)
pdf = pd.concat([pd.read_excel(f) for f in SRCS], ignore_index=True)
sub = pdf[pdf['审批状态'].isin(KEEP)].copy()
EXCLUDE_MAJORS = ['海外销售部', 'FBU财务部', '渠道管理部', 'LD 法务部']
EXCLUDE_REGIONS = ['美洲支持HRBP组']
sub = sub[~sub['三级部门'].isin(EXCLUDE_MAJORS)].copy()
sub = sub[~sub['四级部门'].isin(EXCLUDE_REGIONS)].copy()
sub['补签日期_dt'] = pd.to_datetime(sub['补签日期'], errors='coerce')
sub['ym'] = sub['补签日期_dt'].dt.strftime('%Y-%m')
sub['ymd'] = sub['补签日期_dt'].dt.strftime('%Y-%m-%d')

# 从花名册匹配职位（按工号），未匹配到显示为「—」
roster = pd.read_excel(ROSTER, usecols=['工号', '职位', '职级'])
roster = roster.dropna(subset=['工号', '职位'])
roster = roster.drop_duplicates('工号', keep='first')
roster['工号'] = roster['工号'].astype(str)
pos_map = roster.set_index('工号')['职位'].to_dict()
lvl_map = {k: (str(v).strip() if pd.notna(v) else '—') for k, v in roster.set_index('工号')['职级'].items()}
sub['职位'] = sub['工号'].astype(str).map(pos_map).fillna('—')

# Top10 剔除规则：
#  1) 补签事由 == "入职当天"
#  2) 备注表明因客观情况无法打卡：无打卡机/考勤机、机器故障/损坏、系统问题、闸机故障、消防、
#     无工牌/工卡（无卡无法打卡）等。以下关键词（中英文）视为客观无法打卡。
import re as _re
def is_top_exclude(reason, remark):
    reason = '' if pd.isna(reason) else str(reason).strip()
    if reason == '入职当天':
        return True
    if pd.isna(remark):
        return False
    r = str(remark).strip().lower()
    if not r:
        return False
    obj_patterns = [
        # 无打卡机 / 无考勤机
        r'没有打卡机', r'无打卡机', r'没有考勤机', r'无考勤机',
        # 英文 no machine / no id
        r'no\s*clock', r'no\s*punch', r'no\s*attend', r'no\s*badge', r'no\s*id\b', r'not\s*id',
        # 打卡机/考勤机/闸机 故障损坏
        r'(打卡机|考勤机|闸机).{0,4}(异常|故障|坏|问题|没反应|损坏|失灵|坏了)',
        r'(clock|punch|time\s*clock|attendance)\s*machine.{0,20}(issue|problem|fault|error|fail|broken|not working|didn.?t work|malfunction)',
        # 系统问题
        r'系统问题', r'系统故障', r'系统异常',
        r'system\s*(issue|problem|error|down|fail|crash|not working)',
        # 无法打卡 / 未能正常打卡
        r'无法打卡', r'暂时无法打卡', r'不能打卡', r'没法打卡', r'未能正常打卡', r'无法签到', r'无法上班打卡', r'无法考勤',
        r'cannot\s*clock', r'can.?t\s*clock', r'unable\s*to\s*clock', r'fail\s*to\s*clock', r'no\s*clock\s*in',
        # 消防（区域封锁无法打卡）
        r'消防',
        # 西班牙语入职 / 司机在外跑业务（均属客观无法打卡）
        r'nuevo\s*ingreso', r'\bingreso\b', r'司机在外', r'在外跑业务', r'在外面跑业务', r'在外跑单',
        # 工牌/工卡/id 卡（无卡无法打卡）
        r'id\s*card', r'inactive\s*id', r'lost\s*card', r'forgot\s*card',
        r'工[牌卡].{0,6}(没|未|丢失|丢)', r'(没|未|丢失|丢).{0,4}工[牌卡]', r'没有工[牌卡]', r'无工[牌卡]',
    ]
    return any(_re.search(p, r) for p in obj_patterns)

sub['top_exclude'] = sub.apply(lambda x: is_top_exclude(x['补签事由'], x['备注']), axis=1)
print(f"[Top10剔除] 标记为剔除的记录数: {int(sub['top_exclude'].sum())} / {len(sub)}")

# overall (for Excel)
g_major = sub.groupby('三级部门')['审批状态'].value_counts().unstack(fill_value=0)
for s in KEEP:
    if s not in g_major.columns:
        g_major[s] = 0
g_major['补签合计'] = g_major['已完成'] + g_major['审批中']
g_major = g_major.sort_values('补签合计', ascending=False).reset_index()
g_major['占总体比'] = (g_major['补签合计'] / g_major['补签合计'].sum() * 100).round(1)
g_major['__o'] = g_major['三级部门'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
g_major = g_major.sort_values('__o').drop(columns='__o').reset_index(drop=True)
cnt = sub.groupby(['三级部门', '四级部门', '审批状态']).size().unstack(fill_value=0)
for s in KEEP:
    if s not in cnt.columns:
        cnt[s] = 0
cnt['补签合计'] = cnt['已完成'] + cnt['审批中']
cnt = cnt.reset_index()
major_tot = g_major.set_index('三级部门')['补签合计'].to_dict()
cnt['占大区比'] = (cnt['补签合计'] / cnt['三级部门'].map(major_tot) * 100).round(1)
cnt['__mo'] = cnt['三级部门'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
cnt['__ro'] = [region_idx(m, r) for m, r in zip(cnt['三级部门'], cnt['四级部门'])]
cnt = cnt.sort_values(['__mo', '__ro']).drop(columns=['__mo', '__ro']).reset_index(drop=True)

# period data
months = sorted(sub['ym'].dropna().unique())
days = sorted(sub['ymd'].dropna().unique())
data = {}
for m in months:
    data[m] = agg_period(sub[sub['ym'] == m])
for d in days:
    data[d] = agg_period(sub[sub['ymd'] == d])

# Excel
with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as xw:
    note = pd.DataFrame({
        '说明': [
            '数据来源：补签流程-6月.xlsx + 补签流程-7月.xlsx（合并，按自然键零重叠，无重复计数）',
            f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}',
            '统计口径：审批状态 = 已完成 / 审批中（已排除 已驳回、已废弃、已撤回）',
            '大区维度：三级部门；区域维度：四级部门',
            '加拿大区已归入美洲区（数据中三级部门=美洲区、四级部门=加拿大区）',
            '已剔除大区：海外销售部、FBU财务部、渠道管理部、LD 法务部（按需求不展示）',
            '已剔除区域：美洲支持HRBP组（不展示）',
            '展示排序（按架构）：大区顺序 美洲区 → 欧洲区 → 亚太区 → FBU HRBP Dept.；各区域按指定架构顺序（美洲/欧洲/亚太物理区域顺序，HRBP部按对应大区排列）',
            '仓维度：五级部门（到仓级），第三版块「区域_仓明细」不展示 FBU HRBP Dept. 数据；五级部门为空时统一显示为「部门直属」',
            '仓维度占比：各仓/部门直属补签数 ÷ 所属区域(四级部门)完整合计，确保与区域合计对齐',
            '组维度：六级部门（到组级），第四版块「区域_仓_组明细」展示大区×区域×仓×组占比并可点击组展开组内员工；空组统一显示为「部门直属」，不展示 FBU HRBP Dept. 数据',
            '组维度占比：各组补签数 ÷ 所属仓(五级部门)完整合计，确保与仓合计对齐',
            '组下员工：网页版第四板块点击任意组可展开该组补签员工明细（姓名/工号/职位/补签日期/班次/补签点/补签事由/备注/审批状态）；Excel「组下员工明细」sheet 为全量记录',
            '第五板块「各区补签 Top10 员工」：按区域（四级部门）聚合员工补签数，各区取补签数前 10 名员工（含已完成+审批中），并展示该员工在该区域下补签次数最多的仓（五级部门）和组（六级部门），按大区→区域可折叠展示；Excel「各区补签Top10员工」sheet 为全量排名。Top10 已剔除补签事由=入职当天及备注因客观情况无法打卡的记录',
            f'纳入记录合计：{len(sub)} 条（已完成 {int((sub["审批状态"]=="已完成").sum())} + 审批中 {int((sub["审批状态"]=="审批中").sum())}）',
            '网页版支持按天/按月切换查看，Excel 为全量汇总。',
            '考勤确认及时率（劳务工）看板：见 sheet「考勤确认及时性_大区 / 考勤确认及时性_区域 / 考勤确认及时性_仓」。数据源为《劳务工工时》Excel 的「考勤」sheet（2026-06 与 2026-07 两份，逐人逐日原始考勤，共约 41 万行）；区域按物理仓归属归入三大区（加拿大区归美洲区），口径同正式工考勤确认及时率看板。补签率=应补签数÷应打卡次数，考勤确认率=已确认数÷考勤总数；及时确认率下降代表及时性变差。',
        ]
    })
    note.to_excel(xw, sheet_name='说明', index=False)
    g_major.to_excel(xw, sheet_name='大区汇总', index=False)
    cnt.to_excel(xw, sheet_name='大区_区域明细', index=False)

    # 区域 × 仓 明细：五级部门为空则归为“部门直属”；第三版块不展示 HRBP 数据
    wh = sub[sub['三级部门'] != 'FBU HRBP Dept.'].copy()
    wh['五级部门'] = wh['五级部门'].fillna('部门直属')
    whg = wh.groupby(['三级部门', '四级部门', '五级部门', '审批状态']).size().unstack(fill_value=0)
    for s in KEEP:
        if s not in whg.columns:
            whg[s] = 0
    whg['补签合计'] = whg['已完成'] + whg['审批中']
    whg = whg.reset_index()
    region_full_tot = sub.groupby(['三级部门', '四级部门']).size().rename('region_full')
    whg = whg.merge(region_full_tot.reset_index(), on=['三级部门', '四级部门'], how='left')
    whg['占区域比'] = (whg['补签合计'] / whg['region_full'] * 100).round(1)
    whg['__mo'] = whg['三级部门'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    whg['__ro'] = [region_idx(m, r) for m, r in zip(whg['三级部门'], whg['四级部门'])]
    whg = whg.sort_values(['__mo', '__ro', '补签合计'], ascending=[True, True, False]).drop(columns=['__mo', '__ro', 'region_full']).reset_index(drop=True)
    whg = whg.rename(columns={'三级部门': '大区', '四级部门': '区域', '五级部门': '仓'})
    whg.to_excel(xw, sheet_name='区域_仓明细', index=False)

    # 区域 × 仓 × 组 明细：六级部门为空则归为“部门直属”；不展示 HRBP 数据；占仓比=该组÷所属仓合计
    grpX = sub[sub['三级部门'] != 'FBU HRBP Dept.'].copy()
    grpX['五级部门'] = grpX['五级部门'].fillna('部门直属')
    grpX['六级部门'] = grpX['六级部门'].fillna('部门直属')
    gg = grpX.groupby(['三级部门', '四级部门', '五级部门', '六级部门', '审批状态']).size().unstack(fill_value=0)
    for s in KEEP:
        if s not in gg.columns:
            gg[s] = 0
    gg['补签合计'] = gg['已完成'] + gg['审批中']
    gg = gg.reset_index()
    wh_full = grpX.groupby(['三级部门', '四级部门', '五级部门']).size().rename('wh_full')
    gg = gg.merge(wh_full.reset_index(), on=['三级部门', '四级部门', '五级部门'], how='left')
    gg['占仓比'] = (gg['补签合计'] / gg['wh_full'] * 100).round(1)
    gg['__mo'] = gg['三级部门'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    gg['__ro'] = [region_idx(m, r) for m, r in zip(gg['三级部门'], gg['四级部门'])]
    gg = gg.sort_values(['__mo', '__ro', '五级部门', '补签合计'], ascending=[True, True, True, False]).drop(columns=['__mo', '__ro', 'wh_full']).reset_index(drop=True)
    gg = gg.rename(columns={'三级部门': '大区', '四级部门': '区域', '五级部门': '仓', '六级部门': '组'})
    gg.to_excel(xw, sheet_name='区域_仓_组明细', index=False)

    # 组下员工明细（全量）：每条补签记录对应一名员工的补签申请
    empX = grpX[['三级部门', '四级部门', '五级部门', '六级部门', '姓名', '工号', '职位', '补签日期', '班次名称', '补签点', '补签事由', '备注', '审批状态']].copy()
    empX['备注'] = empX['备注'].fillna('')
    empX = empX.rename(columns={'三级部门': '大区', '四级部门': '区域', '五级部门': '仓', '六级部门': '组', '班次名称': '班次'})
    empX.to_excel(xw, sheet_name='组下员工明细', index=False)

    # 各区补签 Top10 员工：按 大区×区域×工号 聚合补签数，各区取前 10（含 HRBP 区域，与区域明细表口径一致）
    # Top10 已剔除「补签事由=入职当天」及「备注因客观情况无法打卡」的记录
    sub_top = sub[~sub['top_exclude']]
    emp_grp = sub_top[['三级部门', '四级部门', '工号', '姓名', '职位', '五级部门', '六级部门', '审批状态']].copy()
    emp_grp['五级部门'] = emp_grp['五级部门'].fillna('部门直属')
    emp_grp['六级部门'] = emp_grp['六级部门'].fillna('部门直属')
    agg = emp_grp.groupby(['三级部门', '四级部门', '工号', '姓名']).agg(
        补签数=('审批状态', 'size'),
        已完成=('审批状态', lambda s: int((s == '已完成').sum())),
        审批中=('审批状态', lambda s: int((s == '审批中').sum())),
        # 主属仓/组：该员工在该区域下补签次数最多的仓/组（并列时取名字母序最小）
        主属仓=('五级部门', lambda s: s.value_counts().sort_index(ascending=True).idxmax()),
        主属组=('六级部门', lambda s: s.value_counts().sort_index(ascending=True).idxmax()),
        # 职位：取该员工在该区域下第一条非空职位
        职位=('职位', lambda s: s.dropna().replace('—', pd.NA).dropna().iloc[0] if len(s.dropna().replace('—', pd.NA).dropna()) else '—'),
    ).reset_index()
    top_parts = []
    for (maj, reg), g in agg.groupby(['三级部门', '四级部门']):
        g = g.sort_values(['补签数', '姓名'], ascending=[False, True]).head(10).reset_index(drop=True)
        g['排名'] = range(1, len(g) + 1)
        g['大区'] = maj
        g['区域'] = reg
        top_parts.append(g[['大区', '区域', '排名', '姓名', '工号', '职位', '主属仓', '主属组', '补签数', '已完成', '审批中']])
    if top_parts:
        top_df = pd.concat(top_parts, ignore_index=True)
    else:
        top_df = pd.DataFrame(columns=['大区', '区域', '排名', '姓名', '工号', '职位', '主属仓', '主属组', '补签数', '已完成', '审批中'])
    top_df['__mo'] = top_df['大区'].map(MAJOR_IDX).fillna(len(MAJOR_ORDER)).astype(int)
    top_df['__ro'] = [region_idx(m, r) for m, r in zip(top_df['大区'], top_df['区域'])]
    top_df = top_df.sort_values(['__mo', '__ro', '排名']).drop(columns=['__mo', '__ro']).reset_index(drop=True)
    top_df.to_excel(xw, sheet_name='各区补签Top10员工', index=False)

print("Excel 已生成:", OUT_XLSX)

# 员工明细（全量，顶层只存一份；前端按当前月/天过滤建索引，避免逐周期重复存储）
# 此处包含 HRBP，使「各区 Top10 员工」板块与区域明细表（二级板块）口径一致；
# 组/仓明细（第三、四板块）仍用非 HRBP 的 grpX，不受影响
emp_all = sub.copy()
emp_all['五级部门'] = emp_all['五级部门'].fillna('部门直属')
emp_all['六级部门'] = emp_all['六级部门'].fillna('部门直属')
emp_all['补签日期'] = emp_all['补签日期'].map(lambda x: str(x)[:10] if pd.notna(x) else '')
emp_all['备注'] = emp_all['备注'].fillna('')
emp_all = emp_all[['三级部门', '四级部门', '五级部门', '六级部门', '姓名', '工号', '职位', '补签日期', '班次名称', '补签点', '补签事由', '备注', '审批状态', 'ym', 'ymd', 'top_exclude']]
emp_all = emp_all.rename(columns={'三级部门': 'major', '四级部门': 'region', '五级部门': 'wh', '六级部门': 'group', '班次名称': '班次'})
allEmp = emp_all.to_dict('records')

# 正式工 emp 明细表列定义（供前端 data-driven 渲染）
FORMAL_EMP_KEYS = ['姓名', '工号', '职位', '补签日期', '班次', '补签点', '补签事由', '备注', '审批状态']
FORMAL_EMP_HEADERS = ['姓名', '工号', '职位', '补签日期', '班次', '补签点', '补签事由', '备注', '审批状态']
FORMAL_SUBTITLE = '维度：三级部门（大区）× 四级部门（区域）　|　口径：审批状态 = 已完成 + 审批中'

# ===================== 劳务工数据源（独立于正式工，结构对齐便于前端复用） =====================
LABOR_SRCS = [r'D:/Documents/Downloads/劳务工补签-6月.xlsx', r'D:/Documents/Downloads/劳务工补签-7月.xlsx']
LABOR_SHEET = '劳务工-考勤表'
LABOR_ARCH_SHEET = '劳务工架构'

def build_labor_payload():
    """从劳务工考勤表构建与正式工同构的 payload。
    劳务工无「补签申请」概念，定义「补签记录」= 实际补签数 > 0 的每日考勤行。
    大区按区域名显式规则判断：欧洲区/亚太区/其余→美洲区。"""
    # 1) 区域 -> 大区 映射（显式规则，兼容「英国/英国区」两种写法）
    EUROPE_BASE = {'英国', '德国', '捷克', '法国', '波兰', '西班牙', '意大利'}
    APAC_BASE = {'澳洲', '日本', '韩国'}
    MAJOR_ORDER_L = ['美洲区', '欧洲区', '亚太区']

    def region_to_major(r):
        r = str(r).strip()
        base = r[:-1] if r.endswith('区') else r
        if base in EUROPE_BASE:
            return '欧洲区'
        if base in APAC_BASE:
            return '亚太区'
        return '美洲区'  # 其余全部归入美洲区

    # 2) 逐文件流式读取「劳务工-考勤表」：用 openpyxl read_only 模式逐行读取，
    #    仅保留所需列且 实际补签数 > 0，避免 53 列 × 20万行 一次性载入撑爆内存
    from openpyxl import load_workbook
    _labor_cols = ['工号', '员工名称', '工种', '区域', '仓库', '组', '考勤日期', '班次',
                   '首打卡补签时间', '末打卡补签时间', '休息开始补签时间', '休息结束补签时间',
                   '异常原因', '修改原因', '实际补签数', '应打卡数', '应补签数']
    frames = []
    for f in LABOR_SRCS:
        wb = load_workbook(f, read_only=True, data_only=True)
        ws = wb[LABOR_SHEET]
        it = ws.iter_rows(values_only=True)
        header = list(next(it))
        cidx = {name: i for i, name in enumerate(header)}
        jcols = [cidx[c] for c in _labor_cols]
        recs = {c: [] for c in _labor_cols}
        for row in it:
            for c, j in zip(_labor_cols, jcols):
                recs[c].append(row[j] if j < len(row) else None)
        wb.close()
        frames.append(pd.DataFrame(recs))
    L = pd.concat(frames, ignore_index=True)
    L['三级部门'] = L['区域'].astype(str).map(region_to_major)

    # 按显式规则得到大区排序与区域排序（区域顺序复用正式工架构顺序 REGION_ORDER，并在末尾补上没有列出的区域）
    all_regions_set = set(L['区域'].dropna().astype(str).unique())
    major_order_l = [m for m in MAJOR_ORDER_L if m in set(L['三级部门'])]
    region_order_l = {}
    for m in major_order_l:
        ordered = [r for r in REGION_ORDER.get(m, []) if r in all_regions_set]
        extras = [r for r in all_regions_set if region_to_major(r) == m and r not in ordered]
        extras.sort()
        region_order_l[m] = ordered + extras
    L = L.rename(columns={'区域': '四级部门', '仓库': '五级部门', '组': '六级部门',
                          '员工名称': '姓名', '工种': '职位', '异常原因': '补签事由', '修改原因': '备注'})
    L['六级部门'] = L['六级部门'].fillna('部门直属')
    L['五级部门'] = L['五级部门'].fillna('部门直属')
    L['补签事由'] = L['补签事由'].fillna('')
    L['备注'] = L['备注'].fillna('')
    L['职位'] = L['职位'].fillna('—')
    L['班次'] = L['班次'].fillna('')
    # 数值列统一转换（原始可能为字符串）
    L['实际补签数'] = pd.to_numeric(L['实际补签数'], errors='coerce').fillna(0)
    L['应打卡数'] = pd.to_numeric(L['应打卡数'], errors='coerce').fillna(0)
    L['应补签数'] = pd.to_numeric(L['应补签数'], errors='coerce').fillna(0)
    # 格式化补签时间：合并首打卡/末打卡/休息开始/休息结束四个补签时间字段的非空值
    _time_cols = ['首打卡补签时间', '末打卡补签时间', '休息开始补签时间', '休息结束补签时间']
    def _fmt_time(v):
        if pd.isna(v) or v is None or v == '':
            return ''
        if isinstance(v, (datetime, dt_time)):
            return v.strftime('%H:%M')
        s = str(v).strip()
        if s.lower() in ('', 'nan', 'none'):
            return ''
        # 若源表已为 HH:MM:SS 字符串，截断为 HH:MM
        if re.match(r'^\d{1,2}:\d{2}:\d{2}$', s):
            return s[:-3]
        return s
    for c in _time_cols:
        L[c] = L[c].apply(_fmt_time)
    # 封顶规则：一个人一天的应补签数合计最大为 2（对应上下班两次打卡），
    # 按 (工号, 考勤日期) 将应补签数合计截断为 2；实际补签数（已补签数）同步不超过封顶后的应补签数，保持 未完成 >= 0
    L = L.sort_values(['工号', '考勤日期']).reset_index(drop=True)
    _g = L.groupby(['工号', '考勤日期'])['应补签数']
    _cum = _g.cumsum()
    _prev = _cum - L['应补签数']
    L['应补签数'] = np.minimum((2 - _prev).clip(lower=0), L['应补签数'])
    L['实际补签数'] = np.minimum(L['实际补签数'], L['应补签数'])
    # 补签记录 = 应补签数 > 0 或 实际补签数 > 0（任一涉及补签的行均纳入求和）
    L['is_record'] = (L['应补签数'] > 0) | (L['实际补签数'] > 0)
    L['dt'] = pd.to_datetime(L['考勤日期'], errors='coerce')
    L['ym'] = L['dt'].dt.strftime('%Y-%m')
    L['ymd'] = L['dt'].dt.strftime('%Y-%m-%d')

    # 补签记录用于板块一~四求和、员工下钻、Top10
    L_rec = L[L['is_record']].copy()
    L_rec['审批状态'] = '已完成'
    L_rec['top_exclude'] = L_rec.apply(lambda x: is_top_exclude(x['补签事由'], x['备注']), axis=1)

    def add_labor_rate(agg, df_all):
        """给 agg_period 结果补充 补签率 = 应补签数 / 应打卡数（基于全量考勤行，非仅补签记录）。"""
        ydk = float(df_all['应打卡数'].sum()); ybq = float(df_all['应补签数'].sum())
        agg['ydkTotal'] = int(ydk); agg['ybqTotal'] = int(ybq)
        agg['rateTotal'] = round(ybq / ydk * 100, 1) if ydk else 0.0
        def _rate(sy, sx):
            y = float(sy); x = float(sx)
            return (round(x / y * 100, 1) if y else 0.0, int(y), int(x))
        g = df_all.groupby('三级部门').agg(ydk=('应打卡数', 'sum'), ybq=('应补签数', 'sum'))
        mrate = {k: _rate(v['ydk'], v['ybq']) for k, v in g.iterrows()}
        for r in agg['major']:
            rt, y, x = mrate.get(r['name'], (0, 0, 0)); r['rate'] = rt; r['ydk'] = y; r['ybq'] = x
        g = df_all.groupby(['三级部门', '四级部门']).agg(ydk=('应打卡数', 'sum'), ybq=('应补签数', 'sum'))
        drate = {(k[0], k[1]): _rate(v['ydk'], v['ybq']) for k, v in g.iterrows()}
        for r in agg['detail']:
            rt, y, x = drate.get((r['major'], r['region']), (0, 0, 0)); r['rate'] = rt; r['ydk'] = y; r['ybq'] = x
        g = df_all.groupby(['三级部门', '四级部门', '五级部门']).agg(ydk=('应打卡数', 'sum'), ybq=('应补签数', 'sum'))
        wrate = {(k[0], k[1], k[2]): _rate(v['ydk'], v['ybq']) for k, v in g.iterrows()}
        for r in agg['warehouse']:
            rt, y, x = wrate.get((r['major'], r['region'], r['wh']), (0, 0, 0)); r['rate'] = rt; r['ydk'] = y; r['ybq'] = x
        g = df_all.groupby(['三级部门', '四级部门', '五级部门', '六级部门']).agg(ydk=('应打卡数', 'sum'), ybq=('应补签数', 'sum'))
        grate = {(k[0], k[1], k[2], k[3]): _rate(v['ydk'], v['ybq']) for k, v in g.iterrows()}
        for r in agg['group']:
            rt, y, x = grate.get((r['major'], r['region'], r['wh'], r['group']), (0, 0, 0)); r['rate'] = rt; r['ydk'] = y; r['ybq'] = x
        return agg

    # 3) 聚合数据（板块一~四：应补签数/实际补签数求和 + 补签率）
    L_agg = L_rec[['三级部门', '四级部门', '五级部门', '六级部门', '审批状态', 'ym', 'ymd', '应补签数', '实际补签数']].copy()
    months_l = sorted(L['ym'].dropna().unique())
    days_l = sorted(L['ymd'].dropna().unique())
    data_l = {}
    for m in months_l:
        data_l[m] = agg_period_labor(L_agg[L_agg['ym'] == m], major_order_l, region_order_l)
        add_labor_rate(data_l[m], L[L['ym'] == m])
    for d_ in days_l:
        data_l[d_] = agg_period_labor(L_agg[L_agg['ymd'] == d_], major_order_l, region_order_l)
        add_labor_rate(data_l[d_], L[L['ymd'] == d_])

    # 4) 员工明细（板块四下钻）：按 (姓名, 工号, 工种, 考勤日期, 班次) 聚合，
    #    保留「首打卡补签时间」「末打卡补签时间」两列（休息补签时间不展示）。
    #    为压缩 HTML 体积，明细改用「位置数组」存储
    #    [姓名, 工号, 工种, 考勤日期, 班次, 首打卡补签时间, 末打卡补签时间]，前端按 empHeaders 顺序渲染。
    #    每组按考勤日期降序裁剪为前 EMP_DETAIL_CAP 条（报表展示用，全量见 Excel「组下员工明细」），
    #    并通过 empCount 记录每组真实总条数用于展示。
    def _join_time(s):
        return '; '.join(sorted(set(x for x in s if x)))
    empagg = L_rec.groupby(['三级部门', '四级部门', '五级部门', '六级部门',
                            '姓名', '工号', '职位', '考勤日期', '班次'], as_index=False).agg(
        首打卡补签时间=('首打卡补签时间', _join_time),
        末打卡补签时间=('末打卡补签时间', _join_time),
    )
    empagg['考勤日期'] = empagg['考勤日期'].astype(str)
    empagg = empagg.sort_values('考勤日期', ascending=False)

    EMP_DETAIL_CAP = 50
    empIndex = {}
    empCount = {}
    for _, r in empagg.iterrows():
        k = f"{r['三级部门']}|{r['四级部门']}|{r['五级部门']}|{r['六级部门']}"
        empCount[k] = empCount.get(k, 0) + 1
        if len(empIndex.get(k, [])) < EMP_DETAIL_CAP:
            empIndex.setdefault(k, []).append([
                r['姓名'], r['工号'], r['职位'],
                r['考勤日期'], r['班次'], r['首打卡补签时间'], r['末打卡补签时间'],
            ])

    # 5) 各区 Top10 员工（板块五，按整体统计，不随日期筛选）
    topagg = L_rec.groupby(['三级部门', '四级部门', '工号', '姓名', '职位']).agg(
        补签次数=('应补签数', 'sum'),
        已补签数=('实际补签数', 'sum'),
        主属仓=('五级部门', lambda s: s.value_counts().sort_index().idxmax()),
        主属组=('六级部门', lambda s: s.value_counts().sort_index().idxmax()),
    ).reset_index()
    topEmpIndex = {}
    for (maj, reg), g in topagg.groupby(['三级部门', '四级部门']):
        g = g[g['补签次数'] > 3].sort_values('补签次数', ascending=False).head(10)
        arr = [{'count': int(rr['补签次数']), 'done': int(rr['已补签数']), 'ing': int(rr['补签次数'] - rr['已补签数']),
                'name': rr['姓名'], 'gong': rr['工号'], 'gongzhong': rr['职位'],
                'wh': rr['主属仓'], 'group': rr['主属组']} for _, rr in g.iterrows()]
        topEmpIndex[f"{maj}|{reg}"] = arr

    LABOR_EMP_KEYS = ['姓名', '工号', '工种', '考勤日期', '班次', '首打卡补签时间', '末打卡补签时间']
    LABOR_EMP_HEADERS = ['姓名', '工号', '工种', '考勤日期', '班次', '首打卡补签时间', '末打卡补签时间']
    LABOR_SUBTITLE = '维度：大区（劳务工架构）× 区域　|　口径：补签合计 = 应补签数，已完成 = 已补签数，未完成 = 应补签数 − 已补签数'

    LABOR_NOTE = """
    <div class="note-section">
      <div class="note-label">数据来源</div>
      <ul class="note-list">
        <li>合并 <code>劳务工补签-6月.xlsx</code> 与 <code>劳务工补签-7月.xlsx</code> 的「劳务工-考勤表」sheet。</li>
        <li>劳务工无「补签申请」概念，本报告将 <strong>应补签数 &gt; 0 或 实际补签数 &gt; 0</strong> 的每日考勤行纳入「补签记录」，并对 <strong>应补签数 / 实际补签数（已补签数）</strong> 求和。</li>
        <li><strong>大区映射规则</strong>：欧洲区 = 英国/德国/捷克/法国/波兰/西班牙/意大利；亚太区 = 澳洲/日本/韩国；其余区域统一归入美洲区。</li>
      </ul>
    </div>
    <div class="note-divider"></div>
    <div class="note-section">
      <div class="note-label">板块说明</div>
      <ul class="note-list">
        <li><strong>板块一~四</strong>：按所选日期/月份对「应补签数 / 实际补签数（已补签数）」求和，结构与正式工一致（大区×区域×仓×组）。其中 <strong>补签合计 = 应补签数</strong>、<strong>已完成 = 已补签数</strong>、<strong>未完成 = 应补签数 − 已补签数</strong>。</li>
        <li><strong>补签率</strong> = 应补签数 ÷ 应打卡数（基于全量考勤行，分母取该范围全部应打卡点数，非仅补签记录），在 KPI 卡与各大区/区域/仓/组表中展示。</li>
        <li><strong>板块四下钻</strong>：点击组可展开该组下补签员工明细，展示姓名、工号、工种、考勤日期、班次、首打卡补签时间、末打卡补签时间。同一天同一班次的多条记录会合并为一行。</li>
        <li><strong>板块五 Top10</strong>：按区域取补签次数前 10 名员工（<strong>整体统计，不随日期筛选</strong>），附带主属仓、主属组。</li>
        <li><strong>应补签数口径</strong>：一个人一天的应补签数合计最大为 2，对应上下班两次打卡；超过 2 的情况已按员工+考勤日期将应补签数合计封顶取 2（截断多余部分），并同步将实际补签数限制在封顶后的应补签数内，保证 未完成 ≥ 0。</li>
      </ul>
    </div>
    """

    return {
        'months': months_l, 'days': days_l, 'data': data_l,
        'empIndex': empIndex, 'empCount': empCount, 'topEmpIndex': topEmpIndex,
        'empKeys': LABOR_EMP_KEYS, 'empHeaders': LABOR_EMP_HEADERS,
        'type': 'labor', 'subtitle': LABOR_SUBTITLE, 'noteHtml': LABOR_NOTE,
    }

# 释放正式工阶段的大对象（pdf/sub 等原始明细），避免与劳务工读取叠加触发 OOM
import gc as _gc
for _v in ('pdf', 'sub', 'emp_all', 'roster', 'g_major', 'cnt'):
    if _v in globals():
        del globals()[_v]
_gc.collect()

labor_payload = build_labor_payload()

# ===== 考勤确认及时性（劳务工）看板数据 =====
ATTEND_FILES = {
    '2026-07': r"D:/Documents/Downloads/考勤确认及时性劳务工（07.01-07.31）(1).xlsx",
    '2026-06': r"D:/Documents/Downloads/考勤确认及时性劳务工（06.01-06.30）(1).xlsx",
}
ATTEND_PERIOD_LABELS = {'2026-07': '本期 2026-07', '2026-06': '上期 2026-06'}
# 劳务工考勤确认及时性（v2 明细）数据源（2026-09-15 起）：改用《劳务工工时》Excel 的「考勤」sheet
LABOR_GS_FILES = [
    r"D:/【每月数据处理！！】/3.工时数据处理/2026/6月（新）/1 数据收集/2.劳务工工时-20260702.xlsx",
    r"D:/【每月数据处理！！】/3.工时数据处理/2026/7月（新）/1 数据收集/2.劳务工工时-20260803.xlsx",
]
ATTEND_MAJOR_ORDER = ['美洲区', '欧洲区', '亚太区', 'FBU HRBP Dept.']
# 考勤确认及时性 sheet 的「区域」口径与劳务工架构不同（如新泽西区/加州区/休斯顿区），按已知归属归入三大区
REGION_TO_MAJOR = {
    '亚特兰大区': '美洲区', '休斯顿区': '美洲区', '加州区': '美洲区', '加拿大区': '美洲区',
    '新泽西区': '美洲区', '芝加哥区': '美洲区', '萨凡纳区': '美洲区', '达拉斯区': '美洲区', '迈阿密区': '美洲区',
    '西雅图区': '美洲区', '诺福克区': '美洲区', '印第安纳区': '美洲区', '墨西哥区': '美洲区',
    '德国区': '欧洲区', '捷克区': '欧洲区', '法国区': '欧洲区', '波兰区': '欧洲区', '英国区': '欧洲区', '西班牙区': '欧洲区',
    '意大利区': '欧洲区',
    '澳洲区': '亚太区', '日本区': '亚太区', '韩国区': '亚太区',
}
# 收集未命中映射的区域，构建结束时告警，避免新增区域被静默归入「其他」
_UNMAPPED_REGIONS = {}


def _read_attend_sheet(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb['考勤确认及时性']
    recs = []
    for row in ws.iter_rows(values_only=True):
        reg, wh = row[1], row[2]
        if isinstance(wh, str) and wh != 'check' and isinstance(row[3], (int, float)):
            recs.append({
                '区域': reg, '仓库': wh,
                '应打卡次数': int(row[3] or 0),
                '实际打卡数': int(row[4] or 0),
                '应补签数': int(row[5] or 0),
                '已补签数': int(row[6] or 0),
                '考勤应确认数': int(row[7] or 0),
                '考勤实际确认数': int(row[8] or 0),
            })
    wb.close()
    return recs


def _agg_attend(recs):
    def block(rows):
        ydk = sum(r['应打卡次数'] for r in rows)
        ybq = sum(r['应补签数'] for r in rows)
        ybqd = sum(r['已补签数'] for r in rows)
        yqr = sum(r['考勤应确认数'] for r in rows)
        sjqr = sum(r['考勤实际确认数'] for r in rows)
        bqr = (ybq / ydk) if ydk else None
        qrl = (sjqr / yqr) if yqr else None
        return {'ydk': ydk, 'ybq': ybq, 'ybqd': ybqd, 'yqr': yqr, 'sjqr': sjqr, 'bqr': bqr, 'qrl': qrl}

    total = block(recs)
    major_map, region_map, wh_map = {}, {}, {}
    for r in recs:
        reg = r['区域']
        if reg and reg not in REGION_TO_MAJOR:
            _UNMAPPED_REGIONS[reg] = _UNMAPPED_REGIONS.get(reg, 0) + 1
        maj = REGION_TO_MAJOR.get(reg, '其他')
        major_map.setdefault(maj, []).append(r)
        region_map.setdefault((maj, r['区域']), []).append(r)
        wh_map.setdefault((maj, r['区域'], r['仓库']), []).append(r)
    major = [dict(major=m, **block(rs)) for m, rs in major_map.items()]
    region = [dict(major=m, region=rg, **block(rs)) for (m, rg), rs in region_map.items()]
    wh = [dict(major=m, region=rg, wh=w, **block(rs)) for (m, rg, w), rs in wh_map.items()]
    return {'total': total, 'major': major, 'region': region, 'wh': wh}


def build_attend_payload():
    periods_data = {k: _agg_attend(_read_attend_sheet(p)) for k, p in ATTEND_FILES.items()}
    # 区域排序：取两期并集，按本期(2026-07)应打卡次数降序
    base = periods_data['2026-07']
    reg_y = {}
    for r in base['region']:
        reg_y[(r['major'], r['region'])] = r['ydk']
    for k in periods_data:
        for r in periods_data[k]['region']:
            reg_y.setdefault((r['major'], r['region']), 0)
    region_order = {}
    for maj in ATTEND_MAJOR_ORDER:
        regs = sorted({rg for (m, rg) in reg_y if m == maj},
                      key=lambda rg: -reg_y.get((maj, rg), 0))
        region_order[maj] = regs
    # 仓排序：按本期应打卡次数降序
    wh_order = {}
    wh_y = {w['wh']: w['ydk'] for w in base['wh']}
    for r in base['wh']:
        wh_order.setdefault(r['major'] + '|' + r['region'], []).append(r['wh'])
    for k in wh_order:
        wh_order[k].sort(key=lambda w: -wh_y.get(w, 0))
    ATTEND_NOTE = (
        "<ul class='note-list'>"
        "<li><strong>数据来源</strong>：《考勤确认及时性劳务工（07.01-07.31）》与《考勤确认及时性劳务工（06.01-06.30）》的「考勤确认及时性」sheet，按区域×仓库聚合。</li>"
        "<li><strong>维度</strong>：区域按归属归入三大区（美洲区 / 欧洲区 / 亚太区）；加拿大区归入美洲区。区域口径与劳务工架构表存在差异（如新泽西区、加州区），已按物理仓归属对齐至三大区。</li>"
        "<li><strong>口径</strong>：补签率 = 应补签数 ÷ 应打卡次数；考勤确认率 = 考勤实际确认数 ÷ 考勤应确认数；各层级比率均按汇总值重算（非直接取源表行内比率）。应打卡次数 = 上下班卡×2。</li>"
        "<li><strong>对比</strong>：本期 = 2026-07，上期 = 2026-06；表格与卡片中「上」为上期值，Δpp 为百分点变化（补签率上升、考勤确认率下降均代表及时性变差）。</li>"
        "<li><strong>交互</strong>：点击「对比视图 / 本期 / 上期」切换；点击区域行可展开其下各仓明细。</li>"
        "</ul>"
    )
    return {
        'type': 'attend',
        'title': '考勤确认及时率（劳务工）',
        'subtitle': '维度：三大区 × 区域 × 仓　|　口径：补签率=应补签数÷应打卡次数，考勤确认率=考勤实际确认数÷考勤应确认数',
        'majorOrder': ATTEND_MAJOR_ORDER,
        'regionOrder': region_order,
        'whOrder': wh_order,
        'periods': [{'key': k, 'label': ATTEND_PERIOD_LABELS[k]} for k in ['2026-07', '2026-06']],
        'curKey': '2026-07', 'prevKey': '2026-06',
        'data': periods_data,
        'noteHtml': ATTEND_NOTE,
    }


# ===== 考勤确认及时性（劳务工）看板 v2：逐人逐日下钻（劳务工-考勤表）=====
# 复用 ATTEND_FILES；维度同 v1，但数据来自「劳务工-考勤表」逐日记录，支持选到具体日期 + 大区→区域→仓→组下钻
ATTEND_METRICS = ['ydk', 'sjk', 'ybq', 'sjq', 'yqr', 'sjqr', 'ldk']
ATTEND_METRIC_LABELS = {
    'ydk': '应打卡数', 'sjk': '实际打卡数', 'ybq': '应补签数', 'sjq': '实际补签数',
    'yqr': '应确认数', 'sjqr': '实际确认数', 'ldk': '漏打卡数',
}


def _read_attend_detail(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb['劳务工-考勤表']
    recs = []
    for row in ws.iter_rows(values_only=True):
        wh = row[7]
        d = row[10]
        if not (isinstance(wh, str) and wh) or not d:
            continue
        reg = row[6] if isinstance(row[6], str) else ''
        if reg and reg not in REGION_TO_MAJOR:
            _UNMAPPED_REGIONS[reg] = _UNMAPPED_REGIONS.get(reg, 0) + 1
        grp = row[8] if isinstance(row[8], str) and row[8] else '部门直属'
        try:
            recs.append({
                'date': str(d)[:10],
                'major': REGION_TO_MAJOR.get(reg, '其他'),
                'region': reg, 'wh': wh, 'grp': grp,
                'gong': row[3], 'name': row[2],
                'zg': row[4] if isinstance(row[4], str) else '',
                'ydk': int(row[44] or 0), 'sjk': int(row[45] or 0),
                'ybq': int(row[46] or 0), 'sjq': int(row[47] or 0),
                'yqr': int(row[48] or 0), 'sjqr': int(row[49] or 0),
                'ldk': int(row[50] or 0),
            })
        except Exception:
            continue
    wb.close()
    # 应补签数封顶：同一员工同一天合计最大 2（对应上下班两次打卡）
    from collections import defaultdict
    cap = defaultdict(lambda: [0, 0])
    out = []
    for r in recs:
        k = (r['gong'], r['date'])
        uy, us = cap[k]
        ny = min(uy + r['ybq'], 2)
        ns = min(us + r['sjq'], ny)
        rr = dict(r)
        rr['ybq'] = ny - uy
        rr['sjq'] = ns - us
        cap[k] = [ny, ns]
        out.append(rr)
    return out


def _read_attend_detail_gs(path):
    """从《劳务工工时》的「考勤」sheet 逐人逐日读取（该表无辅助列，按原始列推导指标）：
    考勤总数 yqr = 1/行；已确认数 sjqr = 确认状态 ∈ {已确认, 已复核}；
    应打卡数 ydk = 2/行（上下班各 1 次）；实际打卡数 sjk = 首/末打卡时间非空数（补签后已回填）；
    应补签数 ybq = 实际补签数 = 首/末补签时间非空数（补签后打卡时间已回填，未补签缺口本表不可见，按 0 计）；
    漏打卡数 ldk = ydk − sjk（本表基本为 0）。"""
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb['考勤']
    recs = []
    untimely_details = []

    def _nz(v):
        return isinstance(v, str) and v.strip() != ''

    def _s(v, t=False):
        # None/空串 → '—'；时间对象 → HH:MM；其余转字符串
        if v is None:
            return '—'
        if isinstance(v, str):
            return v.strip() or '—'
        if t and hasattr(v, 'strftime'):
            return v.strftime('%H:%M')
        return str(v)

    for row in ws.iter_rows(values_only=True):
        wh = row[7]
        d = row[10]
        if not (isinstance(wh, str) and wh) or not d:
            continue
        ds = str(d)[:10]
        if not _re.match(r'^\d{4}-\d{2}-\d{2}$', ds):   # 跳过表头等非数据行
            continue
        reg = row[6] if isinstance(row[6], str) else ''
        if reg and reg not in REGION_TO_MAJOR:
            _UNMAPPED_REGIONS[reg] = _UNMAPPED_REGIONS.get(reg, 0) + 1
        grp = row[8] if isinstance(row[8], str) and row[8] else '部门直属'
        sjk = int(_nz(row[20])) + int(_nz(row[21]))          # 首/末打卡时间
        sq = int(_nz(row[31])) + int(_nz(row[34]))           # 首/末打卡补签时间
        qr = row[35] if isinstance(row[35], str) else ''     # 确认状态
        recs.append({
            'date': ds,
            'major': REGION_TO_MAJOR.get(reg, '其他'),
            'region': reg, 'wh': wh, 'grp': grp,
            'gong': row[3], 'name': row[2],
            'zg': row[4] if isinstance(row[4], str) else '',
            'ydk': 2, 'sjk': sjk, 'ybq': sq, 'sjq': sq,
            'yqr': 1, 'sjqr': 1 if qr in ('已确认', '已复核') else 0,
            'ldk': 2 - sjk,
        })
        if qr not in ('已确认', '已复核'):
            untimely_details.append({
                'major': REGION_TO_MAJOR.get(reg, '其他'), 'region': reg, 'wh': wh, 'grp': grp,
                'date': ds,
                'row': [_s(row[2]), _s(row[3]), _s(row[4]), ds, _s(row[18]),
                        _s(row[20], t=True), _s(row[21], t=True), _s(qr),
                        _s(row[36]), _s(row[38])],
            })
    wb.close()
    # 应补签数封顶：同一员工同一天合计最大 2（对应上下班两次打卡）
    from collections import defaultdict
    cap = defaultdict(lambda: [0, 0])
    out = []
    for r in recs:
        k = (r['gong'], r['date'])
        uy, us = cap[k]
        ny = min(uy + r['ybq'], 2)
        ns = min(us + r['sjq'], ny)
        rr = dict(r)
        rr['ybq'] = ny - uy
        rr['sjq'] = ns - us
        cap[k] = [ny, ns]
        out.append(rr)
    return out, untimely_details


def _agg_attend_day(recs):
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
            if e is None:
                e = dict(base)
                store[key] = e
            for f in ATTEND_METRICS:
                e[f] = e.get(f, 0) + r[f]
    total = {f: sum(x.get(f, 0) for x in major.values()) for f in ATTEND_METRICS}
    # 按汇总值重算：未确认数 = 应确认数 - 实际确认数
    total['unconfirmed'] = total.get('yqr', 0) - total.get('sjqr', 0)
    for store in (major, detail, wh, grp):
        for e in store.values():
            e['unconfirmed'] = e.get('yqr', 0) - e.get('sjqr', 0)
    return {'total': total, 'major': list(major.values()),
            'detail': list(detail.values()), 'warehouse': list(wh.values()),
            'group': list(grp.values())}


def build_attend_payload_v2():
    all_recs = []
    untimely_details = []
    for p in LABOR_GS_FILES:
        _recs, _uts = _read_attend_detail_gs(p)
        all_recs.extend(_recs)
        untimely_details.extend(_uts)
    if _UNMAPPED_REGIONS:
        print('[警告] 以下区域未命中 REGION_TO_MAJOR，已被归入「其他」，请补映射：')
        for k, v in sorted(_UNMAPPED_REGIONS.items(), key=lambda x: -x[1]):
            print(f'    {k!r}  {v} 行')
    # 按日分组
    from collections import defaultdict
    by_day = defaultdict(list)
    for r in all_recs:
        by_day[r['date']].append(r)
    days_l = sorted(by_day)
    months_l = sorted({d[:7] for d in days_l})
    data_l = {d: _agg_attend_day(by_day[d]) for d in days_l}

    # 员工明细（全期，按 大区|区域|仓|组 聚合，每组限 50 条；下钻展示用）
    emp_agg = defaultdict(lambda: {'name': '', 'zg': '', 'ydk': 0, 'sjk': 0, 'ybq': 0,
                                    'sjq': 0, 'yqr': 0, 'sjqr': 0, 'ldk': 0})
    for r in all_recs:
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = emp_agg[k]
        a['name'] = r['name']
        a['zg'] = r['zg']
        for f in ATTEND_METRICS:
            a[f] += r[f]
    EMP_DETAIL_CAP = 50
    empIndex, empCount = {}, {}
    for (m, rg, w, g, gong), a in emp_agg.items():
        gk = f"{m}|{rg}|{w}|{g}"
        empCount[gk] = empCount.get(gk, 0) + 1
        if len(empIndex.get(gk, [])) < EMP_DETAIL_CAP:
            _unc = a['yqr'] - a['sjqr']
            _rate = round(a['sjqr'] / a['yqr'] * 100, 1) if a['yqr'] else 0
            empIndex.setdefault(gk, []).append(
                [a['name'], gong, a['zg'], a['yqr'], a['sjqr'], _unc, _rate])
    ATTEND_EMP_HEADERS = ['姓名', '工号', '工种', '考勤总数', '已确认数', '未确认数', '及时确认率(%)']

    # 组行角标：未及时确认明细索引（按 大区|区域|仓|组 分组，每组最多 50 条，全量计数另存；行尾附 ym/ymd 供前端按时间范围过滤）
    ATT_UNTIMELY_HEADERS = ['姓名', '工号', '工种', '考勤日期', '班次', '首打卡时间', '末打卡时间',
                            '确认状态', '考勤状态', '考勤异常原因']
    att_emp_index, att_emp_count = {}, {}
    for u in untimely_details:
        k = u['major'] + '|' + u['region'] + '|' + u['wh'] + '|' + u['grp']
        att_emp_count[k] = att_emp_count.get(k, 0) + 1
        if len(att_emp_index.get(k, [])) < EMP_DETAIL_CAP:
            att_emp_index.setdefault(k, []).append(u['row'] + [u['date'][:7], u['date']])
    for _k in att_emp_index:
        att_emp_index[_k].sort(key=lambda e: e[-1], reverse=True)  # 按考勤日期降序
    print('[劳务工及时率] 组角标未及时明细：%d 条，覆盖 %d 个组' % (
        sum(att_emp_count.values()), len(att_emp_count)))

    # Top 员工（按 大区|区域 聚合，未确认数（确认状态非 已确认/已复核）降序取前 10）
    top_by = defaultdict(list)
    for (m, rg, w, g, gong), a in emp_agg.items():
        top_by[(m, rg)].append({'name': a['name'], 'gong': gong, 'zg': a['zg'],
                                'wh': w, 'group': g, 'unc': a['yqr'] - a['sjqr']})
    topEmpIndex = {}
    for (m, rg), lst in top_by.items():
        lst = [x for x in lst if x['unc'] > 0]
        lst.sort(key=lambda x: -x['unc'])
        topEmpIndex[f"{m}|{rg}"] = lst[:10]

    # 劳务工考勤准确率 Top10：按漏打卡数（ldk）排序
    top_by_ldk = defaultdict(list)
    for (m, rg, w, g, gong), a in emp_agg.items():
        top_by_ldk[(m, rg)].append({'name': a['name'], 'gong': gong, 'zg': a['zg'],
                                    'wh': w, 'group': g, 'ldk': a['ldk']})
    topEmpIndexLdk = {}
    for (m, rg), lst in top_by_ldk.items():
        lst = [x for x in lst if x['ldk'] > 0]
        lst.sort(key=lambda x: -x['ldk'])
        topEmpIndexLdk[f"{m}|{rg}"] = lst[:10]

    ATTEND_SUBTITLE = ('维度：三大区 × 区域 × 仓 × 组（逐人逐日）　|　'
                       '口径：考勤确认及时率 = 已确认数 ÷ 考勤总数；'
                       '未确认数 = 考勤总数 − 已确认数')
    ATTEND_NOTE_V2 = """
    <div class="note-section">
      <div class="note-label">数据来源</div>
      <ul class="note-list">
        <li>两份《劳务工工时》Excel（2.劳务工工时-20260702 / 20260803）的「考勤」sheet，逐人逐日原始考勤记录（6月约 19.9 万行 + 7月约 21.3 万行）。</li>
        <li>区域按物理仓归属归入三大区（美洲区 / 欧洲区 / 亚太区；加拿大区归美洲区），与劳务工架构口径一致。</li>
      </ul>
    </div>
    <div class="note-divider"></div>
    <div class="note-section">
      <div class="note-label">板块说明</div>
      <ul class="note-list">
        <li><strong>板块一~四</strong>：按所选日期/月份对 考勤总数 / 已确认数 / 未确认数 求和，结构同正式工考勤确认及时率看板（大区×区域×仓×组）。</li>
        <li><strong>考勤确认及时率</strong>：考勤总数 = 考勤记录条数（每人每日 1 条）；已确认数 = 确认状态为「已确认 / 已复核」的记录数；未确认数 = 考勤总数 − 已确认数（含「未确认 / 已驳回」）；及时确认率 = 已确认数 ÷ 考勤总数（均按所选范围汇总值重算）。</li>
        <li><strong>板块四下钻</strong>：点击组可展开该组「未及时确认」员工明细（姓名/工号/工种/考勤日期/班次/首末打卡/确认状态/考勤状态/考勤异常原因），随日期/月份筛选联动，按考勤日期降序，每组最多展示 50 条。</li>
        <li><strong>板块五 Top10</strong>：按区域取补签数前 10 名员工（整体统计，不随日期筛选），附主属仓、主属组。</li>
      </ul>
    </div>
    """
    return {
        'type': 'laborAtt',
        'title': '考勤确认及时率（劳务工）',
        'subtitle': ATTEND_SUBTITLE,
        'majorOrder': ATTEND_MAJOR_ORDER,
        'regionOrder': REGION_ORDER,
        'months': months_l, 'days': days_l, 'data': data_l,
        'empIndex': att_emp_index, 'empCount': att_emp_count, 'topEmpIndex': topEmpIndex,
        'topEmpIndexLdk': topEmpIndexLdk,
        'empHeaders': ATT_UNTIMELY_HEADERS,
        'metrics': ATTEND_METRICS, 'metricLabels': ATTEND_METRIC_LABELS,
        'cols': [
            {'key': 'yqr', 'label': '考勤总数'},
            {'key': 'sjqr', 'label': '已确认数'},
            {'key': 'unconfirmed', 'label': '未确认数'},
            {'pct': True, 'num': 'sjqr', 'den': 'yqr', 'label': '及时确认率'},
        ],
        'noteHtml': ATTEND_NOTE_V2,
    }


attend_payload = build_attend_payload_v2()
attend_json = json.dumps(attend_payload, ensure_ascii=False, separators=(',', ':'))

# ===== 考勤确认及时性（劳务工）看板数据写入 Excel（在已生成的 xlsx 上追加 sheet）=====
# 注意：Excel 用 v1 聚合结构（按 2026-07 / 2026-06 两期），HTML 用 v2 逐日下钻结构
import pandas as pd
_attd = build_attend_payload()['data']
_ac, _ap = _attd['2026-07'], _attd['2026-06']

def _pct(v):
    return None if v is None else round(v * 100, 1)

def _attend_df(level):
    cm = {(x['major'], x.get('region'), x.get('wh')): x for x in _ac[level]}
    pm = {(x['major'], x.get('region'), x.get('wh')): x for x in _ap[level]}
    keys = sorted(set(cm) | set(pm),
                  key=lambda k: (ATTEND_MAJOR_ORDER.index(k[0]) if k[0] in ATTEND_MAJOR_ORDER else 99, str(k[1])))
    rows = []
    for k in keys:
        c, p = cm.get(k), pm.get(k)
        r = {'大区': k[0]}
        if level in ('region', 'wh'):
            r['区域'] = k[1]
        if level == 'wh':
            r['仓'] = k[2]
        r['应打卡次数(本期)'] = c['ydk'] if c else None
        r['应补签数(本期)'] = c['ybq'] if c else None
        r['补签率(本期)%'] = _pct(c['bqr']) if c else None
        r['考勤确认率(本期)%'] = _pct(c['qrl']) if c else None
        r['应打卡次数(上期)'] = p['ydk'] if p else None
        r['应补签数(上期)'] = p['ybq'] if p else None
        r['补签率(上期)%'] = _pct(p['bqr']) if p else None
        r['考勤确认率(上期)%'] = _pct(p['qrl']) if p else None
        r['补签率Δpp'] = round((c['bqr'] - p['bqr']) * 100, 1) if (c and p and c['bqr'] is not None and p['bqr'] is not None) else None
        r['考勤确认率Δpp'] = round((c['qrl'] - p['qrl']) * 100, 1) if (c and p and c['qrl'] is not None and p['qrl'] is not None) else None
        rows.append(r)
    return pd.DataFrame(rows)

_att_major = _attend_df('major')
_att_region = _attend_df('region')
_att_wh = _attend_df('wh')
_tot = {'大区': '合计', '应打卡次数(本期)': _ac['total']['ydk'], '应补签数(本期)': _ac['total']['ybq'],
        '补签率(本期)%': _pct(_ac['total']['bqr']), '考勤确认率(本期)%': _pct(_ac['total']['qrl']),
        '应打卡次数(上期)': _ap['total']['ydk'], '应补签数(上期)': _ap['total']['ybq'],
        '补签率(上期)%': _pct(_ap['total']['bqr']), '考勤确认率(上期)%': _pct(_ap['total']['qrl']),
        '补签率Δpp': round((_ac['total']['bqr'] - _ap['total']['bqr']) * 100, 1),
        '考勤确认率Δpp': round((_ac['total']['qrl'] - _ap['total']['qrl']) * 100, 1)}
_att_major = pd.concat([_att_major, pd.DataFrame([_tot])], ignore_index=True)

from openpyxl import load_workbook as _load_wb
_wbx = _load_wb(OUT_XLSX)
for _sn in ('考勤确认及时性_大区', '考勤确认及时性_区域', '考勤确认及时性_仓'):
    if _sn in _wbx.sheetnames:
        del _wbx[_sn]
_wbx.save(OUT_XLSX)
with pd.ExcelWriter(OUT_XLSX, engine='openpyxl', mode='a', if_sheet_exists='replace') as xw:
    _att_major.to_excel(xw, sheet_name='考勤确认及时性_大区', index=False)
    _att_region.to_excel(xw, sheet_name='考勤确认及时性_区域', index=False)
    _att_wh.to_excel(xw, sheet_name='考勤确认及时性_仓', index=False)
print("Excel 已追加考勤确认及时性 sheet（大区/区域/仓）")

# ===== 正式工 考勤确认及时性（数据源：正式工-考勤记录）=====
# 口径（用户确认 2026-09-04）：
#   未及时确认考勤 = 考勤状态=异常 且 (异常备注 不含 迟到/早退)；及时确认率 = (考勤总数 - 未及时确认) ÷ 考勤总数（分母为全部考勤）
#   维度：三级部门=大区；四级部门=区域（去 HRBP部/行政部/渠道部/交付管理部/商务部/财务部 后缀后归入三大区）；五级=仓；六级=组
FORMAL_ATT_FILES = [
    r'D:\Documents\Downloads\正式工-7月考勤记录.xlsx',
    r'D:\Documents\Downloads\正式工-6月考勤记录.xlsx',
]
FORMAL_ATT_SHEET = '考勤记录'


def _formal_major(l3, l4):
    l3 = str(l3).strip()
    l4 = str(l4).strip()
    if l3 in ('欧洲区', '美洲区', '亚太区'):
        return l3
    core = _re.sub(r'(HRBP部|行政部|渠道部|交付管理部|商务部|财务部)$', '', l4)
    if core in ('欧洲区', '美洲区', '亚太区'):
        return core
    if core in REGION_TO_MAJOR:
        return REGION_TO_MAJOR[core]
    for _maj in ('欧洲区', '美洲区', '亚太区'):
        if l4.startswith(_maj):
            return _maj
    return '其他'


def _fs(v):
    """NaN 安全转字符串"""
    return str(v).strip() if pd.notna(v) else ''


FORMAL_UNTIMELY_DETAILS = []  # 未及时确认员工明细（用于组行角标展开，2026-09-18）


def _build_formal_recs():
    recs = []
    excluded = {'财务部': 0, '四级部门为空': 0}
    for f in FORMAL_ATT_FILES:
        df = pd.read_excel(f, sheet_name=FORMAL_ATT_SHEET)
        df['_d'] = pd.to_datetime(df['考勤日期'], errors='coerce')
        for _, r in df.iterrows():
            d = r['_d']
            if pd.isna(d):
                continue
            # 空部门保持 ''，避免 str(NaN) 产生 'nan' 区域
            l3 = str(r['三级部门']).strip() if pd.notna(r['三级部门']) else ''
            l4 = str(r['四级部门']).strip() if pd.notna(r['四级部门']) else ''
            # 剔除财务部（FBU财务部 / ××区财务部），口径：考勤确认及时率不看财务（用户确认 2026-09-17）
            if ('财务部' in l3) or ('财务部' in l4):
                excluded['财务部'] += 1
                continue
            if l3 == 'FBU HRBP Dept.':
                # HRBP 部单独成大区（与补签率视图口径一致）；美洲支持HRBP组剔除不展示
                if l4 == '美洲支持HRBP组':
                    continue
                major = 'FBU HRBP Dept.'
                region = l4
            else:
                # 四级部门为空无法归属区域，剔除（即此前区域下拉里出现的 "nan"，用户确认 2026-09-17）
                if not l4:
                    excluded['四级部门为空'] += 1
                    continue
                major = _formal_major(l3, l4)
                if major == '其他':
                    print('[警告] 正式工未命中大区映射：三级=%r 四级=%r' % (l3, l4))
                core = _re.sub(r'(HRBP部|行政部|渠道部|交付管理部|商务部|财务部)$', '', l4)
                region = core if core else l4
            wh = r['五级部门'] if pd.notna(r['五级部门']) else '部门直属'
            grp = r['六级部门'] if pd.notna(r['六级部门']) else '部门直属'
            status = str(r['考勤状态'])
            is_abn = (status == '异常')
            untimely = False
            if is_abn:
                yc = str(r['异常备注'])
                bz = str(r['备注'])
                has_lc = ('迟到' in yc or '早退' in yc or '迟到' in bz or '早退' in bz)
                untimely = not has_lc
            recs.append({
                'major': major, 'region': region, 'wh': str(wh), 'grp': str(grp),
                'name': str(r['姓名']) if pd.notna(r['姓名']) else '',
                'gong': str(r['工号']) if pd.notna(r['工号']) else '',
                'date': d.strftime('%Y-%m-%d'), 'ym': d.strftime('%Y-%m'),
                'total': 1, 'normal': 1 if status == '正常' else 0,
                'abnormal': 1 if is_abn else 0, 'untimely': 1 if untimely else 0,
            })
            if untimely:
                gong_id = _fs(r['工号'])
                FORMAL_UNTIMELY_DETAILS.append({
                    'major': major, 'region': region, 'wh': str(wh), 'grp': str(grp),
                    'ym': d.strftime('%Y-%m'), 'ymd': d.strftime('%Y-%m-%d'),
                    # 行字段顺序与 GEN_EMP_HEADERS 一致：姓名 工号 部门 职位 职级 考勤日期 星期 当前班次 首打卡 末打卡 考勤状态 异常备注
                    'row': [
                        _fs(r['姓名']), gong_id, _fs(r['四级部门']),
                        pos_map.get(gong_id, '—'), lvl_map.get(gong_id, '—'),
                        d.strftime('%Y-%m-%d'), _fs(r['星期']), _fs(r['当前班次']),
                        _fs(r['首打卡']), _fs(r['末打卡']), _fs(r['考勤状态']), _fs(r['异常备注']),
                    ],
                })
    print('[正式工及时率] 剔除记录：', excluded)
    return recs


def _agg_formal(recs, keys):
    from collections import defaultdict
    by_day = defaultdict(list)
    by_month = defaultdict(list)
    for r in recs:
        by_day[r['date']].append(r)
        by_month[r['ym']].append(r)

    def agg(store):
        major, detail, wh, grp = {}, {}, {}, {}
        for r in store:
            m, rg, w, g = r['major'], r['region'], r['wh'], r['grp']
            for key, st, base in (
                (m, major, {'name': m}),
                (m + '|' + rg, detail, {'major': m, 'region': rg}),
                (m + '|' + rg + '|' + w, wh, {'major': m, 'region': rg, 'wh': w}),
                (m + '|' + rg + '|' + w + '|' + g, grp, {'major': m, 'region': rg, 'wh': w, 'group': g}),
            ):
                e = st.get(key)
                if e is None:
                    e = dict(base)
                    st[key] = e
                for kk in keys:
                    e[kk] = e.get(kk, 0) + r[kk]
        tot = {kk: sum(x.get(kk, 0) for x in major.values()) for kk in keys}
        return {'total': tot, 'major': list(major.values()), 'detail': list(detail.values()),
                'warehouse': list(wh.values()), 'group': list(grp.values())}

    data = {}
    for d, rs in by_day.items():
        data[d] = agg(rs)
    for m, rs in by_month.items():
        data[m] = agg(rs)
    return data, sorted(by_day), sorted(by_month)


_formal_recs = _build_formal_recs()
_formal_keys = ['total', 'normal', 'abnormal', 'untimely']
_formal_data, _formal_days, _formal_months = _agg_formal(_formal_recs, _formal_keys)
# formalAtt 需 timely = total - untimely（用于及时确认率分子）
for _blk in _formal_data.values():
    for _lvl in ('major', 'detail', 'warehouse', 'group'):
        for _r in _blk[_lvl]:
            _r['timely'] = _r['total'] - _r['untimely']
    _blk['total']['timely'] = _blk['total']['total'] - _blk['total']['untimely']
def _build_formal_top(recs, metric, min_val=0):
    from collections import defaultdict
    agg = defaultdict(lambda: {'name': '', 'gong': '', 'major': '', 'region': '', 'wh': '', 'group': '',
                                 'pos': '—', 'total': 0, 'abnormal': 0, 'untimely': 0})
    for r in recs:
        k = (r['major'], r['region'], r['wh'], r['grp'], r['gong'])
        a = agg[k]
        a['name'] = r['name']; a['gong'] = r['gong']
        a['major'] = r['major']; a['region'] = r['region']; a['wh'] = r['wh']; a['group'] = r['grp']
        a['pos'] = pos_map.get(r['gong'], '—')
        a['total'] += r['total']; a['abnormal'] += r['abnormal']; a['untimely'] += r['untimely']
    by_region = defaultdict(list)
    for a in agg.values():
        by_region[(a['major'], a['region'])].append(a)
    top = {}
    for (m, rg), lst in by_region.items():
        lst = [x for x in lst if x[metric] > min_val]
        lst.sort(key=lambda x: -x[metric])
        top[f"{m}|{rg}"] = lst[:10]
    return top

_formal_top_untimely = _build_formal_top(_formal_recs, 'untimely', min_val=3)

# 组行角标：未及时确认员工明细索引（按 大区|区域|仓|组 分组，每组最多 50 条，全量计数另存）
GEN_EMP_HEADERS = ['姓名', '工号', '部门', '职位', '职级', '考勤日期', '星期',
                   '当前班次', '首打卡时间', '末打卡时间', '考勤状态', '异常备注']
GEN_EMP_CAP = 50
gen_emp_index, gen_emp_count = {}, {}
for _u in FORMAL_UNTIMELY_DETAILS:
    _k = _u['major'] + '|' + _u['region'] + '|' + _u['wh'] + '|' + _u['grp']
    gen_emp_count[_k] = gen_emp_count.get(_k, 0) + 1
    if len(gen_emp_index.get(_k, [])) < GEN_EMP_CAP:
        gen_emp_index.setdefault(_k, []).append(_u['row'] + [_u['ym'], _u['ymd']])
for _k in gen_emp_index:
    gen_emp_index[_k].sort(key=lambda e: e[-1], reverse=True)  # 按考勤日期降序
print('[正式工及时率] 组角标未及时明细：%d 条，覆盖 %d 个组' % (
    len(FORMAL_UNTIMELY_DETAILS), len(gen_emp_count)))

# formalAtt 专用：按天仅保留 大区/区域 两级（仓/组明细仅按月提供），以控制 HTML 体积
_formal_data_att = {}
for _k, _blk in _formal_data.items():
    _is_month = len(_k) == 7
    _formal_data_att[_k] = {
        'total': _blk['total'],
        'major': _blk['major'],
        'detail': _blk['detail'],
        'warehouse': _blk['warehouse'] if _is_month else [],
        'group': _blk['group'] if _is_month else [],
    }

FORMAL_NOTE = (
    "<ul class='note-list'>"
    "<li><strong>数据来源</strong>：合并 <code>正式工-7月考勤记录.xlsx</code> 与 <code>正式工-6月考勤记录.xlsx</code> 的「考勤记录」sheet（逐人逐日原始考勤，共约 9.8 万行）。</li>"
    "<li><strong>维度</strong>：三级部门=大区（欧洲区/美洲区/亚太区/FBU HRBP Dept.）；四级部门=区域（去除 HRBP部/行政部/渠道部/交付管理部/商务部/财务部 后缀后按物理仓归属归入三大区；HRBP 各部单独成大区，区域保留「××区HRBP部」原名）；五级部门=仓；六级部门=组。范围仅含美洲区/欧洲区/亚太区及各区对应 HRBP 部；财务部（FBU财务部）整部剔除不展示；四级部门为空、无法归属区域的记录剔除；美洲支持HRBP组剔除不展示（与补签率口径一致）。</li>"
    "<li><strong>考勤确认及时率</strong>：未及时确认 = 考勤状态=异常 且 异常备注不含「迟到/早退」（即缺卡类：缺少首打卡/末打卡等）；及时确认率 = (考勤总数 − 未及时确认) ÷ 考勤总数（分母为全部考勤，约为 98%）。迟到/早退视为已及时确认。</li>"
    "<li><strong>交互</strong>：点击「按天/按月」或选择月份/日期切换时间范围；点击大区/区域/仓行可逐级下钻至组；组行带角标，点击可展开该组「未及时确认」员工明细（姓名/工号/部门/职位/职级/考勤日期/星期/当前班次/首末打卡/考勤状态/异常备注；职位、职级取自 2026-08-24 花名册按工号匹配，未匹配显示「—」，每组最多展示 50 条、按考勤日期降序）。</li>"
    "</ul>"
)

formal_att_payload = {
    'type': 'formalAtt', 'title': '考勤确认及时率（正式工）',
    'subtitle': '维度：大区×区域×仓×组 | 口径：未及时确认=异常且异常备注不含迟到/早退；及时确认率=(考勤总数−未及时确认)÷考勤总数',
    'majorOrder': ATTEND_MAJOR_ORDER, 'regionOrder': REGION_ORDER, 'months': _formal_months, 'days': _formal_days, 'data': _formal_data_att,
    'aggKeys': ['total', 'untimely', 'timely'],
    'cols': [
        {'key': 'total', 'label': '考勤总数'},
        {'key': 'timely', 'label': '已确认数'},
        {'key': 'untimely', 'label': '未及时确认'},
        {'pct': True, 'num': 'timely', 'den': 'total', 'label': '及时确认率'},
    ],
    'noteHtml': FORMAL_NOTE,
    'empIndex': gen_emp_index, 'empCount': gen_emp_count,
    'empHeaders': GEN_EMP_HEADERS,
    'topEmpIndex': _formal_top_untimely,
    'topMetric': 'untimely',
    'topMetricLabel': '未及时确认',
    'topCaption': '五、各区 Top10 员工（按区域内员工未及时确认考勤数排序，整体统计不随日期筛选）',
}
formal_att_json = json.dumps(formal_att_payload, ensure_ascii=False, separators=(',', ':'))
print("[正式工] 考勤总数=%d 正常=%d 异常=%d 未及时确认=%d 准确率=%.1f%% 及时确认率=%.1f%%" % (
    sum(_formal_data[m]['total']['total'] for m in _formal_months),
    sum(_formal_data[m]['total']['normal'] for m in _formal_months),
    sum(_formal_data[m]['total']['abnormal'] for m in _formal_months),
    sum(_formal_data[m]['total']['untimely'] for m in _formal_months),
    sum(_formal_data[m]['total']['normal'] for m in _formal_months) / sum(_formal_data[m]['total']['total'] for m in _formal_months) * 100,
    (sum(_formal_data[m]['total']['total'] for m in _formal_months) - sum(_formal_data[m]['total']['untimely'] for m in _formal_months)) / sum(_formal_data[m]['total']['total'] for m in _formal_months) * 100,
))


# HTML with interactive day/month picker
json_data = json.dumps({
    'months': months, 'days': days, 'data': data, 'allEmp': allEmp,
    'empKeys': FORMAL_EMP_KEYS, 'empHeaders': FORMAL_EMP_HEADERS,
    'type': 'formal', 'subtitle': FORMAL_SUBTITLE,
}, ensure_ascii=False, separators=(',', ':'))

labor_json = json.dumps(labor_payload, ensure_ascii=False, separators=(',', ':'))

html_template = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>补签率统计</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:0;background:#f5f7fa;color:#1f2937;padding:28px}}
.wrap{{max-width:1100px;margin:0 auto}}
/* 顶部导航：一级=板块（准确率/及时性/补签），二级=人员类型（正式工/劳务工） */
.top-nav{{display:flex;align-items:center;justify-content:space-between;gap:14px;background:#fff;border-radius:14px;padding:12px 16px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);flex-wrap:wrap}}
.top-nav-left{{display:flex;align-items:center;gap:10px;min-width:0}}
.top-nav-icon{{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#2563eb,#60a5fa);color:#fff;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}}
.top-nav-title{{display:flex;flex-direction:column;min-width:0}}
.top-nav-title strong{{font-size:15px;color:#111;font-weight:700;white-space:nowrap}}
.top-nav-title small{{font-size:11px;color:#6b7280;margin-top:1px}}
.top-nav-tabs{{display:flex;align-items:center;gap:6px;background:#f1f5f9;border-radius:24px;padding:4px;flex-shrink:0}}
.top-nav-tabs button{{border:none;background:transparent;color:#475569;font-size:13px;cursor:pointer;padding:7px 16px;border-radius:20px;transition:.15s;font-weight:500}}
.top-nav-tabs button.active{{background:#2563eb;color:#fff;font-weight:600;box-shadow:0 2px 6px rgba(37,99,235,.25)}}
.top-nav-tabs button:not(.active):hover{{background:#e2e8f0;color:#1e293b}}
body:not(.labor-rate) .rate-col{{display:none}}
body:not(.labor-rate) .rate{{display:none}}
.rate{{font-weight:700;color:#b45309}}
.view-panel.hidden{{display:none}}
.view-placeholder{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:80px 20px;background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,.08);text-align:center}}
.view-placeholder .ph-icon{{width:56px;height:56px;border-radius:50%;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:24px}}
.view-placeholder .ph-title{{font-size:16px;font-weight:600;color:#1e2937}}
.view-placeholder .ph-text{{font-size:13px;color:#6b7280;max-width:360px;line-height:1.6}}
.header{{display:block;margin-bottom:8px}}
h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:#6b7280;font-size:13px}}

/* controls below subtitle */
.controls{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:12px 0 18px}}
.nav{{display:flex;align-items:center;gap:8px;background:#2563eb;padding:5px;border-radius:30px;box-shadow:0 2px 8px rgba(37,99,235,.25)}}
.nav button{{border:none;background:transparent;color:#dbeafe;font-size:13px;cursor:pointer;padding:7px 14px;border-radius:20px;transition:.15s}}
.nav button.active{{background:#fff;color:#2563eb;font-weight:600}}
.nav button:hover{{color:#fff}}
.nav button.active:hover{{color:#2563eb}}
.nav .arrow{{font-size:18px;line-height:1;padding:5px 10px}}
.picker-wrap{{position:relative}}
#btnPicker,#genBtnPicker,#attBtnPicker{{background:#fff;color:#2563eb;font-weight:600;padding:7px 14px;border-radius:20px;display:flex;align-items:center;gap:6px}}
#btnPicker::after,#genBtnPicker::after,#attBtnPicker::after{{content:"▾";font-size:10px}}
.day-range{{display:flex;align-items:center;gap:8px;background:#fff;padding:5px 10px 5px 12px;border-radius:24px;box-shadow:0 2px 8px rgba(37,99,235,.15);font-size:13px}}
.day-range .range-label{{color:#6b7280;font-size:12px;white-space:nowrap}}
.day-range input[type="date"]{{border:1px solid #e5e7eb;border-radius:8px;padding:5px 8px;font-size:13px;color:#111;background:#fff;font-family:inherit;outline:none}}
.day-range input[type="date"]:focus{{border-color:#2563eb}}
.day-range .range-sep{{color:#9ca3af}}
.day-range .range-quick{{color:#2563eb;cursor:pointer;font-size:12px;margin-left:4px;white-space:nowrap}}
.day-range .range-quick:hover{{text-decoration:underline}}
.dropdown{{position:absolute;top:calc(100% + 8px);right:0;background:#fff;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.15);max-height:360px;overflow:auto;min-width:160px;z-index:100}}
.dropdown.hidden{{display:none}}
.dropdown .item{{padding:9px 14px;font-size:13px;cursor:pointer;white-space:nowrap}}
.dropdown .item:hover{{background:#eff6ff}}
.dropdown .item.active{{background:#2563eb;color:#fff}}
.dropdown .group{{padding:8px 14px 4px;font-size:11px;color:#9ca3af;font-weight:600}}
.dropdown .item-region{{padding:6px 14px;font-size:12.5px;cursor:pointer}}
.dropdown .item-region:hover{{background:#eff6ff}}
#btnRegion,#genBtnRegion,#attBtnRegion{{background:#fff;color:#2563eb;font-weight:600;padding:7px 14px;border-radius:20px;display:flex;align-items:center;gap:6px;border:none;cursor:pointer;box-shadow:0 2px 8px rgba(37,99,235,.15)}}
#btnRegion::after,#genBtnRegion::after,#attBtnRegion::after{{content:"▾";font-size:10px}}
.region-dropdown{{width:1000px;max-height:620px;overflow:hidden;border-radius:12px;padding:0}}
.region-dropdown .rd-header{{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#2563eb;color:#fff;font-weight:600;font-size:14px}}
.region-dropdown .rd-header small{{font-weight:400;opacity:.85;font-size:12px}}
.region-dropdown .rd-body{{display:flex;gap:0;max-height:calc(620px - 44px);overflow:auto;padding:14px 16px}}
.region-dropdown .rd-col{{flex:1;min-width:0;display:flex;flex-direction:column;border-right:1px solid #eef0f3;padding:0 12px}}
.region-dropdown .rd-col:last-child{{border-right:none}}
.region-dropdown .rd-col-header{{display:flex;align-items:baseline;gap:8px;padding-bottom:10px;margin-bottom:8px;border-bottom:2px solid #e5e7eb}}
.region-dropdown .rd-col-title{{font-size:15px;font-weight:700;color:#111;cursor:pointer}}
.region-dropdown .rd-col-title:hover{{color:#2563eb}}
.region-dropdown .rd-col-tag{{font-size:11px;color:#9ca3af}}
.region-dropdown .rd-list{{display:flex;flex-direction:column;gap:12px}}
.region-dropdown .rd-region{{padding-bottom:10px;border-bottom:1px solid #f3f4f6}}
.region-dropdown .rd-region:last-child{{border-bottom:none}}
.region-dropdown .rd-region-title{{font-size:13px;font-weight:600;color:#111;cursor:pointer;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.region-dropdown .rd-region-title:hover{{color:#2563eb}}
.region-dropdown .rd-sub{{font-size:11px;color:#9ca3af;margin:4px 0 3px}}
.region-dropdown .rd-tags{{display:flex;flex-wrap:wrap;gap:5px}}
.region-dropdown .rd-tag{{font-size:11.5px;padding:3px 8px;border-radius:5px;cursor:pointer;white-space:nowrap}}
.region-dropdown .rd-tag-wh{{background:#eff6ff;color:#2563eb}}
.region-dropdown .rd-tag-wh:hover{{background:#dbeafe}}
.region-dropdown .rd-tag-grp{{background:#f3f4f6;color:#475569}}
.region-dropdown .rd-tag-grp:hover{{background:#e5e7eb;color:#111}}
.region-dropdown .rd-empty{{font-size:12px;color:#9ca3af;padding:6px 8px}}

.cards{{display:flex;gap:14px;margin-bottom:24px;flex-wrap:wrap}}
.section-tabs{{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;background:#fff;padding:8px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.section-tabs button{{border:none;background:transparent;color:#475569;font-size:13px;padding:8px 14px;border-radius:8px;cursor:pointer;transition:.15s}}
.section-tabs button:hover{{background:#f3f4f6;color:#111}}
.section-tabs button.active{{background:#2563eb;color:#fff;font-weight:600}}
.rp-grid{{display:flex;flex-direction:column;gap:10px}}
.rp-block{{border:1px solid #eef0f3;border-radius:10px;overflow:hidden;background:#fff}}
.rp-block-header{{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:#eff6ff;user-select:none}}
.rp-block-title{{font-weight:700;font-size:13px;color:#2563eb;cursor:pointer}}
.rp-block-title:hover{{text-decoration:underline}}
.rp-block-icon{{font-size:11px;color:#64748b;cursor:pointer}}
.rp-block-body{{padding:12px 14px;background:#fff}}
.rp-block-body.collapsed{{display:none}}
.rp-region-block{{margin-bottom:10px}}
.rp-region-block:last-child{{margin-bottom:0}}
.rp-region-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
.rp-region-title{{font-weight:600;font-size:12.5px;color:#374151;cursor:pointer;width:fit-content}}
.rp-region-title:hover{{color:#2563eb;text-decoration:underline}}
.rp-region-icon{{font-size:11px;color:#64748b;cursor:pointer;margin-left:6px}}
.rp-region-body.collapsed{{display:none}}
.rp-warehouses{{display:flex;flex-wrap:wrap;gap:5px}}
.rp-wh{{font-size:11.5px;color:#475569;padding:3px 8px;background:#f3f4f6;border-radius:5px;cursor:pointer;white-space:nowrap}}
.rp-wh:hover{{background:#dbeafe;color:#2563eb}}
.rp-major{{font-weight:700;font-size:13px;color:#2563eb;padding:6px 10px;background:#eff6ff;border-radius:8px;white-space:nowrap;display:inline-block;width:fit-content}}
.rp-regions{{display:flex;flex-wrap:wrap;gap:6px}}
.rp-region{{font-size:12px;color:#475569;padding:4px 10px;background:#f3f4f6;border-radius:6px;white-space:nowrap}}
.card{{flex:1;min-width:150px;background:#fff;border-radius:12px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card .v{{font-size:26px;font-weight:700}}
.card .l{{font-size:12px;color:#6b7280;margin-top:4px}}
.card.red .v{{color:#dc2626}}
.card.amber .v{{color:#d97706}}
.card.blue .v{{color:#2563eb}}

/* 单表结构：thead 内 th 使用 sticky；wrapper 用 clip-path 圆角，不裁剪 sticky */
.table-wrapper{{margin-bottom:26px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);clip-path:inset(0 round 12px);background:#fff}}
table{{width:100%;border-collapse:collapse;background:#fff}}
th,td{{padding:10px 12px;text-align:left;font-size:13px;border-bottom:1px solid #eef0f3;vertical-align:middle}}
th{{background:#f0f3f8;font-weight:600;color:#374151;position:-webkit-sticky;position:sticky;top:0;z-index:10}}
/* 五大板块表头冻结增强 */
#tableMajor thead th,#tableDetail thead th,#tableWh thead th,#tableGrp thead th,#tableTop thead th{{top:0}}
/* Top10 固定列宽，避免不同区域行混排导致列宽重算、视觉上错行 */
#tableTop{{table-layout:fixed}}
/* Top10 美化：全部居中对齐 + 均衡列宽 + 指标列高亮（补签率 正式工/劳务工共用 tableTop） */
#tableTop th,#tableTop td{{text-align:center}}
#tableTop th:nth-child(1),#tableTop td:nth-child(1){{width:5%}}
#tableTop th:nth-child(2),#tableTop td:nth-child(2){{width:11%}}
#tableTop th:nth-child(3),#tableTop td:nth-child(3){{width:12%}}
#tableTop th:nth-child(4),#tableTop td:nth-child(4){{width:14%}}
#tableTop th:nth-child(5),#tableTop td:nth-child(5){{width:14%}}
#tableTop th:nth-child(6),#tableTop td:nth-child(6){{width:15%}}
#tableTop th:nth-child(7),#tableTop td:nth-child(7){{width:11%}}
#tableTop th:nth-child(8),#tableTop td:nth-child(8){{width:9%}}
#tableTop th:nth-child(9),#tableTop td:nth-child(9){{width:9%}}
#tableTop .top-emp-row td{{white-space:nowrap!important;word-break:keep-all!important;overflow:hidden!important;text-overflow:ellipsis!important;font-variant-numeric:tabular-nums}}
#tableTop .top-emp-row td.num{{font-weight:600;color:#1d4ed8}}
#tableTop .top-emp-row td:nth-child(8),#tableTop .top-emp-row td:nth-child(9){{color:#475569;font-weight:400}}
#tableTop th:nth-child(7){{color:#1d4ed8}}
#tableTop tr.major-row-t td,#tableTop tr.region-row-t td{{text-align:left;padding-left:14px}}
#genTableTop{{table-layout:fixed}}
#genTableTop th:nth-child(1),#genTableTop td:nth-child(1){{width:40px}}
#genTableTop th:nth-child(2),#genTableTop td:nth-child(2){{width:16%}}
#genTableTop th:nth-child(3),#genTableTop td:nth-child(3){{width:13%}}
#genTableTop th:nth-child(4),#genTableTop td:nth-child(4){{width:13%}}
#genTableTop th:nth-child(5),#genTableTop td:nth-child(5){{width:13%}}
#genTableTop th:nth-child(6),#genTableTop td:nth-child(6){{width:13%}}
#genTableTop .top-emp-row td{{white-space:nowrap!important;word-break:keep-all!important;overflow:hidden!important;text-overflow:ellipsis!important}}
/* Top10 美化：全部居中对齐 + 均衡列宽 + 指标列高亮（正式工 genTableTop / 劳务工 tableAttTop） */
#genTableTop th,#genTableTop td,#tableAttTop th,#tableAttTop td{{text-align:center}}
#genTableTop th:nth-child(1),#genTableTop td:nth-child(1),#tableAttTop th:nth-child(1),#tableAttTop td:nth-child(1){{width:6%}}
#genTableTop th:nth-child(2),#genTableTop td:nth-child(2),#tableAttTop th:nth-child(2),#tableAttTop td:nth-child(2){{width:15%}}
#genTableTop th:nth-child(3),#genTableTop td:nth-child(3),#tableAttTop th:nth-child(3),#tableAttTop td:nth-child(3){{width:13%}}
#genTableTop th:nth-child(4),#genTableTop td:nth-child(4),#tableAttTop th:nth-child(4),#tableAttTop td:nth-child(4){{width:17%}}
#genTableTop th:nth-child(5),#genTableTop td:nth-child(5),#tableAttTop th:nth-child(5),#tableAttTop td:nth-child(5){{width:17%}}
#genTableTop th:nth-child(6),#genTableTop td:nth-child(6),#tableAttTop th:nth-child(6),#tableAttTop td:nth-child(6){{width:15%}}
#genTableTop th:nth-child(7),#genTableTop td:nth-child(7),#tableAttTop th:nth-child(7),#tableAttTop td:nth-child(7){{width:12%}}
#genTableTop td.num,#tableAttTop td.num{{text-align:center;font-weight:600;color:#1d4ed8;font-variant-numeric:tabular-nums}}
#genTableTop th:last-child,#tableAttTop th:last-child{{color:#1d4ed8}}
#genTableTop tr.major-row-gt td,#genTableTop tr.region-row-gt td,#tableAttTop tr.att-major td{{text-align:left;padding-left:14px}}
/* JS 兜底：克隆 thead 为 fixed，兼容 CSS sticky 不生效的环境 */
.sticky-header-clone{{position:fixed!important;top:0;display:none;z-index:10000!important;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.12);border-radius:0 0 10px 10px}}
.sticky-header-clone .clone-table{{width:100%;border-collapse:collapse;background:#f0f3f8;margin-bottom:0;box-shadow:none;border-radius:0}}
.sticky-header-clone .clone-table th{{padding:10px 12px;text-align:left;font-size:13px;border-bottom:1px solid #eef0f3;background:#f0f3f8;font-weight:600;color:#374151;position:static}}
td.num{{text-align:right;font-variant-numeric:tabular-nums}}
tr.grp{{background:#eef4fb;font-weight:700;cursor:pointer}}
tr.subgrp{{background:#f7fafc;font-weight:600;color:#334155;cursor:pointer}}
tr.grp:hover{{background:#e4edf8}}
tr.subgrp:hover{{background:#eef3f8}}
td.indent{{padding-left:30px;color:#475569}}
td.indent2{{padding-left:54px;color:#64748b}}
.fold-icon{{display:inline-block;width:14px;font-size:11px;color:#64748b}}
.hidden{{display:none}}
.bar{{background:#eef0f3;border-radius:6px;height:14px;width:120px;overflow:hidden}}
.bar-fill{{display:block;height:100%;background:linear-gradient(90deg,#2563eb,#60a5fa);border-radius:6px}}
.bar>span{{display:block;height:100%;background:linear-gradient(90deg,#2563eb,#60a5fa);border-radius:6px;min-width:2px}}
caption{{caption-side:top;text-align:left;font-weight:700;font-size:15px;padding:14px 12px 8px;color:#111}}
/* 说明板块：信息卡片 + 分区 + 图标列表 */
.note{{background:linear-gradient(180deg,#f8fbff 0%,#f0f6ff 100%);border-radius:14px;padding:18px 20px;font-size:12.5px;color:#475569;box-shadow:0 1px 3px rgba(37,99,235,.08);border:1px solid #dbeafe}}
.note-header{{display:flex;align-items:center;gap:8px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #bfdbfe;cursor:pointer;user-select:none}}
.note-icon{{width:22px;height:22px;border-radius:50%;background:#2563eb;color:#fff;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.note-title{{font-size:14px;font-weight:700;color:#1e40af;letter-spacing:.2px}}
.note-fold{{margin-left:auto;font-size:12px;color:#64748b;transition:transform .2s ease;flex-shrink:0}}
.note-header.collapsed{{margin-bottom:0;padding-bottom:0;border-bottom:none}}
.note-header.collapsed .note-fold{{transform:rotate(-90deg)}}
.note-body.collapsed{{display:none}}
.note-body{{display:flex;flex-direction:column;gap:14px;overflow:hidden;transition:max-height .25s ease;max-height:2000px}}
.note-body.collapsed{{display:none}}
.note-section{{display:flex;flex-direction:column;gap:6px}}
.note-label{{display:inline-flex;align-items:center;gap:5px;width:fit-content;font-size:11px;font-weight:600;color:#2563eb;background:#fff;border:1px solid #bfdbfe;border-radius:6px;padding:3px 8px;margin-bottom:2px}}
.note-label::before{{content:'';width:5px;height:5px;border-radius:50%;background:#2563eb}}
.note-list{{margin:0;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:5px}}
.note-list li{{position:relative;padding-left:16px;line-height:1.6}}
.note-list li::before{{content:'';position:absolute;left:4px;top:8px;width:5px;height:5px;border-radius:50%;background:#93c5fd}}
.note-list li strong{{color:#1f2937;font-weight:600}}
.note-list li code{{font-family:inherit;font-size:11.5px;color:#2563eb;background:#eff6ff;padding:1px 5px;border-radius:4px;border:1px solid #dbeafe}}
.note-divider{{height:1px;background:linear-gradient(90deg,transparent,#bfdbfe,transparent);margin:2px 0}}
.empty{{color:#9ca3af;font-style:italic}}
.indent3{{padding-left:78px;color:#7c8694}}
.emp-subrow td{{background:#fafcff;padding:0}}
.emp-table{{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0}}
.emp-table thead th,.emp-table tbody th{{background:#eef4fb;font-weight:600;color:#475569;padding:6px 10px;border-bottom:1px solid #e3e8f0;position:static}}
.emp-table td{{padding:5px 10px;border-bottom:1px solid #f0f3f8;color:#334155}}
.emp-count{{font-size:11px;color:#94a3b8;margin-left:6px}}
</style></head><body><div class="wrap">
<div class="top-nav">
  <div class="top-nav-left">
    <div class="top-nav-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg></div>
    <div class="top-nav-title">
      <strong>FBU 交付前台 · 考勤</strong>
      <small>考勤确认及时率 / 补签 · 全球三大区</small>
    </div>
  </div>
  <div class="top-nav-tabs">
    <button id="secAtt" class="active" onclick="showCell(curWt, 'att')">考勤确认及时率</button>
    <button id="secSign" onclick="showCell(curWt, 'sign')">补签率</button>
    <span class="nav-sep"></span>
    <button id="wtFormal" class="active" onclick="showCell('formal', curSec)">正式工</button>
    <button id="wtLabor" onclick="showCell('labor', curSec)">劳务工</button>
  </div>
</div>

<div class="controls" id="globalControls" style="margin:0 0 16px">
<div class="nav">
<button id="btnDay">按天</button>
<button id="btnWeek">按周</button>
<button id="btnMonth" class="active">按月</button>
<button id="btnPrev" class="arrow">‹</button>
<div class="picker-wrap" id="periodPickerWrap">
<button id="btnPicker">2026年7月</button>
<div id="dropdown" class="dropdown hidden"></div>
</div>
<button id="btnNext" class="arrow">›</button>
</div>
<div class="picker-wrap">
<button id="btnRegion">FBU交付前台</button>
<div id="regionDropdown" class="dropdown region-dropdown hidden">
<div class="rp-grid" id="rpGrid"></div>
</div>
</div>
</div>

<div class="view-panel" id="viewFormal">
<div class="header">
<h1>补签率统计</h1>
<div class="sub" id="hdrSub">维度：三级部门（大区）× 四级部门（区域）　|　口径：审批状态 = 已完成 + 审批中</div>
</div>

<div class="section-tabs" id="sectionTabs">
<button data-target="secMajor" class="active">大区汇总</button>
<button data-target="secDetail">区域明细</button>
<button data-target="secWh">仓明细</button>
<button data-target="secGrp">组明细</button>
<button data-target="secTop">Top10 员工</button>
</div>

<div class="cards">
<div class="card"><div class="v" id="cTotal">0</div><div class="l" id="cTotalL">补签合计（条）</div></div>
<div class="card red"><div class="v" id="cDone">0</div><div class="l" id="cDoneL">已完成</div></div>
<div class="card amber"><div class="v" id="cIng">0</div><div class="l" id="cIngL">审批中</div></div>
<div class="card blue"><div class="v" id="cMajors">0</div><div class="l">大区数</div></div>
</div>

<div class="table-section" id="secMajor">
<div class="section-caption">一、大区（三级部门）汇总</div>
<div class="table-wrapper">
<table id="tableMajor"><thead><tr><th>大区</th><th>补签合计</th><th>已完成</th><th>审批中</th><th>占总体比</th><th class='rate-col'>补签率</th><th>占比图例</th></tr></thead><tbody id="majorBody"></tbody></table>
</div>
</div>

<div class="table-section" id="secDetail">
<div class="section-caption">二、大区 × 区域（三级部门 × 四级部门）明细</div>
<div class="table-wrapper">
<table id="tableDetail"><thead><tr><th>区域（四级部门）</th><th>补签合计</th><th>已完成</th><th>审批中</th><th>占大区比</th><th class='rate-col'>补签率</th><th>占比图例</th></tr></thead><tbody id="detailBody"></tbody></table>
</div>
</div>

<div class="table-section" id="secWh">
<div class="section-caption">三、大区 × 区域 × 仓（三级部门 × 四级部门 × 五级部门）补签占比</div>
<div class="table-wrapper">
<table id="tableWh"><thead><tr><th>仓（五级部门）</th><th>补签合计</th><th>已完成</th><th>审批中</th><th>占区域比</th><th class='rate-col'>补签率</th><th>占比图例</th></tr></thead><tbody id="whBody"></tbody></table>
</div>
</div>

<div class="table-section" id="secGrp">
<div class="section-caption">四、大区 × 区域 × 仓 × 组（三级部门 × 四级部门 × 五级部门 × 六级部门）补签占比　<small style="font-weight:400;color:#64748b">点击组可展开组内员工</small></div>
<div class="table-wrapper">
<table id="tableGrp"><thead><tr><th>组（六级部门）</th><th>补签合计</th><th>已完成</th><th>审批中</th><th>占仓比</th><th class='rate-col'>补签率</th><th>占比图例</th></tr></thead><tbody id="grpBody"></tbody></table>
</div>
</div>

<div class="table-section" id="secTop">
<div class="section-caption" id="secTopCap">五、各区补签 Top10 员工（按区域内员工补签数排序，含已完成+审批中）　<small style="font-weight:400;color:#64748b">点击大区/区域可展开或收起 Top 员工</small></div>
<div class="table-wrapper">
<table id="tableTop"><thead><tr><th>排名</th><th>姓名</th><th>工号</th><th id="thTopZhiwei">职位</th><th>主属仓</th><th>主属组</th><th>补签数</th><th>已完成</th><th id="thTopIng">审批中</th></tr></thead><tbody id="topBody"></tbody></table>
</div>
</div>

<div class="note">
  <div class="note-header" id="noteHeader" onclick="toggleNote()">
    <div class="note-icon">i</div>
    <div class="note-title">数据说明</div>
    <div class="note-fold" id="noteFold">▾</div>
  </div>
  <div class="note-body">
    <div class="note-section">
      <div class="note-label">数据来源</div>
      <ul class="note-list">
        <li>合并 <code>补签流程-6月.xlsx</code> 与 <code>补签流程-7月.xlsx</code>，按自然键去重，无重复计数。</li>
        <li>已排除审批状态为 <strong>已驳回 / 已废弃 / 已撤回</strong> 的记录。</li>
        <li>补签合计 = 补签申请记录条数（源表一行一条）。</li>
      </ul>
    </div>
    <div class="note-section">
      <div class="note-label">交互方式</div>
      <ul class="note-list">
        <li>点击右上角 <strong>「按天 / 按周 / 按月」</strong>，可切换按天、按周、按月查看对应时间范围的补签分布。</li>
      </ul>
    </div>
    <div class="note-section">
      <div class="note-label">口径定义</div>
      <ul class="note-list">
        <li><strong>大区</strong> = 三级部门，<strong>区域</strong> = 四级部门；加拿大区已归入美洲区（数据中三级部门=美洲区、四级部门=加拿大区）。</li>
        <li>已剔除大区：海外销售部、FBU财务部、渠道管理部。</li>
        <li>职位从 2026-08-24 花名册按工号匹配，未匹配到显示为 <strong>—</strong>。</li>
      </ul>
    </div>
    <div class="note-divider"></div>
    <div class="note-section">
      <div class="note-label">第四板块 · 大区×区域×仓×组</div>
      <ul class="note-list">
        <li>下钻到 <strong>组（六级部门）</strong>，点击任意组行可展开该组下员工明细：姓名、工号、职位、补签日期、班次、补签点、补签事由、备注、审批状态。</li>
        <li>空组显示为 <strong>部门直属</strong>。</li>
      </ul>
    </div>
    <div class="note-section">
      <div class="note-label">第五板块 · 各区补签 Top10 员工</div>
      <ul class="note-list">
        <li>按区域聚合员工补签数，各区取前 10 名（含已完成+审批中），附带职位、主属仓、主属组。</li>
        <li><strong>主属仓 / 主属组</strong>：该员工在该区域下补签次数最多的仓/组；并列时按名称字母序取第一个。</li>
        <li>Top10 补签数已剔除 <strong>补签事由=入职当天</strong>，以及备注明确为客观情况无法打卡的记录（无打卡机/考勤机、机器故障、系统问题、闸机故障、消防、无工牌工卡、司机在外跑业务、西班牙语入职 Nuevo ingreso 等）。</li>
      </ul>
    </div>
  </div>
</div>
</div>

</div>
</div>

<div class="wrap">
<div class="view-panel" id="viewGen" style="display:none">
<div class="header">
<h1 id="genTitle">考勤确认及时率（正式工）</h1>
<div class="sub" id="genSub"></div>
</div>
<div class="section-tabs" id="genSectionTabs">
<button data-target="genSecMajor" class="active">大区汇总</button>
<button data-target="genSecDetail">区域明细</button>
<button data-target="genSecWh">仓明细</button>
<button data-target="genSecGrp">组明细</button>
<button data-target="genSecTop">Top10 员工</button>
</div>
<div class="cards" id="genCards"></div>
<div class="table-section" id="genSecMajor"><div class="section-caption">一、大区（三级部门）汇总</div><div class="table-wrapper"><table id="genTableMajor"><thead><tr id="genMajorHead"></tr></thead><tbody id="genMajorBody"></tbody></table></div></div>
<div class="table-section" id="genSecDetail"><div class="section-caption">二、大区 × 区域（三级部门 × 四级部门）明细</div><div class="table-wrapper"><table id="genTableDetail"><thead><tr id="genDetailHead"></tr></thead><tbody id="genDetailBody"></tbody></table></div></div>
<div class="table-section" id="genSecWh"><div class="section-caption">三、大区 × 区域 × 仓（三级部门 × 四级部门 × 五级部门）明细</div><div class="table-wrapper"><table id="genTableWh"><thead><tr id="genWhHead"></tr></thead><tbody id="genWhBody"></tbody></table></div></div>
<div class="table-section" id="genSecGrp"><div class="section-caption">四、大区 × 区域 × 仓 × 组（三级部门 × 四级部门 × 五级部门 × 六级部门）明细　<small style="font-weight:400;color:#64748b">点击大区 / 区域 / 仓组头可折叠或展开下级明细</small></div><div class="table-wrapper"><table id="genTableGrp"><thead><tr id="genGrpHead"></tr></thead><tbody id="genGrpBody"></tbody></table></div></div>
<div class="table-section" id="genSecTop"><div class="section-caption" id="genSecTopCap">五、各区 Top10 员工</div><div class="table-wrapper"><table id="genTableTop"><thead><tr id="genTopHead"></tr></thead><tbody id="genTopBody"></tbody></table></div></div>
<div class="note"><div class="note-header" data-notebody="genNoteBody" onclick="toggleNoteById(this)"><div class="note-icon">i</div><div class="note-title">数据说明</div><div class="note-fold">▾</div></div><div class="note-body" id="genNoteBody"></div></div>
</div>

<script>
const formalPayload = {json_data};
const laborPayload = {labor_json};
const formalAttPayload = {formal_att_json};
let payload = formalPayload;
let genPayload = null;
let formalNoteHtml = '';
let months = payload.months;
let days = payload.days;
let data = payload.data;
let C = 6;
const WEEKDAYS = {weekdays};

let mode = 'month'; // 'day' | 'week' | 'month'
let selected = months[months.length - 1];
let daySel = days.length ? days[days.length - 1] : '';
let weekSel = '';

function fmt(n) {{ return Number(n).toLocaleString(); }}
function parseDate(ymd) {{ return new Date(ymd + 'T00:00:00'); }}
function constrainDay(d) {{
  if (!d || days.includes(d)) return d || days[0];
  for (let i = days.length - 1; i >= 0; i--) {{ if (days[i] <= d) return days[i]; }}
  return days[0];
}}
function monthLabel(m) {{ const [y, mo] = m.split('-'); return y + '年' + parseInt(mo, 10) + '月'; }}
function dayLabel(d, withYear=false) {{
  const dt = parseDate(d);
  const [y, mo, da] = d.split('-');
  return (withYear ? y + '年' : '') + parseInt(mo, 10) + '月' + parseInt(da, 10) + '日 ' + WEEKDAYS[dt.getDay()];
}}
function addDaysStr(d, n) {{ const dt = parseDate(d); dt.setDate(dt.getDate() + n); const y = dt.getFullYear(), m = dt.getMonth() + 1, da = dt.getDate(); return y + '-' + (m < 10 ? '0' + m : m) + '-' + (da < 10 ? '0' + da : da); }}
function weekStartOf(d) {{ const dt = parseDate(d); const wd = dt.getDay(); const diff = (wd === 0 ? -6 : 1 - wd); dt.setDate(dt.getDate() + diff); const y = dt.getFullYear(), m = dt.getMonth() + 1, da = dt.getDate(); return y + '-' + (m < 10 ? '0' + m : m) + '-' + (da < 10 ? '0' + da : da); }}
function weeksOf(daysArr) {{ const seen = {{}}; daysArr.forEach(d => {{ seen[weekStartOf(d)] = true; }}); return Object.keys(seen).sort().map(s => [s, addDaysStr(s, 6)]); }}
function weekLabel(start, end) {{ return dayLabel(start, true) + ' ~ ' + dayLabel(end, true); }}
function aggRange(start, end) {{
  const rangeDays = days.filter(d => d >= start && d <= end);
  if (!rangeDays.length) return {{ total: 0, done: 0, ing: 0, major: [], detail: [], warehouse: [], group: [], rateTotal: 0, ydkTotal: 0, ybqTotal: 0 }};
  const majorMap = {{}}, detailMap = {{}}, whMap = {{}}, grpMap = {{}};
  let total = 0, done = 0, ing = 0, ydkTotal = 0, ybqTotal = 0;
  rangeDays.forEach(d => {{
    const day = data[d];
    if (!day) return;
    total += day.total || 0; done += day.done || 0; ing += day.ing || 0;
    ydkTotal += day.ydkTotal || 0; ybqTotal += day.ybqTotal || 0;
    (day.major || []).forEach(r => {{
      if (!majorMap[r.name]) majorMap[r.name] = {{ name: r.name, '已完成': 0, '审批中': 0, total: 0, ydk: 0, ybq: 0, __order: Object.keys(majorMap).length }};
      majorMap[r.name]['已完成'] += r['已完成'] || 0;
      majorMap[r.name]['审批中'] += r['审批中'] || 0;
      majorMap[r.name].total += r.total || 0;
      majorMap[r.name].ydk += r.ydk || 0; majorMap[r.name].ybq += r.ybq || 0;
    }});
    (day.detail || []).forEach(r => {{
      const k = r.major + '|' + r.region;
      if (!detailMap[k]) detailMap[k] = {{ major: r.major, region: r.region, '已完成': 0, '审批中': 0, total: 0, ydk: 0, ybq: 0, __order: Object.keys(detailMap).length }};
      detailMap[k]['已完成'] += r['已完成'] || 0;
      detailMap[k]['审批中'] += r['审批中'] || 0;
      detailMap[k].total += r.total || 0;
      detailMap[k].ydk += r.ydk || 0; detailMap[k].ybq += r.ybq || 0;
    }});
    (day.warehouse || []).forEach(r => {{
      const k = r.major + '|' + r.region + '|' + r.wh;
      if (!whMap[k]) whMap[k] = {{ major: r.major, region: r.region, wh: r.wh, '已完成': 0, '审批中': 0, total: 0, ydk: 0, ybq: 0, __order: Object.keys(whMap).length }};
      whMap[k]['已完成'] += r['已完成'] || 0;
      whMap[k]['审批中'] += r['审批中'] || 0;
      whMap[k].total += r.total || 0;
      whMap[k].ydk += r.ydk || 0; whMap[k].ybq += r.ybq || 0;
    }});
    (day.group || []).forEach(r => {{
      const k = r.major + '|' + r.region + '|' + r.wh + '|' + r.group;
      if (!grpMap[k]) grpMap[k] = {{ major: r.major, region: r.region, wh: r.wh, group: r.group, '已完成': 0, '审批中': 0, total: 0, ydk: 0, ybq: 0, __order: Object.keys(grpMap).length }};
      grpMap[k]['已完成'] += r['已完成'] || 0;
      grpMap[k]['审批中'] += r['审批中'] || 0;
      grpMap[k].total += r.total || 0;
      grpMap[k].ydk += r.ydk || 0; grpMap[k].ybq += r.ybq || 0;
    }});
  }});
  const majorArr = Object.values(majorMap).sort((a, b) => a.__order - b.__order);
  majorArr.forEach(r => {{ r.pct = total ? parseFloat((r.total / total * 100).toFixed(1)) : 0; r.rate = r.ydk ? parseFloat((r.ybq / r.ydk * 100).toFixed(1)) : null; }});
  const majorTot = {{}}; majorArr.forEach(r => majorTot[r.name] = r.total);
  const detailArr = Object.values(detailMap).sort((a, b) => a.__order - b.__order);
  detailArr.forEach(r => {{ r.pctMajor = majorTot[r.major] ? parseFloat((r.total / majorTot[r.major] * 100).toFixed(1)) : 0; r.rate = r.ydk ? parseFloat((r.ybq / r.ydk * 100).toFixed(1)) : null; }});
  const regionTot = {{}}; detailArr.forEach(r => regionTot[r.major + '|' + r.region] = r.total);
  const whArr = Object.values(whMap).sort((a, b) => a.__order - b.__order);
  whArr.forEach(r => {{ r.pctRegion = regionTot[r.major + '|' + r.region] ? parseFloat((r.total / regionTot[r.major + '|' + r.region] * 100).toFixed(1)) : 0; r.rate = r.ydk ? parseFloat((r.ybq / r.ydk * 100).toFixed(1)) : null; }});
  const whTot = {{}}; whArr.forEach(r => whTot[r.major + '|' + r.region + '|' + r.wh] = r.total);
  const grpArr = Object.values(grpMap).sort((a, b) => a.__order - b.__order);
  grpArr.forEach(r => {{ r.pctWh = whTot[r.major + '|' + r.region + '|' + r.wh] ? parseFloat((r.total / whTot[r.major + '|' + r.region + '|' + r.wh] * 100).toFixed(1)) : 0; r.rate = r.ydk ? parseFloat((r.ybq / r.ydk * 100).toFixed(1)) : null; }});
  return {{ total, done, ing, major: majorArr, detail: detailArr, warehouse: whArr, group: grpArr, rateTotal: ydkTotal ? parseFloat((ybqTotal / ydkTotal * 100).toFixed(1)) : null, ydkTotal, ybqTotal }};
}}
function currentData() {{ if (mode === 'day') return aggRange(daySel, daySel); if (mode === 'week') return aggRange(weekSel, addDaysStr(weekSel, 6)); return data[selected] || {{ total: 0, done: 0, ing: 0, major: [], detail: [], warehouse: [], group: [] }}; }}
function dateInRange(ymd) {{ if (mode === 'month') return ymd.startsWith(selected); if (mode === 'week') return ymd >= weekSel && ymd <= addDaysStr(weekSel, 6); return ymd === daySel; }}
function monthInRange(ym) {{ if (mode === 'month') return ym === selected; if (mode === 'week') {{ var ws = weekSel.slice(0,7), we = addDaysStr(weekSel, 6).slice(0,7); return ym >= ws && ym <= we; }} return ym === daySel.slice(0,7); }}

function setMode(m) {{
  mode = m;
  document.getElementById('btnDay').classList.toggle('active', mode === 'day');
  document.getElementById('btnWeek').classList.toggle('active', mode === 'week');
  document.getElementById('btnMonth').classList.toggle('active', mode === 'month');
  if (!days.length) {{ render(); return; }}
  if (mode === 'day') {{
    if (!daySel || !days.includes(daySel)) daySel = days[days.length - 1];
  }} else if (mode === 'week') {{
    var wk = weeksOf(days);
    if (!weekSel || !wk.some(function(w){{ return w[0] === weekSel; }})) weekSel = wk.length ? wk[wk.length - 1][0] : '';
  }} else {{
    if (!selected || !months.includes(selected)) selected = months[months.length - 1];
  }}
  render();
}}

function step(delta) {{
  if (mode === 'month') {{
    const list = months;
    let idx = list.indexOf(selected);
    if (idx === -1) {{ selected = list[list.length - 1]; }}
    else {{
      idx = Math.max(0, Math.min(list.length - 1, idx + delta));
      selected = list[idx];
    }}
  }} else if (mode === 'week') {{
    var wk = weeksOf(days);
    let idx = wk.findIndex(function(w){{ return w[0] === weekSel; }});
    if (idx === -1) weekSel = wk.length ? wk[wk.length - 1][0] : '';
    else {{ idx = Math.max(0, Math.min(wk.length - 1, idx + delta)); weekSel = wk[idx][0]; }}
  }} else {{
    let idx = days.indexOf(daySel);
    if (idx === -1) daySel = days[days.length - 1];
    else {{ idx = Math.max(0, Math.min(days.length - 1, idx + delta)); daySel = days[idx]; }}
  }}
  render();
}}

function renderPicker() {{
  const btn = document.getElementById('btnPicker');
  if (mode === 'day') btn.textContent = dayLabel(daySel, true);
  else if (mode === 'week') btn.textContent = weekLabel(weekSel, addDaysStr(weekSel, 6));
  else btn.textContent = monthLabel(selected);
  const dd = document.getElementById('dropdown');
  dd.innerHTML = '';
  if (mode === 'day') {{
    const grouped = {{}};
    days.forEach(d => {{ const m = d.slice(0, 7); (grouped[m] = grouped[m] || []).push(d); }});
    months.forEach(m => {{
      if (!grouped[m]) return;
      const g = document.createElement('div'); g.className = 'group'; g.textContent = monthLabel(m); dd.appendChild(g);
      grouped[m].forEach(d => {{
        const el = document.createElement('div');
        el.className = 'item' + (d === daySel ? ' active' : '');
        el.textContent = dayLabel(d);
        el.onclick = () => {{ daySel = d; render(); closeDropdown(); }};
        dd.appendChild(el);
      }});
    }});
  }} else if (mode === 'week') {{
    const wk = weeksOf(days);
    wk.forEach(w => {{
      const el = document.createElement('div');
      el.className = 'item' + (w[0] === weekSel ? ' active' : '');
      el.textContent = weekLabel(w[0], w[1]);
      el.onclick = () => {{ weekSel = w[0]; render(); closeDropdown(); }};
      dd.appendChild(el);
    }});
  }} else {{
    months.forEach(m => {{
      const el = document.createElement('div');
      el.className = 'item' + (m === selected ? ' active' : '');
      el.textContent = monthLabel(m);
      el.onclick = () => {{ selected = m; render(); closeDropdown(); }};
      dd.appendChild(el);
    }});
  }}
}}

function render() {{
  renderPicker();
  const d = currentData();
  const showRate = payload.type === 'labor';
  const showYdk = payload.type === 'labor';
  C = (showRate ? 1 : 0) + (showYdk ? 1 : 0) + 6;
  const ingLabel = payload.type === 'labor' ? '未完成' : '审批中';
  const rateCell = (r) => showRate ? `<td class='num rate'>${{r.rate != null ? r.rate + '%' : '—'}}</td>` : '';
  const rateTh = showRate ? "<th class='rate-col'>补签率</th>" : '';
  const ydkCell = (r) => showYdk ? `<td class='num ydk'>${{r.ydk != null ? fmt(r.ydk) : '—'}}</td>` : '';
  const ydkTh = showYdk ? "<th>应打卡合计</th>" : '';
  document.querySelector('#tableMajor thead tr').innerHTML = `<th>大区</th>${{ydkTh}}<th>补签合计</th><th>已完成</th><th>${{ingLabel}}</th><th>占总体比</th>${{rateTh}}<th>占比图例</th>`;
  document.querySelector('#tableDetail thead tr').innerHTML = `<th>区域（四级部门）</th>${{ydkTh}}<th>补签合计</th><th>已完成</th><th>${{ingLabel}}</th><th>占大区比</th>${{rateTh}}<th>占比图例</th>`;
  document.querySelector('#tableWh thead tr').innerHTML = `<th>仓（五级部门）</th>${{ydkTh}}<th>补签合计</th><th>已完成</th><th>${{ingLabel}}</th><th>占区域比</th>${{rateTh}}<th>占比图例</th>`;
  document.querySelector('#tableGrp thead tr').innerHTML = `<th>组（六级部门）</th>${{ydkTh}}<th>补签合计</th><th>已完成</th><th>${{ingLabel}}</th><th>占仓比</th>${{rateTh}}<th>占比图例</th>`;
  const thTopIng = document.getElementById('thTopIng');
  if (thTopIng) thTopIng.textContent = ingLabel;
  const thTopZhiwei = document.getElementById('thTopZhiwei');
  if (thTopZhiwei) thTopZhiwei.textContent = payload.type === 'labor' ? '工种' : '职位';
  document.getElementById('cTotal').textContent = fmt(d.total);
  document.getElementById('cDone').textContent = fmt(d.done);
  document.getElementById('cIng').textContent = fmt(d.ing);
  document.getElementById('cMajors').textContent = d.major.length;

  const mb = document.getElementById('majorBody');
  if (!d.total) {{
    mb.innerHTML = `<tr><td colspan='${{C}}' class='empty'>该时间范围无数据</td></tr>`;
  }} else {{
    mb.innerHTML = d.major.map(r => {{
      const bar = `<div class='bar'><span style='width:${{r.pct}}%'></span></div>`;
      return `<tr data-major="${{attrEsc(r.name)}}"><td>${{esc(r.name)}}</td>${{ydkCell(r)}}<td class='num'>${{fmt(r.total)}}</td><td class='num'>${{r['已完成']}}</td><td class='num'>${{r['审批中']}}</td><td class='num'>${{r.pct}}%</td>${{rateCell(r)}}<td>${{bar}}</td></tr>`;
    }}).join('');
  }}

  const db = document.getElementById('detailBody');
  if (!d.total) {{
    db.innerHTML = `<tr><td colspan='${{C}}' class='empty'>该时间范围无数据</td></tr>`;
  }} else {{
    let cur = null, html = '';
    d.detail.forEach(r => {{
      if (r.major !== cur) {{
        cur = r.major;
        const mt = d.major.find(x => x.name === cur).total;
        html += `<tr class='grp major-row2' data-major="${{cur}}" data-expanded="true" onclick="toggleMajor2(this)"><td colspan='${{C}}'><span class='fold-icon'>▾</span> ${{cur}}（大区合计 ${{fmt(mt)}}）</td></tr>`;
      }}
      const bar = `<div class='bar'><span style='width:${{r.pctMajor}}%'></span></div>`;
      html += `<tr class='region-row2' data-major="${{attrEsc(cur)}}" data-region="${{attrEsc(r.region)}}"><td class='indent'>${{esc(r.region)}}</td>${{ydkCell(r)}}<td class='num'>${{fmt(r.total)}}</td><td class='num'>${{r['已完成']}}</td><td class='num'>${{r['审批中']}}</td><td class='num'>${{r.pctMajor}}%</td>${{rateCell(r)}}<td>${{bar}}</td></tr>`;
    }});
    db.innerHTML = html;
  }}

  renderRegionPanel();

  const wb = document.getElementById('whBody');
  if (!d.warehouse || !d.warehouse.length) {{
    wb.innerHTML = `<tr><td colspan='${{C}}' class='empty'>该时间范围无仓明细数据</td></tr>`;
  }} else {{
    let curMajor = null, curRegion = null, html = '';
    d.warehouse.forEach(r => {{
      if (r.major !== curMajor) {{
        curMajor = r.major;
        curRegion = null;
        const mt = d.major.find(x => x.name === curMajor).total;
        html += `<tr class='grp major-row' data-major="${{curMajor}}" data-expanded="true" onclick="toggleMajor(this)"><td colspan='${{C}}'><span class='fold-icon'>▾</span> ${{curMajor}}（大区合计 ${{fmt(mt)}}）</td></tr>`;
      }}
      if (r.region !== curRegion) {{
        curRegion = r.region;
        const rt = (d.detail.find(x => x.major === curMajor && x.region === curRegion) || {{}}).total || 0;
        html += `<tr class='subgrp region-row' data-major="${{curMajor}}" data-region="${{curRegion}}" data-expanded="true" onclick="toggleRegion(this)"><td colspan='${{C}}'><span class='fold-icon'>▾</span> ${{curRegion}}（区域合计 ${{fmt(rt)}}）</td></tr>`;
      }}
      const bar = `<div class='bar'><span style='width:${{r.pctRegion}}%'></span></div>`;
      html += `<tr class='wh-row' data-major="${{curMajor}}" data-region="${{curRegion}}"><td class='indent2'>${{r.wh}}</td>${{ydkCell(r)}}<td class='num'>${{fmt(r.total)}}</td><td class='num'>${{r['已完成']}}</td><td class='num'>${{r['审批中']}}</td><td class='num'>${{r.pctRegion}}%</td>${{rateCell(r)}}<td>${{bar}}</td></tr>`;
    }});
    wb.innerHTML = html;
  }}

  if (payload.type === 'labor') {{
    empIndex = payload.empIndex || {{}};
    topEmpIndex = payload.topEmpIndex || {{}};
  }} else {{
    buildEmpIndex();
    buildTopEmp();
  }}

  const gb = document.getElementById('grpBody');
  if (!d.group || !d.group.length) {{
    gb.innerHTML = `<tr><td colspan='${{C}}' class='empty'>该时间范围无组明细数据</td></tr>`;
  }} else {{
    let curMajor = null, curRegion = null, curWh = null, html = '';
    d.group.forEach(r => {{
      if (r.major !== curMajor) {{
        curMajor = r.major; curRegion = null; curWh = null;
        const mt = d.major.find(x => x.name === curMajor).total;
        html += `<tr class='grp major-row-g' data-major="${{curMajor}}" data-expanded="true" onclick="toggleMajorG(this)"><td colspan='${{C}}'><span class='fold-icon'>▾</span> ${{curMajor}}（大区合计 ${{fmt(mt)}}）</td></tr>`;
      }}
      if (r.region !== curRegion) {{
        curRegion = r.region; curWh = null;
        const rt = (d.detail.find(x => x.major === curMajor && x.region === curRegion) || {{}}).total || 0;
        html += `<tr class='subgrp region-row-g' data-major="${{curMajor}}" data-region="${{curRegion}}" data-expanded="true" onclick="toggleRegionG(this)"><td colspan='${{C}}'><span class='fold-icon'>▾</span> ${{curRegion}}（区域合计 ${{fmt(rt)}}）</td></tr>`;
      }}
      if (r.wh !== curWh) {{
        curWh = r.wh;
        const wt = (d.warehouse.find(x => x.major === curMajor && x.region === curRegion && x.wh === curWh) || {{}}).total || 0;
        html += `<tr class='subgrp3 wh-row-g' data-major="${{curMajor}}" data-region="${{curRegion}}" data-wh="${{curWh}}" data-expanded="true" onclick="toggleWhG(this)"><td colspan='${{C}}'><span class='fold-icon'>▾</span> ${{curWh}}（仓合计 ${{fmt(wt)}}）</td></tr>`;
      }}
      const bar = `<div class='bar'><span style='width:${{r.pctWh}}%'></span></div>`;
      html += `<tr class='group-row' data-major="${{attrEsc(curMajor)}}" data-region="${{attrEsc(curRegion)}}" data-wh="${{attrEsc(curWh)}}" data-group="${{attrEsc(r.group)}}" data-expanded="false" onclick="toggleEmp(this)"><td class='indent3'><span class='fold-icon'>▸</span> ${{esc(r.group)}} <span class='emp-count'>（点击展开员工）</span></td>${{ydkCell(r)}}<td class='num'>${{fmt(r.total)}}</td><td class='num'>${{r['已完成']}}</td><td class='num'>${{r['审批中']}}</td><td class='num'>${{r.pctWh}}%</td>${{rateCell(r)}}<td>${{bar}}</td></tr>`;
    }});
    gb.innerHTML = html;
  }}

  const tb = document.getElementById('topBody');
  if (!d.total) {{
    tb.innerHTML = "<tr><td colspan='9' class='empty'>该时间范围无数据</td></tr>";
  }} else {{
    let curMajor = null, html = '';
    d.detail.forEach(r => {{
      if (r.major !== curMajor) {{
        curMajor = r.major;
        html += `<tr class='grp major-row-t' data-major="${{attrEsc(curMajor)}}" data-expanded="true" onclick="toggleMajorT(this)"><td colspan='9'><span class='fold-icon'>▾</span> ${{esc(curMajor)}}</td></tr>`;
      }}
      const rk = r.major + '|' + r.region;
      const emps = topEmpIndex[rk] || [];
      html += `<tr class='subgrp region-row-t' data-major="${{attrEsc(curMajor)}}" data-region="${{attrEsc(r.region)}}" data-expanded="true" onclick="toggleRegionT(this)"><td colspan='9'><span class='fold-icon'>▾</span> ${{r.region}}（区域合计 ${{fmt(r.total)}}）<span class='emp-count'>　Top ${{emps.length}} 员工</span></td></tr>`;
      emps.forEach((e, i) => {{
        const zg = payload.type === 'labor' ? (e.gongzhong || '—') : (e.zhiwei || '—');
        html += `<tr class='top-emp-row' data-major="${{attrEsc(curMajor)}}" data-region="${{attrEsc(r.region)}}"><td class='num'>${{i+1}}</td><td>${{esc(e.name)}}</td><td>${{esc(e.gong)}}</td><td style="white-space:nowrap">${{esc(zg)}}</td><td style="white-space:nowrap">${{esc(e.wh)}}</td><td style="white-space:nowrap">${{esc(e.group)}}</td><td class='num'>${{fmt(e.count)}}</td><td class='num'>${{e.done}}</td><td class='num'>${{e.ing}}</td></tr>`;
      }});
      if (!emps.length) {{
        html += `<tr class='top-emp-row' data-major="${{attrEsc(curMajor)}}" data-region="${{attrEsc(r.region)}}"><td class='indent2 empty' colspan='9'>该区域无补签次数大于3次的员工</td></tr>`;
      }}
    }});
    tb.innerHTML = html;
  }}
  setupStickyHeaders();
}}

function updateIcon(row) {{
  const icon = row.querySelector('.fold-icon');
  if (icon) icon.textContent = row.dataset.expanded === 'true' ? '▾' : '▸';
}}
function setRegionState(major, region, collapsed) {{
  const row = document.querySelector(`#whBody tr.region-row[data-major="${{major}}"][data-region="${{region}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#whBody tr.wh-row[data-major="${{major}}"][data-region="${{region}}"]`).forEach(w => w.classList.toggle('hidden', collapsed));
}}
function setMajorState(major, collapsed) {{
  const row = document.querySelector(`#whBody tr.major-row[data-major="${{major}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#whBody tr.region-row[data-major="${{major}}"]`).forEach(r => r.classList.toggle('hidden', collapsed));
  if (collapsed) {{
    document.querySelectorAll(`#whBody tr.wh-row[data-major="${{major}}"]`).forEach(w => w.classList.add('hidden'));
  }} else {{
    document.querySelectorAll(`#whBody tr.region-row[data-major="${{major}}"]`).forEach(r => {{
      const regCollapsed = r.dataset.expanded === 'false';
      document.querySelectorAll(`#whBody tr.wh-row[data-major="${{major}}"][data-region="${{r.dataset.region}}"]`).forEach(w => w.classList.toggle('hidden', regCollapsed));
    }});
  }}
}}
function toggleMajor(row) {{ setMajorState(row.dataset.major, row.dataset.expanded !== 'false'); }}
function toggleRegion(row) {{ setRegionState(row.dataset.major, row.dataset.region, row.dataset.expanded !== 'false'); }}

function setMajorState2(major, collapsed) {{
  const row = document.querySelector(`#detailBody tr.major-row2[data-major="${{major}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#detailBody tr.region-row2[data-major="${{major}}"]`).forEach(r => r.classList.toggle('hidden', collapsed));
}}
function toggleMajor2(row) {{ setMajorState2(row.dataset.major, row.dataset.expanded !== 'false'); }}

function whSortKey(w) {{
  if (w === '部门直属') return [-2, ''];
  const m = /^\\D*(\\d+)/.exec(String(w));
  if (m) return [parseInt(m[1], 10), ''];
  // 无数字职能部门按固定顺序排在数字仓之后
  if (w.includes('行政')) return [100000, '行政'];
  if (w.includes('渠道')) return [100001, '渠道'];
  if (w.includes('卡派')) return [100002, '卡派'];
  if (w.includes('管培')) return [100003, '管培'];
  return [100004, String(w)];
}}
function sortWarehouses(whs) {{
  return Array.from(new Set(whs)).sort((a, b) => {{
    const ka = whSortKey(a), kb = whSortKey(b);
    if (ka[0] !== kb[0]) return ka[0] - kb[0];
    return ka[1].localeCompare(kb[1]);
  }});
}}
function renderRegionPanel() {{
  const d = currentData();
  const grid = document.getElementById('rpGrid');
  if (!d.total) {{ grid.innerHTML = '<div class="rd-empty">该时间范围无数据</div>'; return; }}
  // build major -> regions map (detail is already sorted)
  const regMap = {{}};
  (d.detail || []).forEach(r => {{
    if (!regMap[r.major]) regMap[r.major] = new Set();
    regMap[r.major].add(r.region);
  }});
  // build region -> warehouses map
  const whMap = {{}};
  (d.warehouse || []).forEach(r => {{
    const key = r.major + '|' + r.region;
    if (!whMap[key]) whMap[key] = [];
    whMap[key].push(r.wh);
  }});
  // build region -> groups map (de-duplicate by wh+group)
  const grpMap = {{}};
  (d.group || []).forEach(r => {{
    const key = r.major + '|' + r.region;
    if (!grpMap[key]) grpMap[key] = [];
    const exists = grpMap[key].some(g => g.wh === r.wh && g.group === r.group);
    if (!exists) grpMap[key].push({{wh: r.wh, group: r.group}});
  }});
  const order = ['美洲区','欧洲区','亚太区','FBU HRBP Dept.'];
  let html = '<div class="rd-header">FBU 交付前台 <small>全球大区总览</small></div>';
  html += '<div class="rd-body">';
  order.forEach(major => {{
    const regs = Array.from(regMap[major] || []);
    html += `<div class="rd-col">`;
    html += `<div class="rd-col-header"><div class="rd-col-title" data-major="${{attrEsc(major)}}" onclick="goMajor(this)">${{esc(major)}}</div><div class="rd-col-tag">大区</div></div>`;
    html += `<div class="rd-list">`;
    if (regs.length) {{
      regs.forEach(r => {{
        html += `<div class="rd-region">`;
        html += `<div class="rd-region-title" data-major="${{attrEsc(major)}}" data-region="${{attrEsc(r)}}" onclick="goRegion2(this)">${{esc(r)}}</div>`;
        html += `</div>`;
      }});
    }} else {{
      html += `<div class="rd-empty">无区域数据</div>`;
    }}
    html += `</div></div>`;
  }});
  html += '</div>';
  grid.innerHTML = html;
}}
function esc(s) {{
  if (s == null) return '';
  if (typeof s !== 'string') s = String(s);
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}
function attrEsc(s) {{
  // data-* 属性专用：只转义引号与尖括号，不包 HTML
  if (s == null) return '';
  if (typeof s !== 'string') s = String(s);
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}
function closeRegionDropdown() {{ document.getElementById('regionDropdown').classList.add('hidden'); }}
function toggleRegionDropdown() {{ document.getElementById('regionDropdown').classList.toggle('hidden'); }}
function toggleRegionBlock(e, icon) {{
  if (e) e.stopPropagation();
  const header = icon.closest('.rp-block-header');
  const body = header.nextElementSibling;
  body.classList.toggle('collapsed');
  icon.textContent = body.classList.contains('collapsed') ? '▸' : '▾';
}}
function toggleRegionSubBlock(e, icon) {{
  if (e) e.stopPropagation();
  const body = icon.closest('.rp-region-block').querySelector('.rp-region-body');
  body.classList.toggle('collapsed');
  icon.textContent = body.classList.contains('collapsed') ? '▸' : '▾';
}}
function goWarehouse(el) {{
  const major = el.dataset.major;
  const region = el.dataset.region;
  const wh = el.dataset.wh;
  // expand major in warehouse table
  const mrow = document.querySelector(`#whBody tr.major-row[data-major="${{major}}"]`);
  if (mrow && mrow.dataset.expanded === 'false') toggleMajor(mrow);
  const rrow = document.querySelector(`#whBody tr.region-row[data-major="${{major}}"][data-region="${{region}}"]`);
  if (rrow && rrow.dataset.expanded === 'false') toggleRegion(rrow);
  const rows = document.querySelectorAll(`#whBody tr.wh-row[data-major="${{major}}"][data-region="${{region}}"]`);
  for (const row of rows) {{
    if (row.cells[0].textContent.trim() === wh) {{
      row.scrollIntoView({{ behavior:'smooth', block:'center' }});
      row.style.background = '#dbeafe';
      setTimeout(() => row.style.background = '', 1200);
      break;
    }}
  }}
}}
function goGroup(el) {{
  const major = el.dataset.major;
  const region = el.dataset.region;
  const wh = el.dataset.wh;
  const group = el.dataset.group;
  document.getElementById('secGrp').scrollIntoView({{ behavior:'smooth', block:'start' }});
  setMajorStateG(major, false);
  setRegionStateG(major, region, false);
  setWhStateG(major, region, wh, false);
  const rows = document.querySelectorAll(`#grpBody tr.group-row[data-major="${{major}}"][data-region="${{region}}"][data-wh="${{wh}}"]`);
  for (const row of rows) {{
    if (row.dataset.group === group) {{
      row.scrollIntoView({{ behavior:'smooth', block:'center' }});
      row.style.background = '#dbeafe';
      setTimeout(() => row.style.background = '', 1200);
      break;
    }}
  }}
}}

function goMajor(el) {{
  const major = el.dataset.major;
  const row = document.querySelector(`#majorBody tr[data-major="${{major}}"]`);
  if (row) {{
    row.scrollIntoView({{ behavior:'smooth', block:'center' }});
    row.style.background = '#dbeafe';
    setTimeout(() => row.style.background = '', 1200);
  }}
}}
function goRegion2(el) {{
  const major = el.dataset.major;
  const region = el.dataset.region;
  const mrow = document.querySelector(`#detailBody tr.major-row2[data-major="${{major}}"]`);
  if (mrow && mrow.dataset.expanded === 'false') toggleMajor2(mrow);
  const row = document.querySelector(`#detailBody tr.region-row2[data-major="${{major}}"][data-region="${{region}}"]`);
  if (row) {{
    row.scrollIntoView({{ behavior:'smooth', block:'center' }});
    row.style.background = '#dbeafe';
    setTimeout(() => row.style.background = '', 1200);
  }}
}}

let empIndex = {{}};
function buildEmpIndex() {{
  empIndex = {{}};
  const list = (payload.allEmp) || [];
  list.forEach(e => {{
    const ek = (mode === 'month') ? e.ym : e.ymd;
    if (mode === 'month' ? ek !== selected : !dateInRange(ek)) return;
    const k = e.major + '|' + e.region + '|' + e.wh + '|' + e.group;
    if (!empIndex[k]) empIndex[k] = [];
    empIndex[k].push(e);
  }});
}}
let topEmpIndex = {{}};
function buildTopEmp() {{
  topEmpIndex = {{}};
  const list = payload.allEmp || [];
  const cnt = {{}};
  list.forEach(e => {{
    const ek = (mode === 'month') ? e.ym : e.ymd;
    if (mode === 'month' ? ek !== selected : !dateInRange(ek)) return;
    if (e.top_exclude) return;  // 剔除：补签事由=入职当天，或 备注因客观情况无法打卡
    const rk = e.major + '|' + e.region;
    if (!cnt[rk]) cnt[rk] = {{}};
    const gid = e['工号'] || ('__name__' + (e['姓名'] || ''));
    if (!cnt[rk][gid]) cnt[rk][gid] = {{ count:0, done:0, ing:0, name:e['姓名']||'', gong:e['工号']||'', zhiwei:e['职位']||'—', whCount:{{}}, groupCount:{{}} }};
    const o = cnt[rk][gid];
    const w = e.weight || 1;
    o.count += w;
    if (e['审批状态'] === '已完成') o.done += w; else if (e['审批状态'] === '审批中') o.ing += w;
    const wh = e.wh || '部门直属';
    const gp = e.group || '部门直属';
    o.whCount[wh] = (o.whCount[wh] || 0) + w;
    o.groupCount[gp] = (o.groupCount[gp] || 0) + w;
  }});
  function pickMax(obj) {{
    let best = '', bestCnt = -1;
    for (const k in obj) {{
      if (obj[k] > bestCnt || (obj[k] === bestCnt && k.localeCompare(best) < 0)) {{ best = k; bestCnt = obj[k]; }}
    }}
    return best;
  }}
  for (const rk in cnt) {{
    const arr = Object.values(cnt[rk]).map(o => ({{
      count: o.count, done: o.done, ing: o.ing, name: o.name, gong: o.gong,
      zhiwei: o.zhiwei, wh: pickMax(o.whCount), group: pickMax(o.groupCount)
    }})).filter(o => o.count > 3).sort((a, b) => b.count - a.count || (a.name||'').localeCompare(b.name||''));
    topEmpIndex[rk] = arr.slice(0, 10);
  }}
}}
function setWhStateG(major, region, wh, collapsed) {{
  const row = document.querySelector(`#grpBody tr.wh-row-g[data-major="${{major}}"][data-region="${{region}}"][data-wh="${{wh}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#grpBody tr.group-row[data-major="${{major}}"][data-region="${{region}}"][data-wh="${{wh}}"]`).forEach(w => {{
    w.classList.toggle('hidden', collapsed);
    if (collapsed) collapseEmp(w);
  }});
}}
function setRegionStateG(major, region, collapsed) {{
  const row = document.querySelector(`#grpBody tr.region-row-g[data-major="${{major}}"][data-region="${{region}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#grpBody tr.wh-row-g[data-major="${{major}}"][data-region="${{region}}"]`).forEach(r => {{
    r.classList.toggle('hidden', collapsed);
    if (collapsed) setWhStateG(major, region, r.dataset.wh, true);
    else setWhStateG(major, region, r.dataset.wh, r.dataset.expanded === 'false');
  }});
}}
function setMajorStateG(major, collapsed) {{
  const row = document.querySelector(`#grpBody tr.major-row-g[data-major="${{major}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#grpBody tr.region-row-g[data-major="${{major}}"]`).forEach(r => {{
    r.classList.toggle('hidden', collapsed);
    if (collapsed) setRegionStateG(major, r.dataset.region, true);
    else setRegionStateG(major, r.dataset.region, r.dataset.expanded === 'false');
  }});
}}
function toggleMajorG(row) {{ setMajorStateG(row.dataset.major, row.dataset.expanded !== 'false'); }}
function toggleRegionG(row) {{ setRegionStateG(row.dataset.major, row.dataset.region, row.dataset.expanded !== 'false'); }}
function toggleWhG(row) {{ setWhStateG(row.dataset.major, row.dataset.region, row.dataset.wh, row.dataset.expanded !== 'false'); }}
function setMajorStateT(major, collapsed) {{
  const row = document.querySelector(`#topBody tr.major-row-t[data-major="${{major}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#topBody tr.region-row-t[data-major="${{major}}"]`).forEach(r => {{
    r.classList.toggle('hidden', collapsed);
    if (collapsed) setRegionStateT(major, r.dataset.region, true);
    else setRegionStateT(major, r.dataset.region, r.dataset.expanded === 'false');
  }});
}}
function setRegionStateT(major, region, collapsed) {{
  const row = document.querySelector(`#topBody tr.region-row-t[data-major="${{major}}"][data-region="${{region}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#topBody tr.top-emp-row[data-major="${{major}}"][data-region="${{region}}"]`).forEach(w => w.classList.toggle('hidden', collapsed));
}}
function toggleMajorT(row) {{ setMajorStateT(row.dataset.major, row.dataset.expanded !== 'false'); }}
function toggleRegionT(row) {{ setRegionStateT(row.dataset.major, row.dataset.region, row.dataset.expanded !== 'false'); }}
function toggleEmp(row) {{
  const major = row.dataset.major, region = row.dataset.region, wh = row.dataset.wh, group = row.dataset.group;
  const k = major + '|' + region + '|' + wh + '|' + group;
  if (row.dataset.expanded === 'true') {{
    collapseEmp(row);
  }} else {{
    const emps = empIndex[k] || [];
    const empHeaders = payload.empHeaders || ['姓名','工号','工种','考勤日期','班次','首打卡补签时间','末打卡补签时间'];
    const unit = payload.type === 'labor' ? '条' : '人';
    const total = (payload.empCount && payload.empCount[k] != null) ? payload.empCount[k] : emps.length;
    let rows;
    if (emps.length) {{
      const isArr = Array.isArray(emps[0]);
      const thead = '<tr>' + empHeaders.map(h => `<th>${{esc(h)}}</th>`).join('') + '</tr>';
      const body = emps.map(e => {{
        if (isArr) return '<tr>' + e.map(v => `<td>${{esc(v || '')}}</td>`).join('') + '</tr>';
        const keys = payload.empKeys || empHeaders;
        return '<tr>' + keys.map(kk => `<td>${{esc(e[kk] || '')}}</td>`).join('') + '</tr>';
      }}).join('');
      rows = `<tr class='emp-subrow'><td colspan='${{C}}'><table class='emp-table'><thead>${{thead}}</thead><tbody>${{body}}</tbody></table></td></tr>`;
    }} else {{
      rows = `<tr class='emp-subrow'><td colspan='${{C}}' class='empty'>该组无员工明细</td></tr>`;
    }}
    row.insertAdjacentHTML('afterend', rows);
    row.dataset.expanded = 'true';
    const fi = row.querySelector('.fold-icon'); if (fi) fi.textContent = '▾';
    const ec = row.querySelector('.emp-count'); if (ec) ec.textContent = `（点击收起，共 ${{total}} ${{unit}}${{total > emps.length ? '，显示前 ' + emps.length + ' 条' : ''}}）`;
  }}
}}
function collapseEmp(row) {{
  if (row.dataset.expanded !== 'true') return;
  let nxt = row.nextElementSibling;
  while (nxt && nxt.classList.contains('emp-subrow')) {{
    const t = nxt; nxt = nxt.nextElementSibling; t.remove();
  }}
  row.dataset.expanded = 'false';
  const fi = row.querySelector('.fold-icon'); if (fi) fi.textContent = '▸';
  const ec = row.querySelector('.emp-count'); if (ec) ec.textContent = '（点击展开员工）';
}}

function closeDropdown() {{ document.getElementById('dropdown').classList.add('hidden'); }}
function toggleDropdown() {{ document.getElementById('dropdown').classList.toggle('hidden'); }}

// section tabs navigation
const sectionTabs = document.getElementById('sectionTabs');
const tabButtons = sectionTabs ? Array.from(sectionTabs.querySelectorAll('button')) : [];
const sectionIds = ['secMajor','secDetail','secWh','secGrp','secTop'];
function scrollToSection(id) {{
  const el = document.getElementById(id);
  if (!el) return;
  const headerOffset = 90;
  const top = el.getBoundingClientRect().top + window.pageYOffset - headerOffset;
  window.scrollTo({{ top, behavior: 'smooth' }});
  tabButtons.forEach(b => b.classList.toggle('active', b.dataset.target === id));
}}
function updateActiveTab() {{
  if (!sectionTabs) return;
  const headerOffset = 100;
  let activeId = sectionIds[0];
  for (const id of sectionIds) {{
    const el = document.getElementById(id);
    if (!el) continue;
    if (el.getBoundingClientRect().top <= headerOffset) activeId = id;
  }}
  tabButtons.forEach(b => b.classList.toggle('active', b.dataset.target === activeId));
}}
sectionTabs.addEventListener('click', e => {{
  const b = e.target.closest('button');
  if (!b) return;
  scrollToSection(b.dataset.target);
}});
window.addEventListener('scroll', updateActiveTab, {{ passive: true }});

// 通用板块（考勤确认及时性）Tab 导航
const genSectionTabs = document.getElementById('genSectionTabs');
const genTabButtons = genSectionTabs ? Array.from(genSectionTabs.querySelectorAll('button')) : [];
const genSectionIds = ['genSecMajor','genSecDetail','genSecWh','genSecGrp','genSecTop'];
function scrollToGenSection(id) {{
  const el = document.getElementById(id);
  if (!el) return;
  const headerOffset = 90;
  const top = el.getBoundingClientRect().top + window.pageYOffset - headerOffset;
  window.scrollTo({{ top, behavior: 'smooth' }});
  genTabButtons.forEach(b => b.classList.toggle('active', b.dataset.target === id));
}}
function updateActiveGenTab() {{
  if (!genSectionTabs) return;
  const headerOffset = 100;
  let activeId = genSectionIds[0];
  for (const id of genSectionIds) {{
    const el = document.getElementById(id);
    if (!el) continue;
    if (el.getBoundingClientRect().top <= headerOffset) activeId = id;
  }}
  genTabButtons.forEach(b => b.classList.toggle('active', b.dataset.target === activeId));
}}
if (genSectionTabs) {{
  genSectionTabs.addEventListener('click', e => {{
    const b = e.target.closest('button');
    if (!b) return;
    scrollToGenSection(b.dataset.target);
  }});
}}
window.addEventListener('scroll', updateActiveGenTab, {{ passive: true }});


// ===== 全局控件（顶栏唯一一套）：按当前激活视图分发 =====
function curViewKey(){{
  if (curSec === 'sign') return 'sign';
  return (curWt === 'labor') ? 'attend' : 'gen';
}}
function syncModeBtns(m){{
  ['btnDay','btnWeek','btnMonth'].forEach(function(id, i){{
    var el = document.getElementById(id);
    if (el) el.classList.toggle('active', m === ['day','week','month'][i]);
  }});
}}
function dispatchMode(m){{
  var v = curViewKey();
  if (v === 'sign') setMode(m);
  else if (v === 'gen') setModeGen(m);
  else setModeAttend(m);
}}
function dispatchStep(dir){{
  var v = curViewKey();
  if (v === 'sign') step(dir);
  else if (v === 'gen') stepGen(dir);
  else stepAttend(dir);
}}
function dispatchPicker(e){{
  e.stopPropagation(); closeRegionDropdown(); closeGenDropdown();
  var v = curViewKey();
  if (v === 'sign') toggleDropdown();
  else if (v === 'gen') toggleGenDropdownShared();
  else toggleAttendDropdownShared();
}}
function dispatchRegion(e){{
  e.stopPropagation(); closeDropdown(); closeGenDropdown();
  var v = curViewKey();
  if (v === 'sign') toggleRegionDropdown();
  else if (v === 'gen') toggleGenRegionShared();
  else toggleAttendRegionDropdown();
}}
document.getElementById('btnDay').onclick = () => dispatchMode('day');
document.getElementById('btnWeek').onclick = () => dispatchMode('week');
document.getElementById('btnMonth').onclick = () => dispatchMode('month');
document.getElementById('btnPrev').onclick = () => dispatchStep(-1);
document.getElementById('btnNext').onclick = () => dispatchStep(1);
document.getElementById('btnPicker').onclick = dispatchPicker;
document.getElementById('dropdown').onclick = (e) => e.stopPropagation();
document.getElementById('btnRegion').onclick = dispatchRegion;
document.getElementById('regionDropdown').onclick = (e) => e.stopPropagation();
document.addEventListener('click', () => {{ closeDropdown(); closeRegionDropdown(); closeGenDropdown(); closeGenRegionDropdown(); }});

// JS 兜底：克隆单表 thead 并 fixed 定位，兼容 CSS sticky 不生效的环境
const stickyHeaderClones = [];
function destroyStickyHeaders() {{
  stickyHeaderClones.forEach(o => {{ if (o.wrap) o.wrap.remove(); }});
  stickyHeaderClones.length = 0;
}}
function syncCloneWidths(table, cloneTable) {{
  const origThs = table.querySelectorAll('thead th');
  const cloneThs = cloneTable.querySelectorAll('thead th');
  origThs.forEach((th, i) => {{
    if (cloneThs[i]) {{
      const w = th.getBoundingClientRect().width + 'px';
      cloneThs[i].style.width = w;
      cloneThs[i].style.minWidth = w;
      cloneThs[i].style.maxWidth = w;
    }}
  }});
}}
function toggleNote() {{
  const h = document.getElementById('noteHeader');
  const b = document.querySelector('.note-body');
  if (!h || !b) return;
  const collapsed = h.classList.toggle('collapsed');
  b.classList.toggle('collapsed', collapsed);
}}
function toggleNoteById(h) {{
  var b = document.getElementById(h.getAttribute('data-notebody'));
  if (!b) return;
  var collapsed = h.classList.toggle('collapsed');
  b.classList.toggle('collapsed', collapsed);
}}
function roIdx(order, major, region) {{ var lst = (order || {{}})[major] || []; var i = lst.indexOf(region); return i < 0 ? 9999 : i; }}
function cmpRegionOrd(order, major, a, b) {{ var d = roIdx(order, major, a) - roIdx(order, major, b); return d !== 0 ? d : (a < b ? -1 : a > b ? 1 : 0); }}
function applyNote() {{
  const b = document.querySelector('.note-body');
  if (!b) return;
  if (payload.type === 'labor') {{ b.innerHTML = payload.noteHtml || ''; }}
  else if (formalNoteHtml) {{ b.innerHTML = formalNoteHtml; }}
}}
let genCurrentAgg = null;
function renderGenRegionPanel() {{
  const A = genCurrentAgg;
  const grid = document.getElementById('rpGrid');
  if (!grid) return;
  if (!A || !A.total) {{ grid.innerHTML = '<div class="rd-empty">该时间范围无数据</div>'; return; }}
  const regMap = {{}};
  (A.detail || []).forEach(r => {{ if (!regMap[r.major]) regMap[r.major] = new Set(); regMap[r.major].add(r.region); }});
  const order = ['美洲区','欧洲区','亚太区','FBU HRBP Dept.'];
  const roPanel = (typeof formalAttPayload !== 'undefined' && formalAttPayload.regionOrder) || {{}};
  let html = '<div class="rd-header">FBU 交付前台 <small>全球大区总览</small></div>';
  html += '<div class="rd-body">';
  order.forEach(major => {{
    const regs = Array.from(regMap[major] || []).sort(function(a,b){{ return cmpRegionOrd(roPanel, major, a, b); }});
    html += `<div class="rd-col">`;
    html += `<div class="rd-col-header"><div class="rd-col-title" data-major="${{attrEsc(major)}}" onclick="goGenMajor(this)">${{esc(major)}}</div><div class="rd-col-tag">大区</div></div>`;
    html += `<div class="rd-list">`;
    if (regs.length) {{
      regs.forEach(r => {{ html += `<div class="rd-region"><div class="rd-region-title" data-major="${{attrEsc(major)}}" data-region="${{attrEsc(r)}}" onclick="goGenRegion(this)">${{esc(r)}}</div></div>`; }});
    }} else {{
      html += `<div class="rd-empty">无区域数据</div>`;
    }}
    html += `</div></div>`;
  }});
  html += '</div>';
  grid.innerHTML = html;
}}
function goGenMajor(el) {{
  const major = el.dataset.major;
  const row = document.querySelector(`#genMajorBody tr.att-major[data-major="${{cssEsc(major)}}"]`);
  if (row) {{ row.scrollIntoView({{ behavior:'smooth', block:'center' }}); row.style.background = '#dbeafe'; setTimeout(() => row.style.background = '', 1200); }}
  closeGenRegionDropdown();
}}
function goGenRegion(el) {{
  const major = el.dataset.major;
  const region = el.dataset.region;
  const row = document.querySelector(`#genDetailBody tr.att-region[data-major="${{cssEsc(major)}}"][data-region="${{cssEsc(region)}}"]`);
  if (row) {{ row.scrollIntoView({{ behavior:'smooth', block:'center' }}); row.style.background = '#dbeafe'; setTimeout(() => row.style.background = '', 1200); }}
  closeGenRegionDropdown();
}}
function closeGenDropdown() {{ const d = document.getElementById('genDropdown'); if (d) d.classList.add('hidden'); }}
function closeGenRegionDropdown() {{ const d = document.getElementById('regionDropdown'); if (d) d.classList.add('hidden'); }}
function toggleGenRegionShared() {{
  var dd = document.getElementById('regionDropdown');
  if (!dd) return;
  if (!dd.classList.contains('hidden')) {{ dd.classList.add('hidden'); return; }}
  renderGenRegionPanel();
  dd.classList.remove('hidden');
}}

function setGenMajorStateT(major, collapsed) {{
  const row = document.querySelector(`#genTopBody tr.major-row-gt[data-major="${{cssEsc(major)}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#genTopBody tr.region-row-gt[data-major="${{cssEsc(major)}}"]`).forEach(r => {{
    r.classList.toggle('hidden', collapsed);
    if (collapsed) setGenRegionStateT(major, r.dataset.region, true);
    else setGenRegionStateT(major, r.dataset.region, r.dataset.expanded === 'false');
  }});
}}
function setGenRegionStateT(major, region, collapsed) {{
  const row = document.querySelector(`#genTopBody tr.region-row-gt[data-major="${{cssEsc(major)}}"][data-region="${{cssEsc(region)}}"]`);
  if (!row) return;
  row.dataset.expanded = collapsed ? 'false' : 'true';
  updateIcon(row);
  document.querySelectorAll(`#genTopBody tr.top-emp-row[data-major="${{cssEsc(major)}}"][data-region="${{cssEsc(region)}}"]`).forEach(w => w.classList.toggle('hidden', collapsed));
}}
function toggleGenMajorT(row) {{ setGenMajorStateT(row.dataset.major, row.dataset.expanded !== 'false'); }}
function toggleGenRegionT(row) {{ setGenRegionStateT(row.dataset.major, row.dataset.region, row.dataset.expanded !== 'false'); }}

function renderGenTop10(P) {{
  const tb = document.getElementById('genTopBody');
  const head = document.getElementById('genTopHead');
  const cap = document.getElementById('genSecTopCap');
  if (cap) cap.innerHTML = P.topCaption || '五、各区 Top10 员工';
  if (!tb) return;
  if (!P.topEmpIndex) {{ tb.innerHTML = `<tr><td colspan="7" class="empty">暂无员工排名数据</td></tr>`; if (head) head.innerHTML = '<th>排名</th><th>姓名</th><th>工号</th><th>职位</th><th>主属仓</th><th>主属组</th><th>指标</th>'; return; }}
  const metricKey = P.topMetric || 'val';
  const metricLabel = P.topMetricLabel || '指标';
  if (head) head.innerHTML = '<th>排名</th><th>姓名</th><th>工号</th><th>职位</th><th>主属仓</th><th>主属组</th><th>' + esc(metricLabel) + '</th>';
  const order = P.majorOrder || [];
  const keys = Object.keys(P.topEmpIndex).sort(function(a, b){{
    const [ma, ra] = a.split('|'); const [mb, rb] = b.split('|');
    const oa = order.indexOf(ma), ob = order.indexOf(mb);
    if (oa !== ob) return (oa < 0 ? 99 : oa) - (ob < 0 ? 99 : ob);
    return ra.localeCompare(rb);
  }});
  let html = '', curMajor = null, curRegion = null;
  keys.forEach(function(k){{
    const [major, region] = k.split('|');
    const emps = P.topEmpIndex[k];
    if (!emps || !emps.length) return;
    if (major !== curMajor) {{ curMajor = major; curRegion = null; html += `<tr class="grp major-row-gt" data-major="${{attrEsc(major)}}" data-expanded="true" onclick="toggleGenMajorT(this)"><td colspan="7"><span class="fold-icon">▾</span> ${{esc(major)}}</td></tr>`; }}
    if (region !== curRegion) {{ curRegion = region; html += `<tr class="subgrp region-row-gt" data-major="${{attrEsc(major)}}" data-region="${{attrEsc(region)}}" data-expanded="true" onclick="toggleGenRegionT(this)"><td colspan="7"><span class="fold-icon">▾</span> ${{esc(region)}}（Top ${{emps.length}} 员工）</td></tr>`; }}
    emps.forEach(function(e, i){{
      html += `<tr class="top-emp-row" data-major="${{attrEsc(major)}}" data-region="${{attrEsc(region)}}"><td class="num">${{i+1}}</td><td>${{esc(e.name || '')}}</td><td>${{esc(e.gong || '')}}</td><td style="white-space:nowrap">${{esc(e.pos || '—')}}</td><td>${{esc(e.wh || '—')}}</td><td>${{esc(e.group || '—')}}</td><td class="num">${{fmt(e[metricKey] || 0)}}</td></tr>`;
    }});
  }});
  tb.innerHTML = html || `<tr><td colspan="7" class="empty">该时间范围无数据</td></tr>`;
}}

var genEmpIdx = {{}};
function buildGenEmpIndex() {{
  genEmpIdx = {{}};
  var idx = formalAttPayload.empIndex || {{}};
  Object.keys(idx).forEach(function(k) {{
    idx[k].forEach(function(e) {{
      var ym = e[e.length - 2], ymd = e[e.length - 1];
      var inRange;
      if (genMode === 'month') inRange = (ym === genSel);
      else if (genMode === 'week') inRange = (ymd >= genWeekSel && ymd <= addDaysStr(genWeekSel, 6));
      else inRange = (ymd >= (genDayStart || '') && ymd <= (genDayEnd || ''));
      if (!inRange) return;
      if (!genEmpIdx[k]) genEmpIdx[k] = [];
      genEmpIdx[k].push(e);
    }});
  }});
}}
function toggleGenEmp(row) {{
  var P = formalAttPayload;
  var k = row.dataset.major + '|' + row.dataset.region + '|' + row.dataset.wh + '|' + row.dataset.group;
  if (row.dataset.expanded === 'true') {{ collapseGenEmp(row); return; }}
  var emps = genEmpIdx[k] || [];
  var heads = P.empHeaders || [];
  var colspan = P.cols.length + 2;
  var html;
  if (emps.length) {{
    var thead = '<tr>' + heads.map(function(h) {{ return '<th>' + esc(h) + '</th>'; }}).join('') + '</tr>';
    var body = emps.map(function(e) {{
      return '<tr>' + e.slice(0, heads.length).map(function(v) {{ return '<td>' + esc(v == null ? '' : v) + '</td>'; }}).join('') + '</tr>';
    }}).join('');
    html = '<tr class="emp-subrow"><td colspan="' + colspan + '"><table class="emp-table"><thead>' + thead + '</thead><tbody>' + body + '</tbody></table></td></tr>';
  }} else {{
    html = '<tr class="emp-subrow"><td colspan="' + colspan + '" class="empty">该时间范围内该组无未及时确认记录</td></tr>';
  }}
  row.insertAdjacentHTML('afterend', html);
  row.dataset.expanded = 'true';
  var fi = row.querySelector('.fold-icon'); if (fi) fi.textContent = '▾';
  var ec = row.querySelector('.emp-count');
  if (ec) ec.textContent = emps.length ? '（点击收起，当前范围 ' + emps.length + ' 条）' : '（未及时确认 0 条，点击展开）';
}}
function collapseGenEmp(row) {{
  if (row.dataset.expanded !== 'true') return;
  var nxt = row.nextElementSibling;
  while (nxt && nxt.classList.contains('emp-subrow')) {{ var t = nxt; nxt = nxt.nextElementSibling; t.remove(); }}
  row.dataset.expanded = 'false';
  var fi = row.querySelector('.fold-icon'); if (fi) fi.textContent = '▸';
  var k = row.dataset.major + '|' + row.dataset.region + '|' + row.dataset.wh + '|' + row.dataset.group;
  var cnt = (genEmpIdx[k] || []).length;
  var ec = row.querySelector('.emp-count');
  if (ec) ec.textContent = '（未及时确认 ' + cnt + ' 条，点击展开）';
}}
function renderGen(P) {{
  var titleEl = document.getElementById('genTitle'); if (titleEl) titleEl.textContent = P.title || '';
  var subEl = document.getElementById('genSub'); if (subEl) subEl.textContent = P.subtitle || '';
  var nb = document.getElementById('genNoteBody'); if (nb) nb.innerHTML = P.noteHtml || '';
  var barLabel = (P.type === 'formalAtt') ? '及时确认率图例' : '占比图例';
  function genHead(first){{ var h = '<th>' + first + '</th>'; P.cols.forEach(function(c){{ h += '<th>' + c.label + '</th>'; }}); return h + '<th>' + barLabel + '</th>'; }}
  var ghm1 = document.getElementById('genMajorHead'); if (ghm1) ghm1.innerHTML = genHead('大区');
  var ghm2 = document.getElementById('genDetailHead'); if (ghm2) ghm2.innerHTML = genHead('区域（四级部门）');
  var ghm3 = document.getElementById('genWhHead'); if (ghm3) ghm3.innerHTML = genHead('仓（五级部门）');
  var ghm4 = document.getElementById('genGrpHead'); if (ghm4) ghm4.innerHTML = genHead('组（六级部门）');
  if (genMode === 'month') {{ if (!genSel) genSel = P.months[P.months.length - 1]; }}
  else if (genMode === 'week') {{ if (!genWeekSel) genWeekSel = (weeksOf(P.days)[weeksOf(P.days).length - 1] || [''])[0]; }}
  else {{ if (!genDayStart) genDayStart = (P.days && P.days.length) ? P.days[0] : ''; if (!genDayEnd) genDayEnd = (P.days && P.days.length) ? P.days[P.days.length - 1] : ''; }}
  var AD = P.days || [], ADATA = P.data || {};
  var aggKeys;
  if (genMode === 'month') {{
    aggKeys = ADATA[genSel] ? [genSel] : AD.filter(function(d){{ return d.slice(0,7) === genSel; }});
    if (!aggKeys.length) aggKeys = [genSel];
  }} else if (genMode === 'week') {{
    var w0 = genWeekSel, w1 = addDaysStr(genWeekSel, 6);
    aggKeys = AD.filter(function(d){{ return d >= w0 && d <= w1; }});
    if (!aggKeys.length) aggKeys = [w0];
  }} else {{
    var agd0 = genDayStart || (AD[0]||''), agd1 = genDayEnd || (AD[AD.length-1]||'');
    aggKeys = AD.filter(function(d){{ return d >= agd0 && d <= agd1; }});
    if (!aggKeys.length) aggKeys = [agd0];
  }}
  var A = aggRangeGen(aggKeys, P);
  genCurrentAgg = A;
  buildGenEmpIndex();
  renderGenRegionPanel();
  var t = A.total;
  var cards = '';
  P.cols.forEach(function(c){{ cards += genCard(c, t); }});
  document.getElementById('genCards').innerHTML = cards;
  var mo = P.majorOrder || [];
  var roG = P.regionOrder || {{}};
  function rOrdG(r){{ return roIdx(roG, r.major, r.region); }}
  function sMaj(a,b){{ var ia=mo.indexOf(a.name), ib=mo.indexOf(b.name); if(ia!==ib) return (ia<0?99:ia)-(ib<0?99:ib); return 0; }}
  function sMajReg(a,b){{ var ia=mo.indexOf(a.major), ib=mo.indexOf(b.major); if(ia!==ib) return (ia<0?99:ia)-(ib<0?99:ib); var d=rOrdG(a)-rOrdG(b); if(d!==0) return d; return a.region<b.region?-1:a.region>b.region?1:0; }}
  var majors = A.major.slice().sort(sMaj);
  var details = A.detail.slice().sort(sMajReg);
  var whs = A.warehouse.slice().sort(function(a,b){{ var d=sMajReg(a,b); if(d!==0) return d; if(a.wh!==b.wh) return a.wh<b.wh?-1:1; return 0; }});
  var grps = A.group.slice().sort(function(a,b){{ var d=sMajReg(a,b); if(d!==0) return d; if(a.wh!==b.wh) return a.wh<b.wh?-1:1; if(a.group!==b.group) return a.group<b.group?-1:1; return 0; }});
  var majVal = function(o){{ return (P.type==='formalAtt') ? (o.total||0) : (o.yqr||0); }};
  var NCOL = P.cols.length + 2;
  var h1='';
  majors.forEach(function(m){{
    h1 += '<tr class="att-major" data-major="'+attrEsc(m.name)+'"><td>'+esc(m.name)+'</td>'+genCells(m,t,P)+'</tr>';
  }});
  document.getElementById('genMajorBody').innerHTML = h1;
  var h2='';
  var curM2=null, curMObj2=null;
  details.forEach(function(r){{
    if(r.major!==curM2){{
      curM2=r.major;
      curMObj2=majors.find(function(x){{return x.name===curM2;}})||{{}};
      h2 += '<tr class="grp ghd-m expanded" data-major="'+attrEsc(curM2)+'"><td colspan="'+NCOL+'"><span class="fold-icon">▾</span> '+esc(curM2)+'（大区合计 '+fmt(majVal(curMObj2))+'）</td></tr>';
    }}
    h2 += '<tr class="att-region" data-major="'+attrEsc(r.major)+'" data-region="'+attrEsc(r.region)+'"><td class="indent">'+esc(r.region)+'</td>'+genCells(r,curMObj2,P)+'</tr>';
  }});
  document.getElementById('genDetailBody').innerHTML = h2;
  var h3='';
  var curM3=null, curR3=null, curMObj3=null, curRObj3=null;
  whs.forEach(function(w){{
    if(w.major!==curM3){{
      curM3=w.major; curR3=null; curRObj3=null;
      curMObj3=majors.find(function(x){{return x.name===curM3;}})||{{}};
      h3 += '<tr class="grp ghd-m expanded" data-major="'+attrEsc(curM3)+'"><td colspan="'+NCOL+'"><span class="fold-icon">▾</span> '+esc(curM3)+'（大区合计 '+fmt(majVal(curMObj3))+'）</td></tr>';
    }}
    if(w.region!==curR3){{
      curR3=w.region;
      curRObj3=details.find(function(x){{return x.major===w.major&&x.region===w.region;}})||{{}};
      h3 += '<tr class="subgrp ghd-r expanded" data-major="'+attrEsc(w.major)+'" data-region="'+attrEsc(w.region)+'"><td colspan="'+NCOL+'"><span class="fold-icon">▾</span> '+esc(w.region)+'（区域合计 '+fmt(majVal(curRObj3))+'）</td></tr>';
    }}
    h3 += '<tr class="att-wh" data-major="'+attrEsc(w.major)+'" data-region="'+attrEsc(w.region)+'" data-wh="'+attrEsc(w.wh)+'"><td class="indent2">'+esc(w.wh)+'</td>'+genCells(w,curRObj3,P)+'</tr>';
  }});
  var emptyMsg = '<tr><td colspan="'+NCOL+'" style="padding:14px;text-align:center;color:#94a3b8;font-size:13px">按天视图仅展示大区 / 区域两级，请切换到「按月」查看仓 / 组明细</td></tr>';
  document.getElementById('genWhBody').innerHTML = whs.length ? h3 : emptyMsg;
  var h4='';
  var curM4=null, curR4=null, curW4=null, curWObj4=null;
  grps.forEach(function(g){{
    if(g.major!==curM4){{
      curM4=g.major; curR4=null; curW4=null; curWObj4=null;
      var mm4=majors.find(function(x){{return x.name===curM4;}})||{{}};
      h4 += '<tr class="grp ghd-m expanded" data-major="'+attrEsc(curM4)+'"><td colspan="'+NCOL+'"><span class="fold-icon">▾</span> '+esc(curM4)+'（大区合计 '+fmt(majVal(mm4))+'）</td></tr>';
    }}
    if(g.region!==curR4){{
      curR4=g.region; curW4=null; curWObj4=null;
      var rr4=details.find(function(x){{return x.major===g.major&&x.region===g.region;}})||{{}};
      h4 += '<tr class="subgrp ghd-r expanded" data-major="'+attrEsc(g.major)+'" data-region="'+attrEsc(g.region)+'"><td colspan="'+NCOL+'"><span class="fold-icon">▾</span> '+esc(g.region)+'（区域合计 '+fmt(majVal(rr4))+'）</td></tr>';
    }}
    if(g.wh!==curW4){{
      curW4=g.wh;
      curWObj4=whs.find(function(x){{return x.major===g.major&&x.region===g.region&&x.wh===g.wh;}})||{{}};
      h4 += '<tr class="subgrp3 ghd-w expanded" data-major="'+attrEsc(g.major)+'" data-region="'+attrEsc(g.region)+'" data-wh="'+attrEsc(g.wh)+'"><td colspan="'+NCOL+'"><span class="fold-icon">▾</span> '+esc(g.wh)+'（仓合计 '+fmt(majVal(curWObj4))+'）</td></tr>';
    }}
    var ek4 = g.major + '|' + g.region + '|' + g.wh + '|' + g.group;
    var gCnt = (genEmpIdx[ek4] || []).length;
    var gTotal = (P.empCount && P.empCount[ek4]) ? P.empCount[ek4] : 0;
    var gBadge = gTotal ? ' <span class="emp-count">（未及时确认 ' + gCnt + ' 条，点击展开）</span>' : '';
    h4 += '<tr class="att-grp" data-major="'+attrEsc(g.major)+'" data-region="'+attrEsc(g.region)+'" data-wh="'+attrEsc(g.wh)+'" data-group="'+attrEsc(g.group)+'" data-expanded="false" onclick="toggleGenEmp(this)"><td class="indent3"><span class="fold-icon">▸</span> '+esc(g.group)+gBadge+'</td>'+genCells(g,curWObj4,P)+'</tr>';
  }});
  document.getElementById('genGrpBody').innerHTML = grps.length ? h4 : emptyMsg;
  var genRangeLabel = genMode==='month' ? monthLabel(genSel) : (genMode==='week' ? weekLabel(genWeekSel, addDaysStr(genWeekSel, 6)) : (dayLabel(genDayStart)+(genDayStart!==genDayEnd?' ~ '+dayLabel(genDayEnd):'')));
  var pk = document.getElementById('btnPicker'); if (pk) pk.textContent = genRangeLabel;
  syncModeBtns(genMode);
  renderGenTop10(P);
  updateActiveGenTab();
}}
function genRate(r, c){{ return c.pct ? (r[c.den] ? (r[c.num]/r[c.den]*100) : null) : (r[c.key]||0); }}
function genFmt(c, v){{ return c.pct ? (v==null?'—':v.toFixed(1)+'%') : fmt(v); }}
function genCard(c, t){{ var v=genRate(t,c); return '<div class="card"><div class="v">'+genFmt(c,v)+'</div><div class="l">'+c.label+'</div></div>'; }}
function genCells(r, parentTotal, P){{
  var html='';
  P.cols.forEach(function(c){{ html += '<td class="num">'+genFmt(c, genRate(r,c))+'</td>'; }});
  var pct;
  if (P.type === 'formalAtt') {{
    pct = r.total ? ((r.total - r.untimely) / r.total * 100) : 0;
  }} else {{
    var barKey = P.cols[0].key;
    pct = (parentTotal && parentTotal[barKey]) ? (r[barKey]/parentTotal[barKey]*100) : 0;
  }}
  html += '<td><div class="bar"><div class="bar-fill" style="width:'+pct.toFixed(1)+'%"></div></div><span class="bar-num">'+pct.toFixed(1)+'%</span></td>';
  return html;
}}
function aggRangeGen(keys_arr, P){{
  var ADATA = P.data, keys = P.aggKeys;
  var maj={{}}, det={{}}, wh={{}}, grp={{}}, tot={{}};
  keys.forEach(function(k){{ tot[k]=0; }});
  (keys_arr||[]).forEach(function(d){{
    var day = ADATA[d]; if (!day) return;
    keys.forEach(function(k){{ tot[k] += (day.total[k]||0); }});
    day.major.forEach(function(r){{ var k=r.name; if(!maj[k]) maj[k]={name:k}; keys.forEach(function(kk){{ maj[k][kk]=(maj[k][kk]||0)+(r[kk]||0); }}); }});
    day.detail.forEach(function(r){{ var k=r.major+'|'+r.region; if(!det[k]) det[k]={major:r.major,region:r.region}; keys.forEach(function(kk){{ det[k][kk]=(det[k][kk]||0)+(r[kk]||0); }}); }});
    day.warehouse.forEach(function(r){{ var k=r.major+'|'+r.region+'|'+r.wh; if(!wh[k]) wh[k]={major:r.major,region:r.region,wh:r.wh}; keys.forEach(function(kk){{ wh[k][kk]=(wh[k][kk]||0)+(r[kk]||0); }}); }});
    day.group.forEach(function(r){{ var k=r.major+'|'+r.region+'|'+r.wh+'|'+r.group; if(!grp[k]) grp[k]={major:r.major,region:r.region,wh:r.wh,group:r.group}; keys.forEach(function(kk){{ grp[k][kk]=(grp[k][kk]||0)+(r[kk]||0); }}); }});
  }});
  return {{total:tot, major:Object.values(maj), detail:Object.values(det), warehouse:Object.values(wh), group:Object.values(grp)}};
}}
function genHid(sel, hide){{ document.querySelectorAll(sel).forEach(function(r){{ r.classList.toggle('hidden', hide); }}); }}
function genAnyHid(sel){{ var a=document.querySelectorAll(sel); for(var i=0;i<a.length;i++){{ if(a[i].classList.contains('hidden')) return true; }} return false; }}
function genHIcon(h, expand){{ h.classList.toggle('expanded', expand); var ic=h.querySelector('.fold-icon'); if(ic) ic.textContent = expand ? '▾' : '▸'; }}
document.getElementById('genDetailBody').addEventListener('click', function(e){{
  var h = e.target.closest('tr.ghd-m'); if(!h) return;
  var sel = 'tr.att-region[data-major="' + cssEsc(h.getAttribute('data-major')) + '"]';
  var expand = genAnyHid(sel); genHid(sel, !expand); genHIcon(h, expand);
}});
document.getElementById('genWhBody').addEventListener('click', function(e){{
  var hm = e.target.closest('tr.ghd-m');
  if (hm) {{
    var maj = cssEsc(hm.getAttribute('data-major'));
    var sR = 'tr.ghd-r[data-major="' + maj + '"]';
    var sW = 'tr.att-wh[data-major="' + maj + '"]';
    var expand = genAnyHid(sR) || genAnyHid(sW);
    genHid(sR, !expand); genHid(sW, !expand);
    if (expand) {{
      document.querySelectorAll(sR).forEach(function(rh) {{
        if (rh.dataset.expanded === 'false') genHid('tr.att-wh[data-major="' + maj + '"][data-region="' + cssEsc(rh.getAttribute('data-region')) + '"]', true);
      }});
    }}
    genHIcon(hm, expand);
    return;
  }}
  var hr = e.target.closest('tr.ghd-r');
  if (hr) {{
    var s = 'tr.att-wh[data-major="' + cssEsc(hr.getAttribute('data-major')) + '"][data-region="' + cssEsc(hr.getAttribute('data-region')) + '"]';
    var expand2 = genAnyHid(s); genHid(s, !expand2); genHIcon(hr, expand2);
  }}
}});
document.getElementById('genGrpBody').addEventListener('click', function(e){{
  var hm = e.target.closest('tr.ghd-m');
  if (hm) {{
    var maj = cssEsc(hm.getAttribute('data-major'));
    var sR = 'tr.ghd-r[data-major="' + maj + '"]';
    var sW = 'tr.ghd-w[data-major="' + maj + '"]';
    var sG = 'tr.att-grp[data-major="' + maj + '"]';
    var expand = genAnyHid(sR) || genAnyHid(sW) || genAnyHid(sG);
    genHid(sR, !expand); genHid(sW, !expand); genHid(sG, !expand);
    if (expand) {{
      document.querySelectorAll(sR).forEach(function(rh) {{
        if (rh.dataset.expanded === 'false') {{
          var rg = cssEsc(rh.getAttribute('data-region'));
          genHid('tr.ghd-w[data-major="' + maj + '"][data-region="' + rg + '"]', true);
          genHid('tr.att-grp[data-major="' + maj + '"][data-region="' + rg + '"]', true);
        }}
      }});
      document.querySelectorAll(sW).forEach(function(wh2) {{
        if (wh2.dataset.expanded === 'false') {{
          genHid('tr.att-grp[data-major="' + maj + '"][data-region="' + cssEsc(wh2.getAttribute('data-region')) + '"][data-wh="' + cssEsc(wh2.getAttribute('data-wh')) + '"]', true);
        }}
      }});
    }}
    genHIcon(hm, expand);
    return;
  }}
  var hr = e.target.closest('tr.ghd-r');
  if (hr) {{
    var maj2 = cssEsc(hr.getAttribute('data-major')), rg2 = cssEsc(hr.getAttribute('data-region'));
    var sW2 = 'tr.ghd-w[data-major="' + maj2 + '"][data-region="' + rg2 + '"]';
    var sG2 = 'tr.att-grp[data-major="' + maj2 + '"][data-region="' + rg2 + '"]';
    var expand2 = genAnyHid(sW2) || genAnyHid(sG2);
    genHid(sW2, !expand2); genHid(sG2, !expand2);
    if (expand2) {{
      document.querySelectorAll(sW2).forEach(function(wh3) {{
        if (wh3.dataset.expanded === 'false') {{
          genHid('tr.att-grp[data-major="' + maj2 + '"][data-region="' + rg2 + '"][data-wh="' + cssEsc(wh3.getAttribute('data-wh')) + '"]', true);
        }}
      }});
    }}
    genHIcon(hr, expand2);
    return;
  }}
  var hw = e.target.closest('tr.ghd-w');
  if (hw) {{
    var s = 'tr.att-grp[data-major="' + cssEsc(hw.getAttribute('data-major')) + '"][data-region="' + cssEsc(hw.getAttribute('data-region')) + '"][data-wh="' + cssEsc(hw.getAttribute('data-wh')) + '"]';
    var expand3 = genAnyHid(s); genHid(s, !expand3); genHIcon(hw, expand3);
  }}
}});
function setModeGen(m){{
  if (m !== 'month' && (!genPayload || !genPayload.days || !genPayload.days.length)){{ alert('该板块仅支持按月查看'); return; }}
  genMode = m;
  syncModeBtns(m);
  renderGen(genPayload);
}}
function stepGen(dir){{ if(genMode==='month'){{ var i=genPayload.months.indexOf(genSel); i=Math.min(genPayload.months.length-1, Math.max(0, i+dir)); genSel=genPayload.months[i]; }} else if(genMode==='week'){{ var wk=weeksOf(genPayload.days); var i=wk.findIndex(function(w){{return w[0]===genWeekSel;}}); if(i<0) genWeekSel=wk.length?wk[wk.length-1][0]:''; else {{ i=Math.min(wk.length-1, Math.max(0, i+dir)); genWeekSel=wk[i][0]; }} }} else {{ var i=genPayload.days.indexOf(genDayStart); i=Math.min(genPayload.days.length-1, Math.max(0, i+dir)); genDayStart=genPayload.days[i]; genDayEnd=genPayload.days[i]; }} renderGen(genPayload); }}
function toggleGenDropdownShared(){{
  e = arguments.length ? arguments[0] : undefined; if (e) e.stopPropagation();
  var dd = document.getElementById('dropdown'); if(!dd) return;
  if(!dd.classList.contains('hidden')){{ dd.classList.add('hidden'); return; }}
  dd.innerHTML='';
  if(genMode==='day'){{
    genPayload.days.forEach(function(d){{ dd.appendChild(ddItem(dayLabel(d), function(){{ genDayStart=d; genDayEnd=d; renderGen(genPayload); closeDropdown(); }})); }});
  }} else if(genMode==='week'){{
    weeksOf(genPayload.days).forEach(function(w){{ dd.appendChild(ddItem(weekLabel(w[0],w[1]), function(){{ genWeekSel=w[0]; renderGen(genPayload); closeDropdown(); }})); }});
  }} else {{
    genPayload.months.forEach(function(m){{ dd.appendChild(ddItem(monthLabel(m), function(){{ genSel=m; renderGen(genPayload); closeDropdown(); }})); }});
  }}
  dd.classList.remove('hidden');
}}

let curWt='formal', curSec='att';
let genMode='month', genSel='', genDayStart='', genDayEnd='', genWeekSel='';
function showCell(wt, sec) {{
  curWt = wt; curSec = sec;
  var vf = document.getElementById('viewFormal');
  var va = document.getElementById('viewAttend');
  var vg = document.getElementById('viewGen');
  var showFormal = (sec === 'sign');
  var showAtt = (wt === 'labor' && sec === 'att');
  var showGen = (wt === 'formal' && sec === 'att');
  if (vf) vf.style.display = showFormal ? 'block' : 'none';
  if (va) va.style.display = showAtt ? 'block' : 'none';
  if (vg) vg.style.display = showGen ? 'block' : 'none';
  ['wtFormal','wtLabor'].forEach(function(id){{ var e=document.getElementById(id); if(e) e.classList.toggle('active', id===(wt==='formal'?'wtFormal':'wtLabor')); }});
  ['secAtt','secSign'].forEach(function(id){{ var e=document.getElementById(id); if(e) e.classList.toggle('active', id===('sec'+sec.charAt(0).toUpperCase()+sec.slice(1))); }});
  if (showFormal) {{
    payload = (wt === 'formal') ? formalPayload : laborPayload;
    months = payload.months; days = payload.days; data = payload.data;
    var sub = document.getElementById('hdrSub'); if (sub) sub.textContent = payload.subtitle || '';
    var rbtn = document.getElementById('btnRegion'); if (rbtn) rbtn.textContent = 'FBU交付前台';
    var cTotalL = document.getElementById('cTotalL');
    var cIngL = document.getElementById('cIngL');
    var secTopCap = document.getElementById('secTopCap');
    if (wt === 'formal') {{
      if (cTotalL) cTotalL.textContent = '补签合计（条）';
      if (cIngL) cIngL.textContent = '审批中';
      if (secTopCap) secTopCap.innerHTML = '五、各区补签 Top10 员工（按区域内员工补签数排序，含已完成+审批中）　<small style="font-weight:400;color:#64748b">点击大区/区域可展开或收起 Top 员工</small>';
    }} else {{
      if (cTotalL) cTotalL.textContent = '补签合计（应补签数）';
      if (cIngL) cIngL.textContent = '未完成';
      if (secTopCap) secTopCap.innerHTML = '五、各区补签 Top10 员工（按区域内员工补签数排序，含已完成+未完成）　<small style="font-weight:400;color:#64748b">点击大区/区域可展开或收起 Top 员工</small>';
    }}
    if (payload.months && payload.months.length) selected = payload.months[payload.months.length - 1];
    setMode('month'); applyNote(); render(); setupStickyHeaders();
  }} else if (showAtt) {{
    renderAttend();
  }} else if (showGen) {{
    genPayload = (wt === 'formal' && sec === 'att') ? formalAttPayload : null;
    if (!genPayload) return;
    if (!genPayload.days || !genPayload.days.length) genMode = 'month';
    var rbtn2 = document.getElementById('btnRegion'); if (rbtn2) rbtn2.textContent = 'FBU交付前台';
    renderGen(genPayload);
  }}
}}
showCell('formal', 'att');
function setupStickyHeaders() {{
  destroyStickyHeaders();
  ['tableMajor','tableDetail','tableWh','tableGrp','tableTop'].forEach(id => {{
    const table = document.getElementById(id);
    if (!table) return;
    const thead = table.querySelector('thead');
    if (!thead) return;
    const wrap = document.createElement('div');
    wrap.className = 'sticky-header-clone';
    const cloneTable = document.createElement('table');
    cloneTable.className = 'clone-table';
    cloneTable.innerHTML = '<thead>' + thead.innerHTML + '</thead>';
    wrap.appendChild(cloneTable);
    (document.documentElement || document.body).appendChild(wrap);
    stickyHeaderClones.push({{ table, wrap, cloneTable }});
  }});
  updateStickyHeaders();
}}
let stickyTicking = false;
function updateStickyHeaders() {{
  if (stickyTicking) return;
  stickyTicking = true;
  requestAnimationFrame(() => {{
    stickyTicking = false;
    stickyHeaderClones.forEach(({ table, wrap, cloneTable }) => {{
      const rect = table.getBoundingClientRect();
      const thead = table.querySelector('thead');
      const theadHeight = thead ? thead.offsetHeight : 0;
      if (rect.top < 0 && rect.bottom > theadHeight) {{
        syncCloneWidths(table, cloneTable);
        wrap.style.display = 'block';
        wrap.style.left = rect.left + 'px';
        wrap.style.width = rect.width + 'px';
      }} else {{
        wrap.style.display = 'none';
      }}
    }});
  }});
}}
window.addEventListener('scroll', updateStickyHeaders, {{ passive: true }});
document.addEventListener('scroll', updateStickyHeaders, {{ passive: true }});
window.addEventListener('resize', updateStickyHeaders);
setInterval(updateStickyHeaders, 80);

formalNoteHtml = (document.querySelector('.note-body') || {{}}).innerHTML || '';
setMode('month');
setupStickyHeaders();
</script>
</body></html>"""

html_template = html_template.replace('{{', '{').replace('}}', '}')
html = html_template.replace('{json_data}', json_data).replace('{labor_json}', labor_json).replace('{weekdays}', json.dumps(WEEKDAYS)).replace('{formal_att_json}', formal_att_json)

# ===== 考勤确认及时性（劳务工）看板：独立 view-panel（普通花括号，不走模板 {{ }} 转换）=====
attend_block = """
<div class="view-panel" id="viewAttend" style="display:none">
<div class="header">
<h1>考勤确认及时率（劳务工）</h1>
<div class="sub" id="attendSub"></div>
</div>
<div class="section-tabs" id="attendSectionTabs">
  <button data-target="attSecMajor" class="active">大区汇总</button>
  <button data-target="attSecDetail">区域明细</button>
  <button data-target="attSecWh">仓明细</button>
  <button data-target="attSecGrp">组明细</button>
  <button data-target="attSecTop">Top10 员工</button>
</div>
<div class="cards" id="attendCards"></div>
<div class="section" id="attSecMajor">
  <div class="section-caption">一、大区（三级部门）汇总</div>
  <div class="table-wrapper"><table id="tableAttMajor"><thead><tr><th>大区</th><th>考勤总数</th><th>已确认数</th><th>未确认数</th><th>及时确认率</th><th>图例</th></tr></thead><tbody id="attMajorBody"></tbody></table></div>
</div>
<div class="section" id="attSecDetail">
  <div class="section-caption">二、大区 × 区域（三级部门 × 四级部门）明细</div>
  <div class="table-wrapper"><table id="tableAttDetail"><thead><tr><th>区域（四级部门）</th><th>考勤总数</th><th>已确认数</th><th>未确认数</th><th>及时确认率</th><th>图例</th></tr></thead><tbody id="attDetailBody"></tbody></table></div>
</div>
<div class="section" id="attSecWh">
  <div class="section-caption">三、大区 × 区域 × 仓（三级部门 × 四级部门 × 五级部门）明细</div>
  <div class="table-wrapper"><table id="tableAttWh"><thead><tr><th>仓（五级部门）</th><th>考勤总数</th><th>已确认数</th><th>未确认数</th><th>及时确认率</th><th>图例</th></tr></thead><tbody id="attWhBody"></tbody></table></div>
</div>
<div class="section" id="attSecGrp">
  <div class="section-caption">四、大区 × 区域 × 仓 × 组（三级部门 × 四级部门 × 五级部门 × 六级部门）明细　<small style="font-weight:400;color:#64748b">点击组可展开员工明细</small></div>
  <div class="table-wrapper"><table id="tableAttGrp"><thead><tr><th>大区 / 区域 / 仓 / 组</th><th>考勤总数</th><th>已确认数</th><th>未确认数</th><th>及时确认率</th><th>图例</th></tr></thead><tbody id="attGrpBody"></tbody></table></div>
</div>
<div class="section" id="attSecTop">
  <div class="section-caption">五、各区未确认 Top10 员工（按区域，未确认数排序，整体统计不随日期筛选）</div>
  <div class="table-wrapper"><table id="tableAttTop"><thead><tr><th>排名</th><th>姓名</th><th>工号</th><th>工种</th><th>主属仓</th><th>主属组</th><th>未确认数</th></tr></thead><tbody id="attTopBody"></tbody></table></div>
</div>
<div class="note"><div class="note-header" data-notebody="attendNoteBody" onclick="toggleNoteById(this)"><div class="note-icon">i</div><div class="note-title">数据说明</div><div class="note-fold">▾</div></div><div class="note-body" id="attendNoteBody"></div></div>
</div>

<style>
#viewAttend .att-major{background:#f1f5f9;font-weight:700}
#viewAttend .att-region{cursor:default;background:#fafcff}
#viewAttend .att-region td:first-child{padding-left:30px}
#viewAttend .att-wh{cursor:default;background:#f6f9ff}
#viewAttend .att-grp{cursor:pointer;background:#fff}
#viewAttend .att-grp:hover{background:#f3f7ff}
#viewAttend .emp-subrow td:first-child{padding-left:0}
#viewAttend .labor-rate .bar-fill{background:#3b82f6}
</style>

<script>
const attendPayload = {attend_json};
const ATTEND_METRICS = attendPayload.metrics;
let attendMode = 'month';
let attendSel = attendPayload.months[attendPayload.months.length - 1];
let attendDayStart = '', attendDayEnd = '';
let attendWeekSel = '';
let attendRegionFilter = '';

function attRate(v){ return v == null ? '—' : v.toFixed(1) + '%'; }
function attRange(){
  var AD = attendPayload.days;
  if (attendMode === 'month'){
    var md = AD.filter(function(d){ return d.indexOf(attendSel + '-') === 0; });
    if (md.length) return [md[0], md[md.length - 1]];
    return [attendSel + '-01', attendSel + '-31'];
  } else if (attendMode === 'week'){
    return [attendWeekSel, addDaysStr(attendWeekSel, 6)];
  }
  return [attendDayStart || AD[0], attendDayEnd || AD[AD.length - 1]];
}
function aggRangeAttend(start, end){
  var AD = attendPayload.days, ADATA = attendPayload.data;
  var rangeDays = AD.filter(function(d){ return d >= start && d <= end; });
  if (!rangeDays.length) rangeDays = [start];
  var maj = {}, det = {}, wh = {}, grp = {};
  var tot = {}; ATTEND_METRICS.forEach(function(f){ tot[f] = 0; });
  rangeDays.forEach(function(d){
    var day = ADATA[d]; if (!day) return;
    ATTEND_METRICS.forEach(function(f){ tot[f] += (day.total[f] || 0); });
    day.major.forEach(function(r){ var k = r.name; if (!maj[k]) maj[k] = {name: k}; ATTEND_METRICS.forEach(function(f){ maj[k][f] = (maj[k][f] || 0) + (r[f] || 0); }); });
    day.detail.forEach(function(r){ var k = r.major + '|' + r.region; if (!det[k]) det[k] = {major: r.major, region: r.region}; ATTEND_METRICS.forEach(function(f){ det[k][f] = (det[k][f] || 0) + (r[f] || 0); }); });
    day.warehouse.forEach(function(r){ var k = r.major + '|' + r.region + '|' + r.wh; if (!wh[k]) wh[k] = {major: r.major, region: r.region, wh: r.wh}; ATTEND_METRICS.forEach(function(f){ wh[k][f] = (wh[k][f] || 0) + (r[f] || 0); }); });
    day.group.forEach(function(r){ var k = r.major + '|' + r.region + '|' + r.wh + '|' + r.group; if (!grp[k]) grp[k] = {major: r.major, region: r.region, wh: r.wh, group: r.group}; ATTEND_METRICS.forEach(function(f){ grp[k][f] = (grp[k][f] || 0) + (r[f] || 0); }); });
  });
  return {total: tot, major: Object.values(maj), detail: Object.values(det), warehouse: Object.values(wh), group: Object.values(grp)};
}
function addAttUnconfirmed(A){
  A.total.unconfirmed = (A.total.yqr || 0) - (A.total.sjqr || 0);
  ['major','detail','warehouse','group'].forEach(function(lvl){
    A[lvl].forEach(function(r){ r.unconfirmed = (r.yqr || 0) - (r.sjqr || 0); });
  });
  return A;
}
// 组行角标：未及时确认明细索引（随日期/月份筛选联动，行尾附 ym/ymd）
var attEmpIdx = {};
function buildAttEmpIndex() {
  attEmpIdx = {};
  var idx = attendPayload.empIndex || {};
  Object.keys(idx).forEach(function(k) {
    idx[k].forEach(function(e) {
      var ym = e[e.length - 2], ymd = e[e.length - 1];
      var inRange;
      if (attendMode === 'month') inRange = (ym === attendSel);
      else if (attendMode === 'week') inRange = (ymd >= attendWeekSel && ymd <= addDaysStr(attendWeekSel, 6));
      else inRange = (ymd >= (attendDayStart || '') && ymd <= (attendDayEnd || ''));
      if (!inRange) return;
      if (!attEmpIdx[k]) attEmpIdx[k] = [];
      attEmpIdx[k].push(e);
    });
  });
}
function attCells(r, parentTotal){
  if (!r) return '<td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="num">—</td><td>—</td>';
  var total = r.yqr || 0, confirmed = r.sjqr || 0, unconfirmed = r.unconfirmed || 0;
  var rate = total ? (confirmed / total * 100) : null;
  var rateNum = rate == null ? 0 : rate;
  var bar = '<div class="bar"><div class="bar-fill" style="width:' + rateNum.toFixed(1) + '%"></div></div><span class="bar-num">' + rateNum.toFixed(1) + '%</span>';
  return '<td class="num">' + fmt(total) + '</td><td class="num">' + fmt(confirmed) + '</td><td class="num">' + fmt(unconfirmed) + '</td><td class="num">' + attRate(rate) + '</td><td>' + bar + '</td>';
}
function attCard(v, rate, label){
  var s = rate ? attRate(v) : fmt(v);
  return '<div class="card"><div class="v">' + s + '</div><div class="l">' + label + '</div></div>';
}
function renderAttend(){
  var P = attendPayload;
  if (typeof syncModeBtns === 'function') syncModeBtns(attendMode);
  var sub = document.getElementById('attendSub'); if (sub) sub.textContent = P.subtitle || '';
  var nb = document.getElementById('attendNoteBody'); if (nb) nb.innerHTML = P.noteHtml || '';
  if (typeof updateAttendRegionBtn === 'function') updateAttendRegionBtn();
  var rng = attRange();
  var A = addAttUnconfirmed(aggRangeAttend(rng[0], rng[1]));
  var t = A.total;
  // KPI cards
  document.getElementById('attendCards').innerHTML =
    attCard(t.yqr, false, '考勤总数') + attCard(t.sjqr, false, '已确认数') +
    attCard(t.unconfirmed, false, '未确认数') + attCard(t.yqr ? (t.sjqr / t.yqr * 100) : null, true, '及时确认率');
  // 区域过滤（支持仅按大区筛选：filter 不含 | 时视为大区级）
  var majOrder = P.majorOrder;
  var attFP = attendRegionFilter ? attendRegionFilter.split('|') : null;
  function filtMaj(m){ return !attFP || m === attFP[0]; }
  function filtReg(r){ return !attFP || (r.major === attFP[0] && (!attFP[1] || r.region === attFP[1])); }
  // 排序：大区按 majorOrder，区域按架构固定顺序（与补签率视图 REGION_ORDER 一致），同序按考勤总数降序
  var roA = P.regionOrder || {};
  function rOrdA(r){ var lst = roA[r.major]||[]; var i = lst.indexOf(r.region); return i<0?9999:i; }
  function cmpAttReg(a, b){ var d = rOrdA(a) - rOrdA(b); if (d !== 0) return d; return a.region < b.region ? -1 : a.region > b.region ? 1 : 0; }
  var majors = A.major.slice().sort(function(a, b){ var ia = majOrder.indexOf(a.name), ib = majOrder.indexOf(b.name); if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib); return b.yqr - a.yqr; });
  var details = A.detail.filter(filtReg).sort(function(a, b){ var ia = majOrder.indexOf(a.major), ib = majOrder.indexOf(b.major); if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib); var d = cmpAttReg(a, b); if (d !== 0) return d; return b.yqr - a.yqr; });
  var whs = A.warehouse.filter(filtReg).sort(function(a, b){ var d = cmpAttReg(a, b); if (d !== 0) return d; if (a.wh !== b.wh) return a.wh < b.wh ? -1 : 1; return b.yqr - a.yqr; });
  var grps = A.group.filter(filtReg).sort(function(a, b){ var d = cmpAttReg(a, b); if (d !== 0) return d; if (a.wh !== b.wh) return a.wh < b.wh ? -1 : 1; if (a.group !== b.group) return a.group < b.group ? -1 : 1; return b.yqr - a.yqr; });

  // 板块一：大区（平铺，与补签率一致）
  var h1 = '';
  majors.forEach(function(m){
    h1 += '<tr class="att-major" data-major="' + attrEsc(m.name) + '"><td>' + esc(m.name) + '</td>' + attCells(m, t) + '</tr>';
  });
  document.getElementById('attMajorBody').innerHTML = h1;

  // 板块二：区域（大区组头 + 区域子行，占大区比）
  var NCOL = 6;
  var h2 = '';
  var curM2 = null, curMObj2 = null;
  details.forEach(function(r){
    if (r.major !== curM2){
      curM2 = r.major;
      curMObj2 = majors.find(function(x){ return x.name === curM2; }) || {};
      h2 += '<tr class="grp ahd-m expanded" data-major="' + attrEsc(curM2) + '"><td colspan="' + NCOL + '"><span class="fold-icon">▾</span> ' + esc(curM2) + '（大区合计 ' + fmt(curMObj2.yqr || 0) + '）</td></tr>';
    }
    h2 += '<tr class="att-region" data-major="' + attrEsc(r.major) + '" data-region="' + attrEsc(r.region) + '"><td>' + esc(r.region) + '</td>' + attCells(r, curMObj2) + '</tr>';
  });
  document.getElementById('attDetailBody').innerHTML = h2;

  // 板块三：仓（大区组头 + 区域子组头 + 仓行，占区域比）
  var h3 = '';
  var curM3 = null, curR3 = null, curRObj3 = null;
  whs.forEach(function(w){
    if (w.major !== curM3){
      curM3 = w.major; curR3 = null; curRObj3 = null;
      var mm3 = majors.find(function(x){ return x.name === curM3; }) || {};
      h3 += '<tr class="grp ahd-m expanded" data-major="' + attrEsc(curM3) + '"><td colspan="' + NCOL + '"><span class="fold-icon">▾</span> ' + esc(curM3) + '（大区合计 ' + fmt(mm3.yqr || 0) + '）</td></tr>';
    }
    if (w.region !== curR3){
      curR3 = w.region;
      curRObj3 = details.find(function(x){ return x.major === w.major && x.region === w.region; }) || {};
      h3 += '<tr class="subgrp ahd-r expanded" data-major="' + attrEsc(w.major) + '" data-region="' + attrEsc(w.region) + '"><td colspan="' + NCOL + '"><span class="fold-icon">▾</span> ' + esc(w.region) + '（区域合计 ' + fmt(curRObj3.yqr || 0) + '）</td></tr>';
    }
    h3 += '<tr class="att-wh" data-major="' + attrEsc(w.major) + '" data-region="' + attrEsc(w.region) + '" data-wh="' + attrEsc(w.wh) + '"><td>' + esc(w.wh) + '</td>' + attCells(w, curRObj3) + '</tr>';
  });
  document.getElementById('attWhBody').innerHTML = h3;

  // 板块四：组（大区 + 区域 + 仓 组头 + 组行，占仓比；组行带未及时确认角标，可展开明细）
  var h4 = '';
  var curM4 = null, curR4 = null, curW4 = null, curWObj4 = null;
  buildAttEmpIndex();
  grps.forEach(function(g){
    if (g.major !== curM4){
      curM4 = g.major; curR4 = null; curW4 = null; curWObj4 = null;
      var mm4 = majors.find(function(x){ return x.name === curM4; }) || {};
      h4 += '<tr class="grp ahd-m expanded" data-major="' + attrEsc(curM4) + '"><td colspan="' + NCOL + '"><span class="fold-icon">▾</span> ' + esc(curM4) + '（大区合计 ' + fmt(mm4.yqr || 0) + '）</td></tr>';
    }
    if (g.region !== curR4){
      curR4 = g.region; curW4 = null; curWObj4 = null;
      var rr4 = details.find(function(x){ return x.major === g.major && x.region === g.region; }) || {};
      h4 += '<tr class="subgrp ahd-r expanded" data-major="' + attrEsc(g.major) + '" data-region="' + attrEsc(g.region) + '"><td colspan="' + NCOL + '"><span class="fold-icon">▾</span> ' + esc(g.region) + '（区域合计 ' + fmt(rr4.yqr || 0) + '）</td></tr>';
    }
    if (g.wh !== curW4){
      curW4 = g.wh;
      curWObj4 = whs.find(function(x){ return x.major === g.major && x.region === g.region && x.wh === g.wh; }) || {};
      h4 += '<tr class="subgrp3 ahd-w expanded" data-major="' + attrEsc(g.major) + '" data-region="' + attrEsc(g.region) + '" data-wh="' + attrEsc(g.wh) + '"><td colspan="' + NCOL + '"><span class="fold-icon">▾</span> ' + esc(g.wh) + '（仓合计 ' + fmt(curWObj4.yqr || 0) + '）</td></tr>';
    }
    var gk = g.major + '|' + g.region + '|' + g.wh + '|' + g.group;
    var eCnt = (attEmpIdx[gk] || []).length;
    var gBadge = eCnt ? ' <span class="emp-count">（未及时确认 ' + eCnt + ' 条，点击展开）</span>' : '';
    h4 += '<tr class="att-grp" data-major="' + attrEsc(g.major) + '" data-region="' + attrEsc(g.region) + '" data-wh="' + attrEsc(g.wh) + '" data-group="' + attrEsc(g.group) + '" data-expanded="false"><td>' + esc(g.group) + gBadge + '</td>' + attCells(g, curWObj4) + '</tr>';
  });
  document.getElementById('attGrpBody').innerHTML = h4;

  // 板块五：Top 员工
  var h5 = '';
  majOrder.forEach(function(mj){
    var regs = details.filter(function(r){ return r.major === mj; }).map(function(r){ return r.region; });
    regs.forEach(function(rg){
      var arr = (P.topEmpIndex && P.topEmpIndex[mj + '|' + rg]) || [];
      if (!arr.length) return;
      h5 += '<tr class="att-major"><td colspan="7">' + esc(mj) + ' / ' + esc(rg) + '（未确认 Top10）</td></tr>';
      arr.forEach(function(e, i){
        h5 += '<tr class="top-emp-row"><td class="num">' + (i + 1) + '</td><td>' + esc(e.name) + '</td><td>' + esc(e.gong) + '</td><td>' + esc(e.zg || '—') + '</td><td>' + esc(e.wh) + '</td><td>' + esc(e.group) + '</td><td class="num">' + fmt(e.unc) + '</td></tr>';
      });
    });
  });
  document.getElementById('attTopBody').innerHTML = h5;
  updateAttendDateLabel();
}
// 组头折叠辅助（与补签率视图折叠交互一致）
function attHid(sel, hide){ document.querySelectorAll(sel).forEach(function(r){ r.classList.toggle('hidden', hide); }); }
function attAnyHid(sel){ var a=document.querySelectorAll(sel); for(var i=0;i<a.length;i++){ if(a[i].classList.contains('hidden')) return true; } return false; }
function attHIcon(h, expand){ h.classList.toggle('expanded', expand); var ic=h.querySelector('.fold-icon'); if(ic) ic.textContent = expand ? '▾' : '▸'; }
document.getElementById('attDetailBody').addEventListener('click', function(e){
  var h = e.target.closest('tr.ahd-m'); if (!h) return;
  var sel = 'tr.att-region[data-major="' + cssEsc(h.getAttribute('data-major')) + '"]';
  var expand = attAnyHid(sel); attHid(sel, !expand); attHIcon(h, expand);
});
document.getElementById('attWhBody').addEventListener('click', function(e){
  var hm = e.target.closest('tr.ahd-m');
  if (hm) {
    var maj = cssEsc(hm.getAttribute('data-major'));
    var sR = 'tr.ahd-r[data-major="' + maj + '"]';
    var sW = 'tr.att-wh[data-major="' + maj + '"]';
    var expand = attAnyHid(sR) || attAnyHid(sW);
    attHid(sR, !expand); attHid(sW, !expand);
    if (expand) {
      document.querySelectorAll(sR).forEach(function(rh) {
        if (rh.dataset.expanded === 'false') attHid('tr.att-wh[data-major="' + maj + '"][data-region="' + cssEsc(rh.getAttribute('data-region')) + '"]', true);
      });
    }
    attHIcon(hm, expand);
    return;
  }
  var hr = e.target.closest('tr.ahd-r');
  if (hr) {
    var s = 'tr.att-wh[data-major="' + cssEsc(hr.getAttribute('data-major')) + '"][data-region="' + cssEsc(hr.getAttribute('data-region')) + '"]';
    var expand2 = attAnyHid(s); attHid(s, !expand2); attHIcon(hr, expand2);
  }
});
document.getElementById('attGrpBody').addEventListener('click', function(e){
  var hm = e.target.closest('tr.ahd-m');
  if (hm) {
    var maj = cssEsc(hm.getAttribute('data-major'));
    var sR = 'tr.ahd-r[data-major="' + maj + '"]';
    var sW = 'tr.ahd-w[data-major="' + maj + '"]';
    var sG = 'tr.att-grp[data-major="' + maj + '"]';
    var expand = attAnyHid(sR) || attAnyHid(sW) || attAnyHid(sG);
    attHid(sR, !expand); attHid(sW, !expand); attHid(sG, !expand);
    if (expand) {
      document.querySelectorAll(sR).forEach(function(rh) {
        if (rh.dataset.expanded === 'false') {
          var rg = cssEsc(rh.getAttribute('data-region'));
          attHid('tr.ahd-w[data-major="' + maj + '"][data-region="' + rg + '"]', true);
          attHid('tr.att-grp[data-major="' + maj + '"][data-region="' + rg + '"]', true);
        }
      });
      document.querySelectorAll(sW).forEach(function(wh2) {
        if (wh2.dataset.expanded === 'false') {
          attHid('tr.att-grp[data-major="' + maj + '"][data-region="' + cssEsc(wh2.getAttribute('data-region')) + '"][data-wh="' + cssEsc(wh2.getAttribute('data-wh')) + '"]', true);
        }
      });
    }
    attHIcon(hm, expand);
    return;
  }
  var hr = e.target.closest('tr.ahd-r');
  if (hr) {
    var maj2 = cssEsc(hr.getAttribute('data-major')), rg2 = cssEsc(hr.getAttribute('data-region'));
    var sW2 = 'tr.ahd-w[data-major="' + maj2 + '"][data-region="' + rg2 + '"]';
    var sG2 = 'tr.att-grp[data-major="' + maj2 + '"][data-region="' + rg2 + '"]';
    var expand2 = attAnyHid(sW2) || attAnyHid(sG2);
    attHid(sW2, !expand2); attHid(sG2, !expand2);
    if (expand2) {
      document.querySelectorAll(sW2).forEach(function(wh3) {
        if (wh3.dataset.expanded === 'false') {
          attHid('tr.att-grp[data-major="' + maj2 + '"][data-region="' + rg2 + '"][data-wh="' + cssEsc(wh3.getAttribute('data-wh')) + '"]', true);
        }
      });
    }
    attHIcon(hr, expand2);
    return;
  }
  var hw = e.target.closest('tr.ahd-w');
  if (hw) {
    var s = 'tr.att-grp[data-major="' + cssEsc(hw.getAttribute('data-major')) + '"][data-region="' + cssEsc(hw.getAttribute('data-region')) + '"][data-wh="' + cssEsc(hw.getAttribute('data-wh')) + '"]';
    var expand3 = attAnyHid(s); attHid(s, !expand3); attHIcon(hw, expand3);
    return;
  }
  var tr = e.target.closest('tr.att-grp'); if (!tr) return;
  toggleAttendEmp(tr);
});
function cssEsc(s){ return (s || '').replace(/"/g, '\\"'); }
function toggleAttendEmp(row){
  var P = attendPayload;
  var maj = row.getAttribute('data-major'), reg = row.getAttribute('data-region'), w = row.getAttribute('data-wh'), g = row.getAttribute('data-group');
  var k = maj + '|' + reg + '|' + w + '|' + g;
  if (row.dataset.expanded === 'true'){ collapseAttendEmp(row); return; }
  var emps = attEmpIdx[k] || [];
  var heads = P.empHeaders || [];
  var html;
  if (emps.length) {
    var thead = '<tr>' + heads.map(function(h){ return '<th>' + esc(h) + '</th>'; }).join('') + '</tr>';
    var body = emps.map(function(e){ return '<tr>' + e.slice(0, heads.length).map(function(v){ return '<td>' + esc(v == null ? '' : v) + '</td>'; }).join('') + '</tr>'; }).join('');
    html = '<tr class="emp-subrow"><td colspan="7"><table class="emp-table"><thead>' + thead + '</thead><tbody>' + body + '</tbody></table></td></tr>';
  } else {
    html = '<tr class="emp-subrow"><td colspan="7" class="empty">该时间范围内该组无未及时确认记录</td></tr>';
  }
  row.insertAdjacentHTML('afterend', html);
  row.dataset.expanded = 'true';
  var ec = row.querySelector('.emp-count');
  if (ec) ec.textContent = emps.length ? '（点击收起，当前范围 ' + emps.length + ' 条）' : '（未及时确认 0 条，点击展开）';
}
function collapseAttendEmp(row){
  var nxt = row.nextElementSibling;
  while (nxt && nxt.classList.contains('emp-subrow')){ var t = nxt; nxt = nxt.nextElementSibling; t.remove(); }
  row.dataset.expanded = 'false';
  var gk = row.getAttribute('data-major') + '|' + row.getAttribute('data-region') + '|' + row.getAttribute('data-wh') + '|' + row.getAttribute('data-group');
  var cnt = (attEmpIdx[gk] || []).length;
  var ec = row.querySelector('.emp-count'); if (ec) ec.textContent = cnt ? '（未及时确认 ' + cnt + ' 条，点击展开）' : '';
}
// 日期控制
function setModeAttend(m){
  attendMode = m;
  if (typeof syncModeBtns === 'function') syncModeBtns(m);
  if (m === 'week' && !attendWeekSel){ var wk = weeksOf(attendPayload.days); attendWeekSel = wk.length ? wk[wk.length - 1][0] : ''; }
  if (m === 'day' && !attendDayStart){ attendDayStart = attendDayEnd = attendPayload.days[attendPayload.days.length - 1] || ''; }
  renderAttend();
}
function stepAttend(dir){
  var AD = attendPayload.days;
  if (attendMode === 'month'){
    var i = attendPayload.months.indexOf(attendSel);
    i = Math.min(attendPayload.months.length - 1, Math.max(0, i + dir));
    attendSel = attendPayload.months[i];
  } else if (attendMode === 'week'){
    var wk = weeksOf(AD);
    var j = wk.findIndex(function(w){ return w[0] === attendWeekSel; });
    if (j < 0) attendWeekSel = wk.length ? wk[wk.length - 1][0] : '';
    else { j = Math.min(wk.length - 1, Math.max(0, j + dir)); attendWeekSel = wk[j][0]; }
  } else {
    var j = AD.indexOf(attendDayStart || AD[0]);
    j = Math.min(AD.length - 1, Math.max(0, j + dir));
    attendDayStart = attendDayEnd = AD[j];
  }
  renderAttend();
}
function updateAttendDateLabel(){
  var el = document.getElementById('attDateLabel'); if (el) el.textContent = '';
  var pk = document.getElementById('btnPicker'); if (!pk) return;
  var AD = attendPayload.days;
  var lbl;
  if (attendMode === 'month'){ lbl = monthLabel(attendSel); }
  else if (attendMode === 'week'){ lbl = weekLabel(attendWeekSel, addDaysStr(attendWeekSel, 6)); }
  else { lbl = dayLabel(attendDayStart || AD[0], true) + (attendDayStart !== attendDayEnd ? ' ~ ' + dayLabel(attendDayEnd, true) : ''); }
  pk.textContent = lbl;
}
function ddHide(id){ var e = document.getElementById(id); if (e) e.classList.add('hidden'); }
// 用 DOM 构建下拉项并绑定事件，避免内联 onclick 的引号转义问题
function ddItem(label, fn){
  var el = document.createElement('div');
  el.className = 'dd-item';
  el.textContent = label;
  el.addEventListener('click', fn);
  return el;
}
function toggleAttendDropdownShared(e){
  if (e) e.stopPropagation();
  var dd = document.getElementById('dropdown');
  if (!dd) return;
  if (!dd.classList.contains('hidden')){ dd.classList.add('hidden'); return; }
  var AD = attendPayload.days;
  dd.innerHTML = '';
  if (attendMode === 'month'){
    dd.appendChild(ddItem('按月', function(){ attendSel = attendPayload.months[attendPayload.months.length - 1]; setModeAttend('month'); ddHide('dropdown'); }));
    attendPayload.months.forEach(function(m){ dd.appendChild(ddItem(monthLabel(m), function(){ attendSel = m; setModeAttend('month'); ddHide('dropdown'); })); });
  } else if (attendMode === 'week'){
    var wk = weeksOf(AD);
    if (!wk.length) dd.appendChild(ddItem('（无数据）', function(){ ddHide('dropdown'); }));
    wk.forEach(function(w){ dd.appendChild(ddItem(weekLabel(w[0], w[1]), function(){ attendWeekSel = w[0]; setModeAttend('week'); ddHide('dropdown'); })); });
  } else {
    AD.forEach(function(d){ dd.appendChild(ddItem(dayLabel(d, true), function(){ attendDayStart = attendDayEnd = d; setModeAttend('day'); ddHide('dropdown'); })); });
  }
  dd.classList.remove('hidden');
}
function toggleAttendRegionDropdown(e){
  if (e) e.stopPropagation();
  var dd = document.getElementById('regionDropdown');
  if (!dd) return;
  if (!dd.classList.contains('hidden')){ dd.classList.add('hidden'); return; }
  var grid = document.getElementById('rpGrid'); if (!grid) return;
  // 与补签率视图同款网格式区域面板：大区列 + 区域项（点击后筛选劳务工表格）
  var regMap = {};
  attendPayload.days.forEach(function(d){
    var day = attendPayload.data[d]; if (!day) return;
    (day.detail || []).forEach(function(r){
      if (!regMap[r.major]) regMap[r.major] = {};
      regMap[r.major][r.region] = true;
    });
  });
  var order = ['美洲区','欧洲区','亚太区'];
  var roD = attendPayload.regionOrder || {};
  var html = '<div class="rd-header">FBU 交付前台 <small>全球大区总览</small></div><div class="rd-body">';
  order.forEach(function(major){
    var regs = Object.keys(regMap[major] || {}).sort(function(a, b){ var d = roIdx(roD, major, a) - roIdx(roD, major, b); return d !== 0 ? d : (a < b ? -1 : a > b ? 1 : 0); });
    html += '<div class="rd-col">';
    html += '<div class="rd-col-header"><div class="rd-col-title" data-major="'+attrEsc(major)+'" onclick="pickAttMajor(this)">'+esc(major)+'</div><div class="rd-col-tag">大区</div></div>';
    html += '<div class="rd-list">';
    if (regs.length){
      regs.forEach(function(r){
        html += '<div class="rd-region"><div class="rd-region-title" data-major="'+attrEsc(major)+'" data-region="'+attrEsc(r)+'" onclick="pickAttRegion(this)">'+esc(r)+'</div></div>';
      });
    } else {
      html += '<div class="rd-empty">无区域数据</div>';
    }
    html += '</div></div>';
  });
  html += '</div>';
  grid.innerHTML = html;
  dd.classList.remove('hidden');
}
function pickAttMajor(el){
  attendRegionFilter = el.dataset.major;
  renderAttend();
  ddHide('regionDropdown'); ddHide('dropdown');
}
function pickAttRegion(el){
  attendRegionFilter = el.dataset.major + '|' + el.dataset.region;
  renderAttend();
  ddHide('regionDropdown'); ddHide('dropdown');
}
function updateAttendRegionBtn(){
  var btn = document.getElementById('btnRegion'); if (!btn) return;
  if (!attendRegionFilter){ btn.textContent = 'FBU交付前台'; return; }
  var p = attendRegionFilter.split('|');
  btn.textContent = p[1] ? p[1] : p[0];
}
// 下拉容器内点击不冒泡（由主脚本的共享控件绑定负责，这里无需重复绑定）
// 板块导航
var attendSectionTabs = document.getElementById('attendSectionTabs');
var attendTabBtns = attendSectionTabs ? Array.from(attendSectionTabs.querySelectorAll('button')) : [];
var attendSectionIds = ['attSecMajor','attSecDetail','attSecWh','attSecGrp','attSecTop'];
attendSectionTabs.addEventListener('click', function(e){
  var b = e.target.closest('button'); if (!b) return;
  var id = b.dataset.target;
  var el = document.getElementById(id); if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
  attendTabBtns.forEach(function(x){ x.classList.toggle('active', x === b); });
});
renderAttend();
</script>
</div>
"""
attend_block = attend_block.replace('{attend_json}', attend_json)
html = html.replace('</body>', attend_block + '\n</body>')

with open(OUT_HTML, 'w', encoding='utf-8') as fh:
    fh.write(html)
print("HTML 已生成:", OUT_HTML)
print("月份:", months)
print("日期数:", len(days))
