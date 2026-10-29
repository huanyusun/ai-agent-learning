# 统一课程中心:实施记录与验收

> 本仓库是学习中心的独立仓(2026-10-29 从 huanyusun/fde-study 的学习模块迁出)。
> 文中提到的 Git 提交号(如 `7aea723`、`53112a6`)指上游 fde-study 仓库的历史,不在本仓库中。

执行计划:[统一课程中心与自动更新 Implementation Plan](docs/superpowers/plans/2026-10-28-learning-hub.md)。
本文件按任务记录改动、验证结果和遗留问题;状态只写已发生的事实。

## 执行状态总览

| 任务 | 状态 | 记录 |
|---|---|---|
| T01 结构化迁移与校验器 | 已完成(离线验证) | 见下 |
| T02 统一生成器与文档入口 | 已完成(离线验证 + 浏览器实测) | 见下 |
| T03 筛选、周计划与个人进度 | 已完成(离线验证 + 无头浏览器实测) | 见下 |
| T04 网络抓取和课程刷新 | 已完成(离线验证 + 真实网络检查) | 见下 |
| T05 候选课程发现 | 已完成(离线验证 + 真实网络发现) | 见下 |
| T06 更新报告与恢复文档 | 已完成(离线验证) | 见下 |
| T07 CI 与定时自动更新 | 已完成(本地实现与 YAML 校验;**在线调度未验证**) | 见下 |
| T08 整体验收与交接 | 已完成(验收记录见下;在线调度未验证) | 见下 |

在线调度(定时 Actions)**已在线验证**(2026-10-29,本仓库 GitHub Actions):workflow_dispatch 真实运行三次,refresh / discover / 提交 / 带租约推送 / PR 创建全部成功,PR #1 是第一份可审核更新;CI 在 Ubuntu + Python 3.11 干净环境通过。详见文末「在线调度验证」。

## 环境说明

- 工作树无 `.venv`,为本任务新建 `.venv`,仅安装 `pytest==9.1.1`(产品依赖未安装、未改动)。
- 测试命令:`.venv/bin/python -m pytest tests/learning_hub -q`(等效于计划中的 `python3 -m pytest`,系统 Python 无 pytest)。
- 用户原有未提交资料(README.md、AI学习路径与大纲.md、docs/superpowers/、learning/ 四个 Markdown)已先原样提交存档(commit `7aea723`),后续生成器接管时可从该提交恢复。

## T01 结构化迁移与校验器(2026-10-29)

**改动**

- 新增 `learning/data/catalog.json`:迁移 20 门课程(C01–C20)、8 个阶段(S00–S07,共 33 个 assignment)、18 周(W01–W18)、10 个研读入口(repo_links)。内容来自 `learning/courses.md`、`learning/README.md`、`learning/weekly-plan.md` 和 `AI学习路径与大纲.md`。
- 新增 `learning/data/sources.json`:两个官方目录来源(Hugging Face Learn、LangChain Academy),`course_rules` 初始为空。
- 新增 `learning/templates/weekly-note.md`:原周计划中的学习记录模板,正文未改。
- 新增 `tools/learning_hub/`(`__init__.py`、`catalog.py`、`__main__.py`):加载与校验器,CLI 先提供 `validate` 子命令。
- 新增 `tests/learning_hub/`(conftest.py、test_catalog.py):23 个离线测试。

**验证**

- 先写测试后实现:初跑确认 `tools.learning_hub` 模块缺失(红灯),实现后 23 项全部通过。
- 覆盖:重复课程/作业 ID、悬空课程引用(C99)、悬空周作业引用、缺周、缺阶段、阶段依赖成环(含自环)、未知前置阶段、非法 URL scheme、effort min>max、负数投入、非法 A/B 级别与日期格式、非法 kind/cost_status、repo_links 与周 repo_paths 指向不存在的仓库路径、catalog 中混入自动观测字段被拒。
- `python3 -m tools.learning_hub validate` 输出:`catalog 校验通过:课程 20、阶段 8、周 18。`

**迁移判断(供人工逐行核对)**

- 原表"本周交付与验收"为合并列:迁移时按分号拆为 `deliverables` 与 `acceptance` 两个字段;原文全部保留,拆分位置是解释性判断。
- 周内无明确验收条款时,`acceptance` 引用对应阶段的"学完要能完成"目标(标注"对齐阶段目标"),未新造标准。
- C06 在原目录标注"阶段 3/4/5":阶段 3 为 README 明确的选修(Unit 1、Unit 2.3);阶段 4/5 内容(Unit 3 Agentic RAG、观测评测加餐)按课程目录顺序映射,并在 `note`/`why` 中说明原 README 分阶段表未单列。
- C19/C20 原表无工时估算:`effort_hours` 记为 0–0 并注明"原目录未给出估算",未编造数字。
- cost_status 为人工判断:C01/C03/C04/C05/C06/C07/C08/C10/C19/C20 有"内容公开但账号/资源/算力另计"等说明,记为 `mixed`;C02/C09/C11 内容明确免费,记为 `free_content`;C12–C18 为 B 级、费用未核查,记为 `unknown`。
- B 级课程(C12–C18)的 403 背景(官方目录确认存在、详情页抓取 403)保留在各课程 `manual_review.note`,核查日期固定 2026-10-28。
- `learning/README.md` 的"如何开始/最少选课组合/课程之外仍需自行完成"与 `courses.md` 的"覆盖边界与选择依据"、`weekly-plan.md` 的综合项目二选一和 W1 关系说明属于整段文字,计划在 T02 由生成器模板承载,不在本任务范围。

**遗留问题**

- 无阻塞项。

## T02 统一生成器与文档入口(2026-10-29)

**改动**

- 新增 `tools/learning_hub/render.py`:`build_outputs`(确定性生成 4 个文件)、`write_outputs`(临时文件 + `os.replace` 原子写)、`check_outputs`(漂移比较)。整段人工策划文字(如何开始、最少选课组合、覆盖边界、综合项目二选一、与 W1 关系等)保存为 `CURATED_*` 常量,编辑入口集中。
- 新增 `learning/web/template.html`:页面结构与内嵌样式/逻辑源文件,仅含一个数据占位符;生成器强制占位符恰好出现一次。
- 生成 `learning/index.html`、`learning/README.md`、`learning/courses.md`、`learning/weekly-plan.md`(原人工版本已存档于提交 `7aea723`,可随时恢复)。
- `tools/learning_hub/__main__.py` 增加 `build` 与 `build --check`(退出码:一致 0 / 漂移 1)。
- 根 `README.md`:AI 学习路线一节补统一入口 `learning/index.html` 与维护命令。
- 新增 `tests/learning_hub/test_render.py`:12 个离线测试。

**验证**

- 先写测试后实现(初跑红灯:`render` 模块不存在);实现后全套 35 个测试通过。
- 连续两次 build 输出 SHA-256 逐字节一致;`build --check` 只比较不写文件(测试断言被改文件内容不被覆盖);漂移检测报告缺失与不一致。
- 转义:`<script>alert(1)</script>` 标题在 HTML 中以 `<script>` 内嵌、Markdown 中转义为实体;内嵌 payload 段内不存在裸 `<`/`>`,无法提前闭合 `<script>`。
- B 级核查标记不会被升级为 A(C12 行断言 `B(2026-10-28)` 且不含 `A(2026-10-28)`)。
- 浏览器实测(file:// 直接打开):无控制台错误;统计条、8 个阶段卡片、20 行资源表、18 行周计划、10 行研读入口、候选区"尚未运行"提示全部渲染;C12 显示 B 级与 403 说明;无 CDN、无运行时 fetch。
- `validate`、`build`、`build --check` 全部通过。

**遗留问题**

- 页面筛选/搜索/个人进度属 T03,尚未实现(页面目前为只读展示)。
- 观测与候选数据文件尚不存在,页面按"尚未检查/尚未运行"如实展示,不编造日期。

## T03 筛选、周计划与个人进度(2026-10-29)

**改动**

- `learning/web/template.html` 增加:搜索框 + 阶段/语言/类型/主选修筛选(组合生效、计数、空结果提示);「我的进度」面板(导出/导入/清空);阶段指定内容表与周计划表的进度按钮(作业用 assignment ID、周用 W ID)。
- 进度存储:`localStorage` 键 `learning-hub.progress.v1`,值为 `{schema_version:1, assignments:{}, weeks:{}}`;状态固定 未开始/进行中/已完成/待复盘;未知顶层字段在导入时保留(向前兼容)。
- 导入校验为纯 JS 块(`LEARNING_HUB_PROGRESS.validateImport`,模板中以 `PROGRESS-CORE-START/END` 标记),先完整验证再替换;失败时返回错误且不产生可应用数据。
- localStorage 不可用时降级:页面可读、进度仅在本次页面有效并显示提示条。
- 新增 `tests/learning_hub/test_progress_js.py`:9 个测试,校验逻辑用 node 执行纯 JS 块。

**验证(全部真实执行)**

- 离线测试:全套 44 个通过(node 覆盖:合法导入、缺省分区、未知 ID 忽略并报告、非法状态整体拒绝且不返回数据、非对象拒绝、schema_version 错误、未知顶层字段保留)。
- 筛选实测(浏览器 1280px):阶段 S04 + 选修 → 恰好 C06/C09/C14/C15 四条;搜索不存在词 → 资源表与阶段卡显示空结果提示;清除筛选恢复 20/20、33/33。
- 进度实测(无头 Chrome + CDP,独立实例):点击循环写入正确;刷新后 W01=进行中、S04-C09-01=已完成并汇总正确;损坏 JSON 重载后提示"已忽略、页面可正常阅读"且进度归零、20 行资源表可读;注入脚本禁用 localStorage 后显示临时进度提示且按钮仍可在本次会话内工作;导出内容与存储一致。
- 布局:390px 与 1280px 无头截图检查,无横向溢出,筛选条与按钮可用。
- 说明:曾用 chrome-devtools 连接用户浏览器验证,应用户要求停止切换前台标签;上述交互验收改在独立无头 Chrome 实例完成。键盘焦点验证到"搜索框可聚焦(native input)";全部控件为原生元素并带 :focus-visible 样式,未做逐键 Tab 走查。

**遗留问题**

- file:// 与 localhost 存储隔离、跨入口迁移步骤的说明放在 T06 文档任务;页面提示文案已含"导出/导入迁移"。

## T04 网络抓取和课程刷新(2026-10-29)

**改动**

- 新增 `tools/learning_hub/fetch.py`:`fetch_url` 返回固定字段字典;默认 transport 单次请求、不跟随重定向(重定向策略归 refresh 逐跳控制)、15 秒超时、响应体上限 2MiB、逐跳公网地址检查(私有/回环拒绝)、明确 User-Agent;超时/5xx/429 最多额外重试 2 次,Retry-After ≤60 秒生效、超限放弃本次。
- 新增 `tools/learning_hub/refresh.py`:`refresh_courses` 只接受"单次请求"的 fetch(便于逐跳安全检查);重定向最多 5 跳、仅允许课程原域与 `course_rules.allowed_redirect_hosts`;先取 robots.txt(禁止→restricted 不访问;无法获取→跳过并注明;4xx 视为无规则);同域间隔 ≥2 秒(可注入 sleep);404/410 按 run_id 去重累计,连续两次独立运行才 likely_unavailable;正文定位顺序为配置区域→main→article,忽略 script/style/nav/footer/noscript 并压缩空白;定位不到正文或非 HTML 内容→unsupported_content,不用整页 hash 冒充;403/429/网络错误保留既有成功指纹。接口在计划签名基础上增加可选 kwargs `sources`/`sleep`(course_rules 存于 sources.json,需传入;测试需注入 sleep),已在文档字符串注明。
- `__main__.py` 增加 `refresh` 子命令:`--apply` 与 `--output-dir` 互斥(同时传入退出 2);默认写 `.runtime/learning-hub/`;`--apply` 写 `learning/data/observations.json` 并重建页面,前后比对 catalog SHA-256;单站异常不改变退出码,汇总打印各状态计数并提示"退出 0 不代表全部正常"。
- 新增 `learning/data/observations.json`:2026-10-28T16:53Z(UTC)真实检查基线;新增 `tests/learning_hub/test_fetch.py`(13 个)与 `test_refresh.py`(17 个),全部离线。

**验证**

- 离线测试全套 75 个通过,覆盖清单全部场景:200/301/403/404/410/429/500/超时/非 HTML、5 跳上限、2MiB 上限、Retry-After 5 与 120、首次建基线、相同/变化内容、错误页不覆盖指纹、重复 run_id 不累计、两次独立缺失→疑似失效、恢复清零、robots 三态、未允许域重定向停止、仅访问课程域、catalog 输入不被修改。
- 真实网络检查(本地输出模式 + `--apply` 各一次):20 门课程全部 reachable 并首次建立内容基线;DeepLearning.AI(C12–C18)本次直接返回 200,与 2026-10-28 人工核查时的 403 不同——B 级核查标记保持不变(HTTP 200 不升级 A,费用仍待人工确认);`--apply` 后 catalog SHA-256 前后一致;build --check 无漂移。

**遗留问题**

- 尚无 403 案例(本次全部可达):403 分支由离线测试覆盖,真实 403 出现时按记录如实展示。
- 更新报告(latest.md)属 T06;当前以 stdout 汇总。

## T05 候选课程发现(2026-10-29)

**改动**

- 新增 `tools/learning_hub/discover.py`:`normalize_url`(小写 host、去 fragment、仅去 `utm_*`/`ref`/`source`、去无意义尾斜杠、保留功能参数)与 `discover_candidates`(遍历启用来源,单来源失败不清空历史、全部成功才推进 `last_discovery_month`);候选存归一化 URL,初始 `new`,人工 `accepted/dismissed` 与 `first_seen_at` 跨运行保留,消失候选保留记录;已有课程 URL 排除;不递归、不抓候选详情。
- `__main__.py` 增加 `discover` 子命令(与 refresh 相同的 `--apply`/`--output-dir` 互斥与 SHA 守卫);stdout 汇总候选状态与来源检查,来源异常时明确提示。
- 新增 `learning/data/candidates.json`(真实发现基线)与 `tests/learning_hub/test_discover.py`(11 个测试)。

**验证**

- 离线测试全套 86 个通过:相对链接解析、允许域/路径前缀过滤、同页与跨运行去重(尾斜杠同 URL)、跟踪参数去除、功能参数保留(tab=1)、已有课程排除、new/accepted/dismissed 状态保持、消失候选保留、失败来源不清空历史且月份不推进、robots 拒绝与网络失败记异常、catalog 不被修改、仅访问来源域。
- 真实发现:LangChain Academy 正常,发现 3 个新候选(Deep Agents 介绍、LangSmith Essentials、LangSmith Deployment);huggingface.co 在当前网络 TLS 连接被重置(robots 与目录均 network_error)——如实记录为来源异常,未编造发现;两次运行验证异常来源不清空历史(3 条保持、URL 一致);`--apply` 后页面候选区实测渲染 3 行(无头 Chrome),统计卡显示"3 个候选(未纳入)"。

**遗留问题**

- huggingface.co 在本网络不可达:HF 候选发现待网络可用后运行;来源异常会持续如实展示,不影响其他来源。
- 候选的人工处理(接受/忽略)目前直接编辑 candidates.json,T06 将把步骤写入 MAINTENANCE.md。

## T06 更新报告与恢复文档(2026-10-29)

**改动**

- 新增 `tools/learning_hub/report.py`:`render_update_report(observations, candidates)` 确定性渲染 Markdown 报告——运行时间、检查总数、各状态计数(中文标签+枚举)、首次建立基线单独标记(不计为更新)、正文变化提醒(注明人工数据不受影响)、重定向链接变化、异常清单与解释(403/429/超时≠下架)、全部网络失败的明确措辞;候选区区分"发现失败"(来源异常)与"没有发现新候选"(检查成功但无新课程);固定说明含标题/费用待人工核查、进度不自动同步、file:// 与 localhost 存储隔离及导出/导入迁移。
- `build_outputs` 新增第 5 个输出 `learning/updates/latest.md`(已生成并纳入漂移检查);报告横幅标明数据来自 observations/candidates。
- 新增 `learning/MAINTENANCE.md`:数据三分原则、命令表、新增课程(C21 起不回收编号)、修改章节/阶段/周、人工确认 A/B(HTTP 200 不自动升级)、候选接受/忽略步骤、重建基线、Git 恢复观测、状态解读表、进度与自动更新关系、已知限制。
- 新增 `tests/learning_hub/test_report.py`:8 个测试。

**验证**

- 全套 94 个离线测试通过,覆盖要求的四种情形:转义(`<script>` 标题与 note 中 HTML 均转义)、固定输入重复渲染一致、零变化(含"首次建立基线 1 门…不是内容更新"与"没有发现新候选")、全部网络失败(明确"全部 2 门课程检查失败…不代表课程下架")。
- 另覆盖:发现失败与未发现候选措辞区分、异常状态计数与清单、空 observations 如实显示"尚无检查记录"。
- `build` 生成 5 个文件,`build --check` 无漂移。

**遗留问题**

- 无;报告目前只覆盖最近一次运行(observations 只保留最新状态,历史趋势不在此范围)。

## T07 CI 与定时自动更新(2026-10-29)

**改动**

- 新增 `.github/workflows/learning-hub-ci.yml`:push/PR 触碰学习文件时运行 validate、离线测试、`build --check`;权限仅 `contents: read`;不访问公网、不依赖产品模型配置;超时 10 分钟;concurrency 按 ref 取消重复。
- 新增 `.github/workflows/learning-hub-refresh.yml`:cron `17 1 * * 1`(UTC,周一北京时间 09:17)+ workflow_dispatch(布尔 `discover` 输入);月度发现读 `candidates.json` 顶层 `last_discovery_month`(仅全部来源成功才推进,失败来源自然保留重试资格;手动可强制);先 validate+测试,再 `refresh --apply`、按需 `discover --apply`,随后再次 validate+测试+`build --check`(PR 不触发 CI,故 job 内显式验证);提交 allowlist 仅限 observations.json、candidates.json、latest.md 与 4 个生成文件;固定分支 `automation/learning-hub-refresh`,带租约推送,查找到的开放 PR 若作者不是 `github-actions[bot]` 则失败保留现场;PR 用 gh CLI + `--body-file learning/updates/latest.md`,无差异不建 PR;权限仅 `contents: write` 与 `pull-requests: write`(GITHUB_TOKEN,无第三方 PAT);concurrency `learning-hub-refresh`(不取消)+ job 超时 20 分钟;Action 固定 commit SHA(checkout v5.0.0、setup-python v5.6.0、upload-artifact v4.6.2,均经 `git ls-remote` 核查并在旁注主版本);artifact 仅含三个数据/报告文件(不含 .env、.runtime、客户材料),保留 30 天;失败时 Job Summary 写入原因,artifact 照常上传,结果不静默丢失。
- `learning/MAINTENANCE.md` 补充工作流说明与限制(默认分支、Actions 权限策略、schedule 延迟/停用、合并 PR 永远是人工动作)。

**验证**

- YAML 校验通过(pyyaml),并断言:cron 表达式、两工作流权限矩阵、20 分钟超时、concurrency 组、discover 输入存在。
- Action SHA 通过 `git ls-remote` 对 github.com 实际核查(本机到 github.com 可达)。
- **在线调度未验证**:远端 `origin`(github.com:huanyusun/fde-study)默认分支 `main` 仍停留在初始提交 `53112a6`,本工作分支未推送、未合并;工作流文件不在默认分支上,schedule 与 workflow_dispatch 均无法触发。不虚报"已启动";待分支合并推送后,可手动 dispatch 做首次在线验证。

**遗留问题**

- 在线验证待用户把分支推送到 GitHub 并合入 `main` 后进行;此前定时更新不会发生。

## T08 整体验收与交接(2026-10-29)

**验收命令真实结果**

- `validate`:通过(课程 20、阶段 8、周 18)。
- 完整学习测试:`94 passed`。
- `build --check`:生成文件与 catalog 一致,无漂移(5 个生成文件)。
- `git diff --check`(工作区与暂存区):无空白错误。
- 数据核对脚本:生成 Markdown 的本地链接全部存在;catalog 20 门课程全部出现在页面;候选 3 条均不在 20 门课程之内;阶段 8、周 18。
- 变更范围核对(对照初始提交 `53112a6`,共 35 个文件):全部位于 `learning/`、`tools/learning_hub/`、`tests/learning_hub/`、`.github/workflows/`、根 `README.md`、`docs/superpowers/`、`AI学习路径与大纲.md`(用户成果存档);`platform/`、`contracts/`、`artifacts/`、`course-materials/`、`docs/w01/`、`product/`、`evals/`、`tests/`(产品测试)、`sample_data/` 零改动;用户原有未提交资料原样保留于存档提交 `7aea723`。

**页面实测(无头 Chrome,390–500px 与 1280px)**

- 结构完整:8 阶段卡、20 资源行、18 周行、10 研读入口、3 候选行;来源检查栏显示真实"已覆盖 20 门"。
- 搜索空结果提示、S04+选修组合筛选(4/20、4/33)正常。
- 进度点击写入 localStorage;非法导入被整体拒绝且旧进度保留;未知 ID 导入被忽略并报告。
- 发现并修复:阶段卡内作业表未包横向滚动容器导致窄屏水平溢出——已修复并复测(scrollWidth=视口宽,无溢出元素)。

**场景演练对照**

| 场景 | 演练方式 | 结果 |
|---|---|---|
| 相同页面/无变化 | 离线 fixture(test_refresh) | 通过:content_changed=False、报告"未发现正文变化" |
| 来源变化(重定向) | 离线 fixture | 通过:redirected 状态、记录 final_url |
| 403 | 离线 fixture | 通过:restricted、保留成功指纹;真实运行中 C12–C18 曾 403(2026-10-28),本次 200,B 级未升级 |
| 连续 404 → 疑似失效 → 恢复 | 离线 fixture | 通过:missing_once → likely_unavailable → 恢复清零 |
| 目录异常 | 离线 fixture + 真实网络(huggingface.co TLS 被重置) | 通过:来源记 failed、历史候选保留、月份不推进 |
| 无 PR 权限 | **未在线演练**(需要真实 Actions 环境);代码路径为失败时写 Job Summary 并上传 artifact | 如实标注:未验证 |

**验收分级结论**

- 已实现:T01–T07 全部交付物(catalog 契约、生成器、页面、refresh/discover、报告、维护文档、两个 workflow)。
- 已离线验证:94 个离线测试、determinism、漂移检查、转义、进度导入防护、7 类场景 fixture 演练。
- 已真实网络验证:两次 refresh --apply(20/20 reachable 基线)、两次 discover(1 来源成功 + 1 来源网络异常如实记录)。
- **已在线调度验证:未验证。** 分支未推送/未合入 `main`,schedule 与 workflow_dispatch 无法触发;在用户推送合并前,定时更新不会发生,不视作已上线。

**交付入口与命令**

- 统一入口:`learning/index.html`(直接双击打开,或 `python3 -m http.server 8000 --bind 127.0.0.1` 后访问 `/learning/`)。
- 日常维护:`learning/MAINTENANCE.md`;更新报告:`learning/updates/latest.md`;命令见根 `README.md`。

**遗留问题汇总**

1. 在线调度未验证(待推送合并后手动 dispatch 一次即可验证)。
2. huggingface.co 在当前网络不可达:HF 候选发现待网络可用;来源异常如实展示。
3. 无 PR 权限路径未在线演练(设计上失败即保留报告 artifact)。
4. C12–C18 的 B 级核查与费用待人工确认;HTTP 200 不改变该状态。


## 在线调度验证(2026-10-29,GitHub Actions)

推送本仓库后依次验证:

1. `learning-hub-ci` 随 push 自动触发,Ubuntu + Python 3.11 干净环境:validate + 94 离线测试 + 漂移检查全部通过(两次)。
2. `learning-hub-refresh` 手动 dispatch 三次:
   - 第 1 次发现工作流缺陷:`gh pr list --jq '.[0]'` 在无开放 PR 时输出空串,解析崩溃;refresh / discover / 提交 / 带租约推送本身成功。已修复(70cd4c2)。
   - 第 2 次暴露仓库设置:新仓库默认禁止 Actions 创建 PR,失败路径按设计工作(Job Summary、30 天 artifact、失败原因日志均保留)。已在仓库设置中允许 Actions 创建 PR。
   - 第 3 次全绿:20 门检查(12 可达、8 受限——GitHub 出口 IP 被部分站点 403,如实标注)、HF + LangChain 双来源候选发现、正文变化提醒(C05/C20)、提交至 automation/learning-hub-refresh 并创建 PR #1。
3. 结论:定时链路端到端可用;PR 合并由人工完成。

## 自定义域名上线(2026-10-29,learning.f2b.me)

- GitHub Pages:`https://huanyusun.github.io/ai-agent-learning/`(workflow 部署,推送自动更新,已验证 200)。
- 代理加速:`https://learning.f2b.me/` — 用户服务器(154.29.144.91)nginx 反代 Pages;证书 Let's Encrypt(webroot 自动续期);外部验证:证书 CN 正确、HTTP 301→HTTPS 200、标题与站内资源正常、无 github.io 跳转泄漏。
- 服务器拓扑为 stream 层 SNI 分发:learning 监听 127.0.0.1:10444 并在 nginx.conf map 登记(首版直接监听公网 443 与 stream 冲突导致 reload 静默失败,已修正);实际配置存档于 `docs/nginx-learning.f2b.me.conf`。
- 操作方式:部署脚本上传至服务器 `~/learning-deploy.sh`、`~/learning-repair2.sh`,由用户以 sudo 执行(sudo 密码不经过任何对话或日志)。
