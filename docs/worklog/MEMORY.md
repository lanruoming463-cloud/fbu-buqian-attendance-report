
## 补签/考勤报表口径（2026-10-10）
- 正式工考勤确认及时率：捷克区特殊口径——首打卡与末打卡均为空的缺卡记录视为及时确认，不计入未及时（_build_formal_recs 白名单，FORMAL_NOTE 已注明）。
- 主体报表数据范围 2026-06/07/10；8-9月仅在独立 T+1 日更看板（T1_DATA 不在 gen_buqian_stats.py）。
- 部署链路：_deploy3.py（妙搭 app_17cg3t4mvjm + 自动 _github_sync.py 同步公开仓库 lanruoming463-cloud/fbu-buqian-attendance-report）。
