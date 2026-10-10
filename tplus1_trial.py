# -*- coding: utf-8 -*-
"""
T+1 考勤确认及时率 试算（依据《全球T+1考勤确认及时性管理规范》）
- OEHR(正式工)已确认 = 考勤状态正常 + 异常且迟到/早退（+ 捷克区特例：异常且缺首打卡和末打卡 也算已确认）
- 及时率(按天) = 已确认条数 / 应确认条数(总条数)
- 增量更新：tplus1_state.json 记录每日出稿状态；已冻结日(T+2工作日10:00深圳后)不再重算
用法: python tplus1_trial.py [--force]
"""
import openpyxl, json, os, re, sys, datetime as dt, warnings
from collections import defaultdict
warnings.filterwarnings("ignore")

XLSX = r"D:\Documents\Downloads\正式工-8月.xlsx"
STATE_F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tplus1_state.json")
TZ = dt.timezone(dt.timedelta(hours=8))  # 深圳时间
SUF = re.compile(r"(HRBP部|行政部|渠道部|交付管理部|商务部|财务部)$")
MAJORS = ("欧洲区", "美洲区", "亚太区")
FORCE = "--force" in sys.argv

# 列索引（正式工-8月.xlsx, 161列核算导出）
C_DATE, C_NAME, C_EMP, C_DIV, C_L3, C_L4, C_L5, C_L6 = 0, 1, 2, 4, 6, 7, 8, 9
C_FIRST, C_LAST, C_LATE, C_EARLY, C_STATUS = 28, 29, 38, 40, 134


def freeze_at(d):
    """T+2工作日 10:00 深圳时间（周末顺延；法定节假日未建模）"""
    t = d
    for _ in range(2):
        t += dt.timedelta(days=1)
        while t.weekday() >= 5:
            t += dt.timedelta(days=1)
    return dt.datetime.combine(t, dt.time(10, 0), TZ)


def major_of(l3, l4):
    if l3 in MAJORS:
        return l3
    if l3 == "FBU HRBP Dept.":
        return "FBU HRBP Dept."
    core = SUF.sub("", l4)
    if core in MAJORS:
        return core
    for m in MAJORS:
        if l4.startswith(m):
            return m
    return "其他"


def s(v):
    return str(v).strip() if v is not None else ""


def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def load_state():
    if os.path.exists(STATE_F):
        with open(STATE_F, encoding="utf-8") as f:
            return json.load(f)
    return {"oehr": {}, "otws": {}}


def save_state(st):
    with open(STATE_F, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def main():
    now = dt.datetime.now(TZ)
    print(f"[运行时刻] {now:%Y-%m-%d %H:%M:%S 深圳}  force={FORCE}")
    state = load_state()

    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    next(it)  # header

    per_day = defaultdict(lambda: [0, 0, 0, 0])  # total, confirmed, confirmed_no_cz, untimely
    per_major = defaultdict(lambda: [0, 0, 0])
    ex = {"财务部": 0, "四级空": 0, "HRBP美洲支持": 0}
    for r in it:
        d = r[C_DATE]
        if d is None:
            continue
        dstr = d.strftime("%Y-%m-%d") if isinstance(d, dt.datetime) else str(d)[:10].replace("/", "-")
        l3, l4 = s(r[C_L3]), s(r[C_L4])
        if "财务部" in l3 or "财务部" in l4:
            ex["财务部"] += 1
            continue
        if l3 == "FBU HRBP Dept.":
            if l4 == "美洲支持HRBP组":
                ex["HRBP美洲支持"] += 1
                continue
        elif not l4:
            ex["四级空"] += 1
            continue
        status = s(r[C_STATUS])
        abn = status == "异常"
        late, early = num(r[C_LATE]) > 0, num(r[C_EARLY]) > 0
        czech = "捷克" in s(r[C_DIV])
        miss_both = s(r[C_FIRST]) == "" and s(r[C_LAST]) == ""
        confirmed = (not abn) or late or early or (czech and miss_both)
        # 统一存四元组: total / confirmed / confirmed_无捷克 / untimely
        a = per_day[dstr]
        a[0] += 1
        if confirmed:
            a[1] += 1
        else:
            a[3] += 1
        if (not abn) or late or early:
            a[2] += 1
        mj = major_of(l3, l4)
        pm = per_major[mj]
        pm[0] += 1
        if confirmed:
            pm[1] += 1
        else:
            pm[2] += 1
    wb.close()

    print(f"[剔除] {ex}  合计剔除 {sum(ex.values())}")
    print()
    print("=== 按天（规范口径）===")
    print(f"{'日期':<12}{'总条数':>8}{'已确认':>8}{'未确认':>8}{'及时率':>9}  来源")
    rows_out = {}
    for d in sorted(per_day):
        total, conf, conf_ncz, untimely = per_day[d]
        frozen = now >= freeze_at(dt.date.fromisoformat(dstr))
        rec = state["oehr"].get(d)
        if rec and frozen and not FORCE:
            src = "冻结跳过(用已出稿)"
            total, conf, conf_ncz, untimely = rec["total"], rec["confirmed"], rec["confirmed_ncz"], rec["untimely"]
        else:
            src = "本次计算" + ("" if frozen else "(未冻结可重算)")
            state["oehr"][d] = {
                "total": total, "confirmed": conf, "confirmed_ncz": conf_ncz, "untimely": untimely,
                "rate": round(conf / total * 100, 2) if total else None,
                "frozen": frozen, "calculated_at": now.isoformat(timespec="seconds"),
            }
        rate = f"{conf/total*100:.2f}%" if total else "-"
        print(f"{d:<12}{total:>8}{conf:>8}{untimely:>8}{rate:>9}  {src}")
        rows_out[d] = (total, conf, untimely)

    save_state(state)
    print()
    T = sum(v[0] for v in per_day.values())
    Cf = sum(v[1] for v in per_day.values())
    Cn = sum(v[2] for v in per_day.values())
    print(f"[8月月度] 总条数={T}  已确认(含捷克特例)={Cf}  未确认={T-Cf}  及时率={Cf/T*100:.2f}%")
    print(f"[8月月度] 若无捷克特例: 已确认={Cn}  及时率={Cn/T*100:.2f}%  (捷克特例影响 {(Cf-Cn)/T*100:+.2f}pp)")
    for mj, (t, c, _) in sorted(per_major.items(), key=lambda x: -x[1][0]):
        print(f"  - {mj:<16} 总={t:>6} 已确认={c:>6} 及时率={c/t*100:.2f}%")
    print(f"[状态文件] {STATE_F} 已保存（{len(state['oehr'])} 天在册）")


if __name__ == "__main__":
    main()
