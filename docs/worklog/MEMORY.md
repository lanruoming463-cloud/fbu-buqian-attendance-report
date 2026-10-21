
## 补签/考勤报表口径（2026-10-10）
- 正式工考勤确认及时率：捷克区特殊口径——首打卡与末打卡均为空的缺卡记录视为及时确认，不计入未及时（_build_formal_recs 白名单，FORMAL_NOTE 已注明）。
- 主体报表数据范围 2026-06/07/10；8-9月仅在独立 T+1 日更看板（T1_DATA 不在 gen_buqian_stats.py）。
- 部署链路：_deploy3.py（妙搭 app_17cg3t4mvjm + 自动 _github_sync.py 同步公开仓库 lanruoming463-cloud/fbu-buqian-attendance-report）。
- T+1 增量注入模式（10.15/10.16-10.18/10.19 实证）：_inject_*.py 只读桌面日更 xlsx，复刻口径合并进已发布 HTML——formalAttPayload 需 day 块 + merge_full_block 累加 2026-10 月块；attendPayload 仅 day 块（月视图前端聚合）。数据范围已扩至 10.1–10.19（release 7698942997014695153）。
- 正式工补签率：西班牙区「补签事由=其他」1,673 条按客观原因整体剔除（gen_buqian_stats.py 已固化，总计 15,012→13,339）。

## GitHub 同步机制（2026-10-10 修订）
- _github_sync.py 同步范围：核心脚本(gen_buqian_stats/_deploy3/_github_sync)、README/.gitignore、无头探针(_probe*)、口径诊断脚本(_diag/_check/_explore)、发布说明(*发布说明*.md)、docs/ 递归、T+1看板核心脚本、报表产物(HTML/xlsx)、attend_acc_data.json。
- 日志路径分离：.workbuddy/memory/*.md 存 docs/worklog/；docs/devlog/*.md 为真实开发日志，两者同名不可混放(曾因去重被记忆日志覆盖，已修)。
- 仓库公开(lanruoming463-cloud/fbu-buqian-attendance-report)；PAT 存 .github_token(gitignored)；发布联动 + 每日22:30兜底。
