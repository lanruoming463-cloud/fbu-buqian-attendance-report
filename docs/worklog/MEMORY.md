# 补签/考勤报表项目长期记忆（精简版 2026-11-19）

## 基础
- 主产物：单体 HTML `补签流程_补签统计.html`（约 11.7MB）。payload：`formalAttPayload`（正式工，有日块+月块）、`attendPayload`（劳务工，仅日块，前端聚合成月）、`formalPayload`/`laborPayload`（补签率）。
- 部署：`_deploy3.py`（妙搭 app_17cg3t4mvjm；自动触发 `_github_sync.py` 同步公开仓库 lanruoming463-cloud/fbu-buqian-attendance-report）。每次改动须更新 `COMMIT_MSG`（当前 V25.11 待部署）。
- 主体报表数据范围 2026-06/07/10；8-9月仅在独立 T+1 看板。T+1 日块已注入至 2026-11-16。
- 体积红线：`att_excel` 不得进 HTML payload（曾致 54MB），gen 脚本已在追加 Excel 后 pop。

## 口径机制（ surgically 修改已发布 HTML，勿全量重跑 gen）
### 正式工剔除/白名单（语义严格区分）
1. `FORMAL_ATT_DATE_WHITELIST`：异常改正常/计及时，**保留 total**，abnormal−1/untimely−1/normal+1，empIndex 删行。当前含原1+法国19+西班牙3+意大利3+11月手动若干+zt0022754/11-13、zt0023345/11-16（gen 8 条/_inject_1025 33 条口径，持续累加）。
2. `FORMAL_ATT_EXCLUDE_DATES`：整条从分母剔除（total/normal/abnormal/untimely 全减）。含 zt0021853/11-13、11-16。
3. `FORMAL_ATT_LEAVE_FROM`：离职生效日起整条剔除，日期 `>=` 生效日。含 zt0023023→2026-11-16。
4. `FORMAL_ATT_EXCLUDE_EMPS`（全期，zt0022056）/ `FORMAL_ATT_EXCLUDE_OCT`（zt0021903）/ `FORMAL_ATT_WH_EXCL`（加拿大区3仓 11-01~11-08 按仓白名单）。
- 捷克自动豁免仅限 `region in ('捷克区','捷克区HRBP部')` 且异常备注=`缺少首打卡和末打卡`；**用户明确：其他区域不适用**。
- 「上级当天休假豁免」仅10月，据休假流程+花名册映射，扣 untimely 不改 total。

### 劳务工
- `LABOR_ATT_EXCLUDE_DATES`：整条剔除分母（6 对法国区，2026-10）。
- `LABOR_ATT_DATE_WHITELIST`：保留 yqr、sjqr=yqr、unconfirmed=0、移出未确认名单。含 SAV056776/11-10 + 德国区杜塞尔多夫20号仓GOFO组5人/11-16（DE079640/DE086340/DE079490/DE079487/DE086939，下班未打卡不算异常；这5人11-17也有同类异常，用户只标11-16故未动）。
- ⚠️致命坑：`attendPayload` 含 6/7/8/9 月共 61 个历史日块，**任何全量重建都会误删**。只能外科手术式修正：保历史日块/empIndex 不动，仅替换受影响日块、增量注入新日、按 delta 调 Top。
- LA19（洛杉矶19号仓）夜班：专用文件 `exclude_la19=False`，其他文件 `True`；并非全确认，按实际 yqr−sjqr 处理。专用文件须 `read_only=False`。

## 补签率（考勤为基）
- 分母=考勤记录数，分子=补签完成且非客观原因。仅按月（days=[]，隐藏日/周）；图例宽度=补签率。
- 劳务工剔除：入职当天/初次报道、西班牙区+其他、日本区+提前打卡、备注客观因素。6/7/8 月旧口径（仅按修改原因）。
- ⚠️补签率板块严禁 gen 全量重跑（会抹掉 T+1 日块）；用 `_inject_buqian10.py` 并 `_norm_block` 比对保护 6-9 月块，右→左 reverse 替换两个 const。

## 异常表每日机制
- `_scrape_exception_table.py` + `_apply_exceptions.py`（幂等，退出码 0=需部署/2=跳过），每日 09:30 自动化 id ca859c49。仓库级条目（无工号仅仓库+日期）=整仓当天所有人计及时，从日块 warehouse 取 `we`。

## 关键教训
- 全量重跑 gen 会丢 T+1 日块，重跑后必须补齐其后所有注入文件；全量重跑后须手动 cp `_injected_*.html` 覆盖主 HTML。
- 修正脚本须校验：月块=日块和、`timely==total−untimely`、6/7/8/9/10 月零改动、empIndex 无残留。
- 历史详细日志见 `docs/devlog/` 与各日 `*.md`。
