# -*- coding: utf-8 -*-
"""抓取飞书「考勤确认及时率异常表」(wiki sheet)，解析为修正清单 att_exceptions.json。

表结构(两子表):
  002f25 = 10月-正式工-剔除情况
  OSWWWl = 10月-劳务工-剔除情况
列: 考勤日期 | 员工 | 工号 | 仓库 | 组别 | 剔除原因

动作分类:
  EXCLUDE (剔除该天考勤数据): 剔除原因含"无故缺勤/没来上班/旷工/未到岗/未出勤/没上班"
  CONFIRM (算该天考勤及时确认): 其余非空原因(未及时审批有原因/待确认/改假/infringement等)
  空原因: 跳过

考勤日期支持单日与区间(如 2026/09/28- 2026/10/13 → 展开为每日)。
输出 att_exceptions.json: { formal: [...], labor: [...], scraped_at, source }
每条: { gong, name, wh, group, date, action, reason }
"""
import json, os, re, subprocess, datetime
from collections import defaultdict

WS = r"C:\Users\zt25337\WorkBuddy\2026-08-20-09-25-58"
LARK = r"C:\Users\zt25337\.workbuddy\binaries\node\cli-connector-packages\node_modules\@larksuite\cli\bin\lark-cli.exe"
URL = "https://ztn.larkenterprise.com/wiki/P6ZAwuZweihDHDkBhONcLpLsnAb?sheet=002f25"
OUT = os.path.join(WS, "att_exceptions.json")

SHEETS = {
    "formal": ("002f25", "10月-正式工-剔除情况"),
    "labor": ("OSWWWl", "10月-劳务工-剔除情况"),
}

# 表内繁简混用，故每个关键词都列繁/简两版
EXCLUDE_KW = ["无故缺勤", "無故缺勤", "没来上班", "沒来上班", "旷工",
              "未到岗", "未出勤", "没上班", "沒上班", "沒開門", "未开门", "没开门"]

def read_sheet(sheet_id):
    cmd = [LARK, "sheets", "+csv-get", "--url", URL, "--sheet-id", sheet_id,
           "--range", "A1:F210", "--as", "user", "--format", "json"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    d = json.loads(p.stdout)
    if not d.get("ok"):
        raise RuntimeError("读取失败: " + p.stdout[:300])
    csv = d["data"]["annotated_csv"]
    rows = []
    for line in csv.split("\n"):
        line = line.strip()
        if not line.startswith("[row="):
            continue
        # 去 [row=N] 前缀
        body = line[line.index("]")+1:]
        cols = body.split(",")
        rows.append([c.strip() for c in cols])
    return rows

def parse_dates(s):
    s = (s or "").strip()
    if not s:
        return []
    # 区间: 含 '-' 且两侧像日期
    if "-" in s:
        parts = re.split(r"\s*-\s*", s)
        if len(parts) == 2:
            a = parse_one(parts[0]); b = parse_one(parts[1])
            if a and b:
                out = []
                cur = a
                while cur <= b:
                    out.append(cur.strftime("%Y-%m-%d"))
                    cur += datetime.timedelta(days=1)
                return out
    one = parse_one(s)
    return [one.strftime("%Y-%m-%d")] if one else []

def parse_one(s):
    s = s.strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        try:
            return datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None

def classify(reason):
    r = (reason or "").strip()
    if not r:
        return None
    for kw in EXCLUDE_KW:
        if kw in r:
            return "EXCLUDE"
    return "CONFIRM"

def main():
    result = {"formal": [], "labor": [], "scraped_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": URL}
    stats = defaultdict(int)
    ambiguous = []
    for kind, (sid, title) in SHEETS.items():
        print("读取子表:", title, "(%s)" % sid)
        rows = read_sheet(sid)
        # 跳过表头行(第1行)
        for r in rows[1:]:
            if len(r) < 6:
                r = r + [""]*(6-len(r))
            date_raw, name, gong, wh, group, reason = r[0], r[1], r[2], r[3], r[4], r[5]
            gong = gong.strip()
            if not gong and not date_raw.strip() and not name.strip():
                continue  # 空行
            dates = parse_dates(date_raw)
            action = classify(reason)
            if action is None:
                # 空原因 → 跳过但记录
                if gong or date_raw.strip():
                    print("  ⚠ 空原因跳过:", date_raw, gong, reason)
                continue
            if not dates:
                print("  ⚠ 无法解析日期跳过:", date_raw, gong)
                continue
            for d in dates:
                result[kind].append({
                    "gong": gong, "name": name.strip(), "wh": wh.strip(),
                    "group": group.strip(), "date": d, "action": action, "reason": reason.strip()
                })
                stats[(kind, action)] += 1
            if action == "CONFIRM" and not re.search(r"审批|原因|待|确认|假|infringement|回传|工时|改", reason, re.I):
                ambiguous.append((kind, date_raw, gong, reason))
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n=== 抓取统计 ===")
    print("  正式工 EXCLUDE/CONFIRM:", stats[("formal","EXCLUDE")], "/", stats[("formal","CONFIRM")])
    print("  劳务工 EXCLUDE/CONFIRM:", stats[("labor","EXCLUDE")], "/", stats[("labor","CONFIRM")])
    print("  总条目:", len(result["formal"]) + len(result["labor"]))
    if ambiguous:
        print("  ⚠ 归类为CONFIRM但原因无明确信号(供复核):")
        for a in ambiguous: print("    ", a)
    print("  写出 ->", OUT)
    # 打印样例
    print("\n=== 正式工样例(前8) ===")
    for e in result["formal"][:8]:
        print("  ", e["date"], e["gong"], e["action"], "|", e["reason"][:30])
    print("=== 劳务工样例(前8) ===")
    for e in result["labor"][:8]:
        print("  ", e["date"], e["gong"], e["action"], "|", e["reason"][:30])

if __name__ == "__main__":
    main()
