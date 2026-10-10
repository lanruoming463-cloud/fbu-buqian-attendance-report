
## 补签/考勤报表口径（2026-10-10）
- 正式工考勤确认及时率：捷克区特殊口径——首打卡与末打卡均为空的缺卡记录视为及时确认，不计入未及时（_build_formal_recs 白名单，FORMAL_NOTE 已注明）。
- 主体报表数据范围 2026-06/07/10；8-9月仅在独立 T+1 日更看板（T1_DATA 不在 gen_buqian_stats.py）。
- 部署链路：_deploy3.py（妙搭 app_17cg3t4mvjm + 自动 _github_sync.py 同步公开仓库 lanruoming463-cloud/fbu-buqian-attendance-report）。

## GitHub 同步机制（2026-10-10 修订）
- _github_sync.py 同步范围：核心脚本(gen_buqian_stats/_deploy3/_github_sync)、README/.gitignore、无头探针(_probe*)、口径诊断脚本(_diag/_check/_explore)、发布说明(*发布说明*.md)、docs/ 递归、T+1看板核心脚本、报表产物(HTML/xlsx)、attend_acc_data.json。
- 日志路径分离：.workbuddy/memory/*.md 存 docs/worklog/；docs/devlog/*.md 为真实开发日志，两者同名不可混放(曾因去重被记忆日志覆盖，已修)。
- 仓库公开(lanruoming463-cloud/fbu-buqian-attendance-report)；PAT 存 .github_token(gitignored)；发布联动 + 每日22:30兜底。
