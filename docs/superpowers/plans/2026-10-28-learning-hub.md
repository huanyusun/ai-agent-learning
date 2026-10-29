# 统一课程中心与自动更新 Implementation Plan

> **For agentic workers:** 按任务顺序使用 `executing-plans` 执行，使用复选框跟踪完成情况。本任务由用户指定的 GLM-5.3-Flash 执行；无需启动子代理。每次只完成一项任务并提交验证结果。

**Goal:** 将现有课程、大纲、18 周任务统一为可搜索和跟踪的本地学习中心，并定期检查课程变化、发现候选资源、生成可审核更新。

**Architecture:** JSON 保存人工策划数据，Python 校验并生成 Markdown 和静态 HTML；浏览器负责筛选和个人进度。独立更新器抓取公开来源，把观测结果与人工内容分开。GitHub Actions 定时运行，固定分支 PR 提交更新，人工合并；不能创建 PR 时上传报告，不静默丢失结果。

**Tech Stack:** Python 3.11+ 标准库、pytest、原生 HTML/CSS/JavaScript、GitHub Actions；不引入前端框架、数据库、付费模型 API 或常驻后端。

## 0. 本轮与实施范围

本文件为待执行计划；创建本计划不表示学习页面、更新脚本或定时任务已经实现。

用户所说“整理到一起”按以下产品结果落地：

- 一个入口同时查看 8 个阶段、20 个资源、指定章节、18 周实践、验收和更新提醒。
- 一个资源只录入一次；在多个阶段复用时，各阶段分别指定学习章节和交付物。
- 合并课程导航，而不是下载或拼接外站视频、镜像付费课堂。
- 自动更新包括每周来源检查和每月候选课程发现；候选结果不直接改变学习顺序。
- 页面进度保存在本机，可导入导出；不做账号与跨设备云同步。

## 1. Global Constraints

- 仅修改学习模块、对应工具/测试、工作流和文档入口；不修改 `platform/fde_product/`、W1 契约、作业证据及业务行为。
- 开始前读取 `git status --short`；原有未提交资料属于用户成果，不覆盖、不删除、不夹带进自己的提交。
- 数据、页面文案和命令帮助以中文为主；保留原始课程英文名和原始链接。
- 保留 C01–C20；新增课程从 C21 起，不能因失效或下架回收编号。
- 课程、文章、文档、源码的资源类型必须明确区分。
- 保留 A/B 的历史核查说明；HTTP 200 不能将 B 自动升级为 A。
- 自动流程不修改标题、费用、主修/选修、阶段映射、指定章节、周计划和学习进度；这些属于人工策划数据。
- 抓取结果不能覆盖价格事实；展示“费用待核查”而非推断免费。
- 403/429/超时分别展示，不等同于课程下架；首个 404/410 只提示，连续两次独立运行再标记疑似失效，不自动删除。
- 默认不绕过登录、验证码或访问限制；不读取浏览器凭据，不调用 GLM API，不购买服务。
- 当前日期以实际执行时间为准；历史人工核查日期固定保留 2026-10-28。
- 原 Markdown 可继续访问；被生成器接管的文件加明确标头和人工编辑指引。
- 计划只要求本地页面与工作流文件；不自动部署网站或修改仓库权限。

## 2. 现有资料与落点

输入文件：

- `AI学习路径与大纲.md`：保留为详细能力大纲，不整篇改为生成文件。
- `learning/README.md`：现有阶段导航和代码研读入口，迁移信息后改为生成入口。
- `learning/courses.md`：20 项资源，迁移后由生成器维护。
- `learning/weekly-plan.md`：18 周任务与笔记模板，迁移后由生成器维护；模板保留在单独文件。
- `README.md`：补统一入口和维护命令。
- `pyproject.toml`：已有 pytest 配置，`pythonpath = ["platform"]`；不要破坏现有设置。

目标文件职责：

```text
learning/
  data/catalog.json              # 人工课程、阶段、章节映射与周计划
  data/sources.json              # 允许抓取的官方来源与候选发现规则
  data/observations.json         # 最新自动观测与有效内容指纹
  data/candidates.json           # 新课程候选和人工处理状态
  templates/weekly-note.md       # 现有笔记模板
  web/template.html              # 页面结构、内嵌样式和逻辑；无外部 CDN
  index.html                     # 生成的独立静态页面
  README.md                      # 生成导航
  courses.md                     # 生成资源表
  weekly-plan.md                 # 生成周计划
  updates/latest.md              # 最近一次更新摘要
  MAINTENANCE.md                 # 数据维护、运行、异常与恢复说明
tools/learning_hub/
  __init__.py                    # 包标识
  __main__.py                    # CLI 分发与退出码
  catalog.py                     # 加载、校验和引用完整性
  render.py                      # 生成 Markdown 和 HTML
  fetch.py                       # HTTP、限额和重试；可注入 transport
  refresh.py                     # 链接/内容观测、状态与基线
  discover.py                    # 官方目录候选发现与去重
  report.py                      # 更新摘要，供 PR 与本地阅读
tests/learning_hub/              # 数据、生成、更新、发现的离线测试
.github/workflows/learning-hub-ci.yml
.github/workflows/learning-hub-refresh.yml
```

不提前创建空练习目录；不把抓取的完整网页或视频提交入库。

## 3. 数据与接口契约

### 3.1 catalog.json

顶层固定：`schema_version: 1`、`courses`、`stages`、`weeks`、`repo_links`。禁止将自动观测结果塞入本文件。

课程必填字段：`id`、`title`、`provider`、`url`、`language`、`kind`、`access_note`、`cost_status`、`cost_note`、`effort_hours`、`manual_review`。

- `kind`: `video_course | text_course | documentation | article | source_code`。
- `cost_status`: `free_content | mixed | unknown`；不表示调用 API 或证书免费。
- `effort_hours`: `{min: number, max: number, note: string}`，非负且 min ≤ max。
- `manual_review`: `{level: "A" | "B", reviewed_on: "YYYY-MM-DD", note: string}`。
- 所有 URL 仅允许 http/https；页面链接禁止 `javascript:`。

阶段必填：`id`（S00–S07）、`title`、`objective`、`prerequisites`（阶段 ID 数组）、`assignments`、`deliverables`、`acceptance`。

每个 assignment：`id`（稳定、唯一，例如 S03-C08-01）、`course_id`、`priority`（core/elective）、`sections`（字符串数组）、`why`。同一课程可出现在多阶段，不复制课程元数据。

每周必填：`id`（W01–W18）、`stage_id`、`assignment_ids`、`study`、`practice`、`deliverables`、`acceptance`、`repo_paths`。个人学习状态不写入这里。

`repo_links`：`{label, path, description}` 数组；校验仓库相对路径存在，保留现有研读入口。

### 3.2 observations.json

顶层：`schema_version: 1`、`last_run_at`（UTC ISO 8601）、`courses`（以课程 ID 为键）。课程结果字段：

`checked_at, status, http_status, final_url, last_success_at, last_good_hash, content_changed, consecutive_missing, missing_run_id, note`。

`status` 枚举：`reachable | redirected | restricted | rate_limited | missing_once | likely_unavailable | network_error | unsupported_content`。

有效指纹只取成功的课程正文或配置的内容区域。403、登录/挑战页、网络失败不能建立或覆盖 `last_good_hash`。首次成功建立基线时 `content_changed=false`。正文仅检测“需复核”，不推断语义变化。

### 3.3 sources.json 与 candidates.json

`sources.json` 顶层：`schema_version:1, sources:[], course_rules:{}`。来源字段：`id, url, mode, allowed_hosts, item_path_prefix, enabled, note`；`mode=html_links`。初版仅配置两个已使用的官方目录：

- Hugging Face Learn：`https://huggingface.co/learn`，只接纳同域 `/learn/` 下的课程入口。
- LangChain Academy：`https://academy.langchain.com/`，只接纳同域 `/courses/` 下的链接。

实现时先检查实际响应与 robots.txt；目录不可解析则记“需人工检查”，不伪造空的成功发现。不假定任何站点存在 RSS。其他来源先人工维护，不加通用搜索引擎爬虫。

`course_rules` 按 C ID 配置 `{allowed_redirect_hosts: [], content_region: {tag, id, class_name}}`。正文定位仅支持 tag 和可选 id/单个 class token，不实现完整 CSS 选择器。未配置时依次尝试 main、article；没有命中则 unsupported_content。跳转目标的原始域默认允许，额外域必须显式列出；目录抓取使用其 allowed_hosts。对挑战/登录页面依据 URL 和标题明确特征判 restricted，不建立内容指纹。

候选字段：`url, title, source_id, first_seen_at, last_seen_at, status, note`；status 为 `new | accepted | dismissed`。人工状态和 first_seen_at 必须跨运行保留。入选后人工新增 C 编号，并设置 accepted；不自动分配阶段或费用。

`candidates.json` 顶层：`schema_version:1, last_discovery_month, source_checks:{}, candidates:[]`。source_checks 以来源 ID 保存 `checked_at, status, last_success_month, note`；last_discovery_month 仅在全部启用来源当月成功后推进。部分失败时当月运行只重试失败来源；显式手动 discover 可重查全部来源。

URL 去重：去 fragment、仅去已知跟踪参数 `utm_*`/`ref`/`source`，主机小写，忽略无意义末尾斜杠；保留功能查询参数。不得把不同课程合并。

### 3.4 模块公开接口

```python
# catalog.py
def load_catalog(path: Path) -> dict: ...
def validate_catalog(catalog: dict, repo_root: Path) -> list[str]: ...
# render.py
def build_outputs(catalog: dict, observations: dict, candidates: dict) -> dict[str, str]: ...
# fetch.py；返回固定字典字段而非自由格式异常
def fetch_url(url: str, *, transport=None, sleep=None) -> dict: ...
# 返回：url, final_url, status_code, headers, body, error
# refresh.py；now/run_id 由调用方传入，离线测试固定
def refresh_courses(catalog: dict, previous: dict, *, fetch, now: str, run_id: str) -> dict: ...
# discover.py
def discover_candidates(catalog: dict, sources: dict, previous: dict, *, fetch, now: str) -> dict: ...
# report.py
def render_update_report(observations: dict, candidates: dict) -> str: ...
```

这些是接口说明，实施者需提供函数实现；不把省略号写入最终代码。类型中的 Path 来自 pathlib。

## 4. 命令契约

从工程根目录调用：

```bash
python3 -m tools.learning_hub validate
python3 -m tools.learning_hub build
python3 -m tools.learning_hub build --check
python3 -m tools.learning_hub refresh --output-dir .runtime/learning-hub
python3 -m tools.learning_hub refresh --apply
python3 -m tools.learning_hub discover --output-dir .runtime/learning-hub
python3 -m tools.learning_hub discover --apply
python3 -m pytest tests/learning_hub -q
python3 -m http.server 8000 --bind 127.0.0.1
```

- validate：离线校验，成功 0；数据非法 1。
- build：只读输入，原子替换生成文件；缺观测数据时展示“尚未检查”，不能编造日期。
- build --check：仅比较，不写文件；一致 0，漂移 1。
- refresh/discover 默认结果写 output-dir；未指定时默认 `.runtime/learning-hub/`。只有 --apply 写 tracked 自动数据并重新 build，不修改 catalog.json。
- refresh/discover 单站异常记入结果，整体继续并返回 0；配置非法/程序错误/无法写结果返回 1。报告汇总异常数量，防止“退出 0＝全部课程正常”的误读。
- --apply 和 --output-dir 同时传入报参数冲突，退出 2。
- 所有写入先临时文件、校验成功再替换；失败时不截断现有文件。

## 5. 执行任务

### T01：结构化迁移与校验器

**依赖：** 无。**文件：** catalog.json、sources.json、templates/weekly-note.md、catalog.py、__init__.py、__main__.py、tests/learning_hub/test_catalog.py。

- [x] 对照现有三个 learning Markdown 和原大纲，逐项迁移 20 资源、8 阶段和 18 周任务；保留章节、费用、A/B、研读入口、模板和限制说明，迁移后人工逐行核对。
- [x] 先写离线测试：重复 C ID、悬空 assignment、缺少某周、阶段依赖成环、非法 URL、min>max 和不存在 repo_path 均返回明确字段路径。
- [x] 用如下真实用例验证校验器能阻止破坏引用：

```python
from copy import deepcopy
from pathlib import Path
from tools.learning_hub.catalog import load_catalog, validate_catalog

def test_dangling_course_reference():
    catalog = deepcopy(load_catalog(Path("learning/data/catalog.json")))
    catalog["stages"][0]["assignments"][0]["course_id"] = "C99"
    errors = validate_catalog(catalog, Path.cwd())
    assert any("C99" in error for error in errors)
```

- [x] 运行 `python3 -m pytest tests/learning_hub/test_catalog.py -q`，先确认缺模块失败，再实现校验；通过后运行 validate，预期列出 20/8/18 且无错误。
- [x] 提交本任务负责的新增文件；不整体 git add learning/，避免夹带已有未提交资料。

**验收：** 原始课程和周计划没有信息丢失；自动观测与个人进度没有混入策划数据。

### T02：统一生成器与文档入口

**依赖：** T01。**文件：** render.py、web/template.html、index.html、learning 下三个生成 Markdown、README.md、原大纲、test_render.py。

- [x] 先测：连续 build 字节一致；build --check 不改文件；包含 `<script>` 的标题被转义；20 个资源和 18 周能完整呈现；B 级不会变为 A。
- [x] 实现 build_outputs；模板只替换一个明确数据占位符。内嵌 JSON 时转义 `<`、`>`、`&`，避免 `</script>` 提前闭合。
- [x] 页面使用内嵌数据，无 CDN、无运行时 fetch，直接打开也能阅读；完整展示阶段、指定章节、主/选修、费用、语言、实践、验收及最后检查状态。
- [x] 生成文件顶部加来源与维护命令；README 链接统一入口；保留现有代码研读映射、实施计划/GLM 交接链接和课程覆盖边界。完整大纲保留独立链接。
- [x] 运行 test_render、validate、build、build --check；预期全部通过，第二次 build 无 diff。
- [x] 提交本任务具体文件并记录迁移结果。

**验收：** 编辑 catalog 的一个标题，重建后页面与课程表同步变化；不需手改多份资料。

### T03：筛选、周计划与个人进度

**依赖：** T02。**文件：** web/template.html、生成 index.html；进度导入校验相关测试。

- [x] 增加搜索，以及阶段、语言、类型、主/选修筛选；组合筛选生效，空结果有提示；同资源多阶段章节分别可见。
- [x] 显示 18 周计划及阶段顺序；课程完成用 assignment ID，周进度用 W ID，避免完成某章就误判整门课程完成。
- [x] localStorage 使用 `learning-hub.progress.v1`，值为 `{schema_version:1, assignments:{}, weeks:{}}`；状态固定为未开始/进行中/已完成/待复盘。新增字段必须兼容旧进度。
- [x] 支持 JSON 导入/导出；先完整验证再替换，未知 ID 忽略并报告、非法值拒绝且保留旧进度。localStorage 不可用时仍可阅读并提示临时进度。
- [x] 在 390px 和 1280px 检查布局、键盘焦点、筛选、进度刷新保持、导入导出、损坏 JSON 和空结果；将结果写入验收记录。
- [x] 重建、检查生成漂移并提交。

**验收：** 静态页可用，个人进度不被自动重建覆盖；不把“标为完成”包装成已通过项目验收。

### T04：网络抓取和课程刷新

**依赖：** T01、T02。**文件：** fetch.py、refresh.py、observations.json、CLI、test_fetch.py、test_refresh.py。

- [x] 先用 fake transport 覆盖 200/301/403/404/410/429/500/超时/非 HTML；任何测试都不访问公网。
- [x] 实现 GET、明确 User-Agent、15 秒超时、最多 5 跳重定向、响应体上限 2MiB；顺序请求，同域间隔至少 2 秒；超时/5xx/429 最多额外重试 2 次。Retry-After 最多等待 60 秒；更长则本次记 rate_limited。
- [x] 仅访问配置课程及来源域；检查每次重定向，不向未允许域或私有/回环 IP 继续请求；不传认证信息。读取 robots.txt，明确禁止时跳过并报告 restricted；无法获取规则时跳过并注明原因。
- [x] HTMLParser 忽略 script/style/nav/footer，压缩空白；配置定位不到正文时只记录可达性，status=unsupported_content，不使用整页导航的 hash 冒充课程变化。
- [x] 测试首次建基线、相同内容、有效内容改变、错误页不覆盖成功指纹、重复 run_id 不增加失效次数、连续两次独立 404/410、恢复成功清零。
- [x] refresh --apply 只更新自动观测和生成输出；运行前后 catalog 的 SHA-256 必须一致。
- [x] 运行对应离线测试，再用本地输出模式进行一次真实检查；把 403 如实报告，不为通过验收而绕过限制。
- [x] 提交脚本、测试与经过检查的基线。

**验收：** 单个站点失败不拖垮全部更新，页面能区分从未检查、暂时失败与疑似失效。

### T05：候选课程发现

**依赖：** T04。**文件：** discover.py、sources.json、candidates.json、test_discover.py。

- [x] 先用两个离线目录 fixture 测试：相对链接解析、允许域/路径过滤、课程去重、跟踪参数去除、功能参数保留、同课程多次运行不重复。
- [x] 只抓配置的两个目录，不递归遍历、不抓每个候选详情。目录响应失败或无可解析课程时记录来源异常。
- [x] 排除已有课程 URL；新候选初始为 new；人工 dismissed/accepted 和 first_seen_at 在后续运行保持；消失的候选保留记录。
- [x] 页面独立展示“候选课程，未纳入路径”；不得自动写入 courses/stages/weeks 或宣称适合某阶段。
- [x] 运行离线测试，再执行一次输出到 .runtime 的真实发现；验证异常目录不会清空历史候选。
- [x] 提交具体文件。

**验收：** 月度自动流程能发现配置目录的新增入口；不宣称覆盖全网课程。

### T06：更新报告与恢复文档

**依赖：** T04、T05。**文件：** report.py、updates/latest.md、MAINTENANCE.md、test_report.py。

- [x] 报告列出运行时间、检查总数、各状态计数、链接变化、正文变化提醒、候选来源和异常；明确标题/费用待人工核查。
- [x] 单独标记“首次建立基线”，不将全部课程误报为更新；未发现候选与发现失败必须不同措辞。
- [x] 文档写清新增课程、接受/忽略候选、人工确认 A/B、修改章节、重新基线和恢复旧观测的步骤。
- [x] 明确外站更新不会自动同步到个人进度；file:// 与 localhost 使用不同存储来源，切换入口用导出/导入迁移。
- [x] 测试报告转义、固定时间可重复渲染、零变化、全部网络失败四种情形；运行后提交。

**验收：** 无需读脚本也能维护课程，失败后可从 Git 恢复自动数据并重建。

### T07：CI 与定时自动更新

**依赖：** T01–T06。**文件：** 两个 workflow、MAINTENANCE.md。

- [x] CI 在学习数据、模板、工具、测试或 workflow 改动时执行 validate、离线测试、build --check；PR 测试禁止抓公网，不依赖产品模型配置。
- [x] 定时流程配置 workflow_dispatch 和 cron `17 1 * * 1`（UTC，周一北京时间 09:17）；每周 refresh，每月首次运行 additionally discover。手动 dispatch 增加布尔 discover 输入，不假定月初恰逢周一。
- [x] 月度发现用 candidates 顶层 last_discovery_month 判断，而不是仅判断日期；失败的来源保留重试资格。工作流合并前的重复发现保持幂等。
- [x] 首先在默认分支 checkout 后运行 --apply、build、validate 和离线测试；提交 allowlist 仅限 observations.json、candidates.json、latest.md 与生成页面/Markdown。
- [x] 使用固定分支 `automation/learning-hub-refresh`，查找并更新一个现有 PR；不得每周创建重复 PR。分支/PR 归属不符时失败并保留报告，不覆盖用户分支。
- [x] PR 基于当前默认分支重新生成更新；仅 bot 管理分支允许带租约更新，不合并 PR、不推送默认分支。无文件差异时不建 PR。
- [x] PR 权限只声明 contents:write 与 pull-requests:write；不需第三方 PAT。使用 GitHub CLI 和 --body-file。权限被仓库策略拒绝时仍保留 Job Summary、上传报告和自动数据 artifact，并将失败原因写入日志。
- [x] PR 改动不会必然触发另一个 workflow，因此定时 job 内必须显式跑全套学习模块验证。配置 concurrency 避免手动与定时相互覆盖；设置 20 分钟 job 超时。
- [x] Actions 使用官方维护版本，实施时核查并固定 commit SHA，在旁注主版本；上传 artifacts 30 天。工作流不得上传 .env、.runtime 全目录或客户材料。
- [x] 文档说明默认分支、Actions 权限和定时任务可能延迟/停用的限制；若仓库不托管 GitHub，则本地命令可用，工作流待推送后生效，不声称已经启动。
- [x] 校验 YAML，并实际进行一次 workflow_dispatch 或明确记录“尚未推送/无远端权限，未验证在线调度”；提交文件。

**验收：** 有变化形成一份可审核更新；没有 PR 权限也能取得报告；自动任务不改人工课程数据。

### T08：整体验收与交接

**依赖：** T01–T07。**文件：** `learning/IMPLEMENTATION-RESULTS.md`，必要的文档修订。

- [x] 运行 validate、完整学习测试、build --check、git diff --check，保存真实结果。
- [x] 核对 20 资源/8 阶段/18 周；Markdown 本地链接和所有课程引用存在；新增候选不计入原 20 资源。
- [x] 实测页面搜索、组合筛选、移动端、进度保存及导入失败保护。
- [x] 分别演练：相同页面、来源变化、403、连续 404、恢复、目录异常、无 PR 权限；离线场景使用 fixture，不伪称公网运行结果。
- [x] 验证现有 W1 产品文件没有改动，原有用户工作没有被清理；有产品相关依赖改动则回退这些非授权变更。
- [x] 验收记录区分：已实现、已离线验证、已真实网络验证、已在线调度验证。最后一项无证据时写未验证。
- [x] 最终交付统一入口、命令、测试结果、变更范围和实际限制；不要把功能实现等同于定时任务已上线。

## 6. 执行顺序与里程碑

```text
T01 数据契约 → T02 统一生成 → T03 阅读与进度
                         → T04 来源检查 → T05 候选发现
                                      → T06 报告 → T07 调度 → T08 验收
```

- M1：T01–T03，可本地使用的统一课程中心。
- M2：T04–T06，可手动刷新与发现，自动数据可追踪。
- M3：T07–T08，定时运行配置与完整验收。

建议 GLM 分三轮执行上述里程碑，轮次间读进度记录继续；不要求用户逐项确认。若只是实现困难，应缩小当前改动并修复，不擅自跳过需求。

## 7. 官方依据

- [GitHub 定时事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)：schedule 默认使用 UTC，默认分支运行，可能延迟；实施时再次核查平台限制。
- [GitHub Token 权限](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)：使用工作流权限限制 GITHUB_TOKEN；仓库设置仍可能限制 PR 能力。
- 课程来源及历史核查见仓库 `learning/courses.md`；不要把“能访问网页”当作已核实课堂权益。
