
## 补签/考勤报表口径（2026-10-10）
- 正式工考勤确认及时率：捷克区特殊口径——首打卡与末打卡均为空的缺卡记录视为及时确认，不计入未及时（_build_formal_recs 白名单，FORMAL_NOTE 已注明）。
- 主体报表数据范围 2026-06/07/10；8-9月仅在独立 T+1 日更看板（T1_DATA 不在 gen_buqian_stats.py）。
- 部署链路：_deploy3.py（妙搭 app_17cg3t4mvjm + 自动 _github_sync.py 同步公开仓库 lanruoming463-cloud/fbu-buqian-attendance-report）。
- T+1 增量注入模式（10.15/10.16-10.18/10.19 实证）：_inject_*.py 只读桌面日更 xlsx，复刻口径合并进已发布 HTML——formalAttPayload 需 day 块 + merge_full_block 累加 2026-10 月块；attendPayload 仅 day 块（月视图前端聚合）。数据范围已扩至 10.1–10.19（release 7698942997014695153）。
- 正式工补签率：西班牙区「补签事由=其他」1,673 条按客观原因整体剔除（gen_buqian_stats.py 已固化，总计 15,012→13,339）。
- 正式工补签率板块（2026-10-21 起）改为**考勤为基**口径：分母=范围内考勤总记录数（人日）、分子=JOIN 补签流程已完成并剔除西班牙"其他"+客观原因；数据由 `_formal_attend_rate.json`（`_gen_formal_attend_rate.py` 产出，已校验）驱动，HTML 与 Excel 6 个补签率 sheet 同口径。KPI=考勤记录总数/已补签数/补签率；仅按月呈现（days=[]，按天/按周隐藏）；Top10 按补签天数>3 取 7 列；组下明细 5 列。教训：render 行模板中 ingCell/ydkCell/rateCell 已返回完整 <td>，外层不可再包 <td>；colspan C 已改为动态。release 7698990216392854805。
- 图例规范（2026-10-21）：补签率两板块表头=「补签率图例」且图例条宽度=补签率（barW=rate，非占总体比）；及时率板块=「及时确认率图例」。法国区导出脚本 `_export_france.py`（未及时确认10月/补签Top10 9月，4 sheet）可复用。最新 release 7699025157558553848。
- 劳务工补签率（2026-10-21 起）改为**考勤为基**口径，与正式工完全一致：分母=考勤记录总数（人日=全量考勤行），分子=首/末打卡补签时间非空 且 非客观因素（is_top_exclude 检查 修改原因/备注）；补签率两板块均移除占总体比列、移除应打卡合计/未完成列，表头统一 5 列=[大区,考勤记录总数,已补签数,补签率,补签率图例]；劳务工也仅按月（days_l=[]，隐藏日/周按钮）。核心函数 `agg_period_labor_att`（与 _att_block 同构）；Excel 新增 6 个「劳务工_*」补签率 sheet。aggRange JS 补签率=已完成/total。探针注意：renderAttend 未定义系时序误报（attend script 解析需 ~1s）。release 7699063854717799723。
- **体积红线**：att_excel（Excel 专用全量明细）不得随 payload 序列化进 HTML——曾致 54MB 超妙搭发布上限；gen_buqian_stats.py 已在 Excel 追加后 pop('att_excel')，HTML 10.36MB。修复发布 release 7699065068139334920。
- **日期组件规则（2026-10-21）**：考勤确认及时率（正式工 gen 视图/劳务工 attend 视图）=按天/按周/按月 全组件；仅补签率两板块（正式工/劳务工）仅按月隐藏日/周。关键点：showCell 切换视图时必须恢复 btnDay/btnWeek 的 display（showAtt/showGen 分支已固化）。release 7699069573207018790。
- **T+1 注入回退教训（2026-10-22）**：全量重跑 gen_buqian_stats.py 会丢失已注入的 T+1 日块（源文件仅到注入时点）——重跑后必须重新注入其后所有 T+1 文件。`_inject_1020.py` 已支持多文件列表循环（FORMAL_FILES/LABOR_FILES），可直接复用为补齐脚本；数据范围现 10.1–10.20（release 7699310530578992373）。
- **劳务工考勤确认率「指定日期剔除」机制（2026-10-26 固化）**：`LABOR_ATT_EXCLUDE_DATES`（工号,日期 集合），作用在劳务工 attend 视图——被剔除者该日考勤不计入考勤确认及时率分母、也不计入未及时确认名单。已累计 6 对，全部法国区劳务工：FR083014/10-19、FR091493/10-18、FR086719/10-14、FR092791/10-14、FR093742/10-20、FR092978/10-21。真源需同步改 4 文件：gen_buqian_stats.py / _inject_1020.py / _inject_1021.py / _export_france.py（A2 循环加 `if (g,d) in LABOR_ATT_EXCLUDE_DATES: continue`）。已发布 HTML 用 _patch_labor_fr_excl.py 外科手术式重建 affect 日块(attendPayload 仅 day 块)+清理 empIndex；月聚合前端实时算。release 7700787091309006078。
- **正式工考勤确认率「全期剔除」机制（2026-10-27 固化）**：`FORMAL_ATT_EXCLUDE_EMPS`（工号集合，全期），作用在正式工 gen 视图——被剔除员工全部考勤不计入及时率分母及未及时确认名单（empIndex/topEmpIndex 同步清理）。首个成员 zt0022056（张剑卫/David，美洲区/萨凡纳区/卡派组），横跨 6/7/10 月。真源改 gen_buqian_stats.py（_build_formal_recs 加 `continue`）+ _inject_1021.py/_inject_1022.py（build_formal_recs 加 `continue`）。已发布 HTML 用 _patch_formal_excl_zt22056.py 减法式修正（源文件算每日各维度贡献扣减日块+月块+清理 empIndex/top）；注意源文件 `考勤日期` 为斜杠格式需 pd.to_datetime 归一化。release 7701170605073108256。区别于仅10月的 `FORMAL_ATT_EXCLUDE_OCT`（zt0021903 离职）。

## GitHub 同步机制（2026-10-10 修订）
- _github_sync.py 同步范围：核心脚本(gen_buqian_stats/_deploy3/_github_sync)、README/.gitignore、无头探针(_probe*)、口径诊断脚本(_diag/_check/_explore)、发布说明(*发布说明*.md)、docs/ 递归、T+1看板核心脚本、报表产物(HTML/xlsx)、attend_acc_data.json。
- 日志路径分离：.workbuddy/memory/*.md 存 docs/worklog/；docs/devlog/*.md 为真实开发日志，两者同名不可混放(曾因去重被记忆日志覆盖，已修)。
- 仓库公开(lanruoming463-cloud/fbu-buqian-attendance-report)；PAT 存 .github_token(gitignored)；发布联动 + 每日22:30兜底。

## 劳务工补签剔除规则（2026-10-22 更新）
- 新规则（参考正式工+区域特例）：补签原因=入职当天(含初次报道/首次报道)全剔除；西班牙区+其他剔除；日本区+提前打卡剔除；其余按备注客观因素(is_top_exclude)剔除。补签原因只存在于《劳务工-补签记录-*.xls》(OTWS-打卡数据,实为xlsx)——考勤表异常原因/修改原因不含补签原因。
- 现状：仅 2026-09 用新口径（gen_buqian_stats.py 内 9月覆盖块）；6/7/8月暂无补签记录文件维持旧口径，月度趋势有台阶（西班牙区 8月44.0%→9月1.6%）。补齐 6-8月文件后在 gen 里把 BUQIAN_REC_LABOR 扩为月度映射即可统一。
- 匹配口径：(工号,打卡时间→考勤日期) 匹配考勤表 且该行首/末打卡补签时间非空；按(工号,考勤日期)去重=补签人日。全量重跑后须重跑 _inject_1020.py 并手动 cp _injected_1020.html 覆盖主 HTML（脚本不自动 cp）。release 7699377540092431604。
