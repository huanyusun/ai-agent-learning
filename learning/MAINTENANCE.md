# 学习中心维护手册

面向"不看代码也能维护课程"的使用者。所有命令在工程根目录执行。

## 数据分:三类数据永不混放

| 数据 | 位置 | 谁在写 |
|---|---|---|
| 人工策划数据(课程、阶段、章节、周计划、费用、A/B 核查) | `learning/data/catalog.json` | 只由人编辑 |
| 自动观测(链接可达性、内容指纹、候选课程) | `learning/data/observations.json`、`learning/data/candidates.json` | 只由 `refresh`/`discover --apply` 写 |
| 个人学习进度(未开始/进行中/已完成/待复盘) | 本机浏览器 localStorage(键 `learning-hub.progress.v1`) | 只由页面按钮写 |

自动流程不会修改标题、费用、主修/选修、阶段映射、指定章节、周计划;个人进度不会被重建覆盖。

## 常用命令

```sh
python3 -m tools.learning_hub validate          # 校验 catalog 结构与引用
python3 -m tools.learning_hub build             # 重新生成页面与 Markdown
python3 -m tools.learning_hub build --check     # 检查生成文件是否与数据一致(CI 用)
python3 -m tools.learning_hub refresh           # 真实检查课程链接,结果写 .runtime/(不覆盖正式数据)
python3 -m tools.learning_hub refresh --apply   # 检查并更新 observations.json + 重建页面
python3 -m tools.learning_hub discover          # 官方目录候选发现,结果写 .runtime/
python3 -m tools.learning_hub discover --apply  # 发现并更新 candidates.json + 重建页面
python3 -m pytest tests/learning_hub -q         # 离线测试
python3 -m http.server 8000 --bind 127.0.0.1    # 本地预览(浏览器打开 http://127.0.0.1:8000/learning/)
```

`refresh --apply` 与 `--output-dir` 互斥(同时给退出码 2);单站失败不会让命令失败,看输出里的状态计数。

## 新增课程(从 C21 起)

1. 编辑 `learning/data/catalog.json`,在 `courses` 末尾新增条目;编号从现有最大号 +1,即使旧课程失效也**不回收编号**。
2. 必填字段:`id, title, provider, url, language, kind, access_note, cost_status, cost_note, effort_hours, manual_review`。
   - `kind` 只能是 `video_course / text_course / documentation / article / source_code`;
   - `cost_status` 只能是 `free_content / mixed / unknown`;不确定就填 `unknown`,费用写"待确认";
   - `manual_review`:亲自读取官方页面后填 `level: "A"`;只看到目录/搜索摘要填 `"B"`,日期用实际核查日。
3. 在对应 `stages[].assignments` 里加作业(如 `S03-C21-01`),写清 `sections` 与 `why`;同一课程多阶段就各写一条。
4. 运行 `validate` → 通过后 `build` → `build --check`;再跑一次离线测试。
5. 不要直接改 `learning/README.md`、`courses.md`、`weekly-plan.md`、`index.html`——它们是生成文件,手改会被覆盖。

## 修改章节、阶段或周计划

- 改指定章节:编辑对应 assignment 的 `sections`;改周安排:编辑 `weeks`。
- 阶段依赖(`prerequisites`)不能成环;周编号固定 W01–W18。
- 改完执行 `validate && build`,然后 `build --check` 确认无漂移。

## 人工确认 A/B 核查

- `A` = 亲自读取过官方课程/教程页面;`B` = 只确认存在(目录或搜索摘要),详情页没核实(当时 403)。
- **HTTP 200 不会把 B 自动升级为 A**;升级必须由人完成:亲自读取官方页面 → 更新 `manual_review.level/date/note` → `build`。
- 费用同理:`unknown` 只有在人工确认后才能改;抓取成功不构成价格事实。

## 处理候选课程(candidates.json)

自动发现只产出"候选",不进入学习路径。处理方式(直接编辑 `learning/data/candidates.json`):

- **接受**:先按"新增课程"流程把课程录入 catalog,再把该候选 `status` 改为 `accepted`,`note` 写入新课程编号(如"已录入为 C21")。
- **忽略**:把 `status` 改为 `dismissed`,`note` 写原因。被忽略的候选会一直保留,不会重复出现为 new。
- `first_seen_at` 由系统维护,人工不要改。

## 重新建立内容基线

内容指纹(正文 hash)只在成功读取时建立/更新。需要重新基线(例如正文区域改版导致大量误报):

1. 编辑 `learning/data/observations.json`,删除对应课程的条目(或整份文件)。
2. 运行 `python3 -m tools.learning_hub build`(页面会显示"尚未检查",不会编造日期)。
3. 下次 `refresh --apply` 会把这些课程重新按"首次建立基线"处理。

## 恢复旧观测 / 失败后恢复

自动数据全部入库,可随时从 Git 恢复:

```sh
git log --oneline -- learning/data/observations.json   # 找到想要的版本
git checkout <commit> -- learning/data/observations.json
python3 -m tools.learning_hub build                    # 页面按恢复后的数据重建
```

`candidates.json`、生成文件同理。任何写入都是"先临时文件再替换",失败不会截断现有文件。

## 状态怎么看(课程来源检查)

| 状态 | 含义 | 要做什么 |
|---|---|---|
| reachable / redirected | 可达 / 经重定向可达 | 无需处理;redirected 说明链接有跳转 |
| restricted | 403、登录/挑战页或 robots 禁止 | 不等于下架;想核实就人工用浏览器看 |
| rate_limited | 被限流(429) | 过几天重跑 refresh |
| missing_once | 单次 404/410 | 仅提示;再跑一次确认 |
| likely_unavailable | 连续两次独立运行缺失 | 疑似失效:人工确认后决定下架/换链接,**编号不回收** |
| network_error | 本机网络/超时 | 恢复网络重跑;不代表课程下架 |
| unsupported_content | 可达但定位不到正文区域 | 需要时在 sources.json 的 `course_rules` 配置 `content_region` |

## 个人进度与自动更新的关系

- 外站课程更新**不会**自动同步到个人进度;进度只在你点按钮时变化。
- `file://` 直接打开与 `http://127.0.0.1:8000` 打开是两个浏览器来源,进度互不相通;换入口前先「导出进度 JSON」,到新入口再「导入进度 JSON」。
- localStorage 不可用时页面仍可阅读,进度仅在本次会话内有效(页面会提示)。

## 自动更新工作流(GitHub Actions)

两个工作流位于 `.github/workflows/`,均固定官方 Action 的 commit SHA:

| 工作流 | 触发 | 做什么 |
|---|---|---|
| `learning-hub-ci.yml` | push/PR 触碰 `learning/`、`tools/learning_hub/`、`tests/learning_hub/`、工作流本身 | validate + 离线测试 + `build --check`;**不访问公网** |
| `learning-hub-refresh.yml` | 每周一 UTC 01:17(北京时间 09:17)+ 手动 dispatch(可勾选 discover) | refresh --apply;每月首次/来源失败重试/手动强制时额外 discover --apply;全套离线验证;把自动数据与生成文件提交到 `automation/learning-hub-refresh` 分支 |

月度发现判断读 `candidates.json` 顶层 `last_discovery_month`(只在全部启用来源成功后推进),不是简单看日期;失败的来源保留旧月份,下周自动重试。更新结果只提交到固定分支并维护**一个** PR(带租约更新,归属不是 bot 则失败保留现场);无差异不建 PR;不合并 PR、不推送默认分支。PR 权限被仓库策略拒绝时,报告与自动数据仍会写入 Job Summary 并作为 artifact 保留 30 天。

### 工作流的限制

- schedule 使用 UTC,可能延迟,仓库禁用 Actions 时不会运行;只在**默认分支**上的工作流定义才会被调度。
本仓库(2026-10-29)已完成在线验证:CI 与 workflow_dispatch 真实运行通过,自动更新 PR #1 已创建;合并 PR 是人工动作,自动流程永远不会自行合并。本地命令不依赖 GitHub、始终可用。仓库设置中已允许 Actions 创建 PR(关闭该开关后,周任务会按设计失败并保留报告 artifact)。
- 合并 PR 是人工动作,自动流程永远不会自行合并。

## 已知限制(截至 2026-10-29)

- 候选发现只覆盖 `learning/data/sources.json` 里启用的官方目录;huggingface.co 在部分网络不可达时,该来源会如实显示“发现失败”。

## GitHub Pages 与自定义域名代理加速

- 官方站点:`https://huanyusun.github.io/ai-agent-learning/`,由 `learning-hub-pages` 工作流在 `learning/`、大纲或工作流改动推送到 main 时自动发布(也可手动 dispatch)。
- 页面是纯静态快照:`index.html`、数据、生成 Markdown、大纲与维护手册都在站点内;`platform/` 等代码研读链接指向仓库文件,请回 GitHub 仓库查看。
- **自有域名代理加速**:使用 `learning.f2b.me`(DNS 已指向服务器 154.29.144.91,无需改动)。服务器按 `docs/nginx-learning.f2b.me.conf` 反向代理 Pages:先放配置并注释 ssl 三行,reload 后 `certbot certonly --nginx -d learning.f2b.me` 签证书,再恢复 ssl 三行并 reload。站点内容更新仍走 Pages 工作流,代理无需改动。配置完成后用 `curl -sSI https://learning.f2b.me/` 验证。
- 改用域名后,页面进度 localStorage 会绑定新来源(域名),与 `github.io` 和 `file://` 互不相通;切换入口先「导出进度 JSON」再「导入」。
