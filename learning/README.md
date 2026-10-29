<!-- 本文件由 tools/learning_hub 生成;请勿手工编辑,改动会被 build 覆盖。
     数据来源:learning/data/catalog.json(人工策划数据)
     重新生成:python3 -m tools.learning_hub build
     漂移检查:python3 -m tools.learning_hub build --check
     整段人工文字在 tools/learning_hub/render.py 的 CURATED_* 常量中维护;
     迁移前的人工原稿存档于上游仓库 huanyusun/fde-study(提交 7aea723)。 -->

# AI Agent 工程课程导航(生成)

从[完整学习大纲](../AI学习路径与大纲.md)出发,按能力依赖组织网上课程,并配套本仓库实践。资源核查日期:2026-10-28。

统一入口:[learning/index.html](index.html)——搜索、筛选、18 周进度与导入导出都在这一个页面。

下一步建设:[统一课程中心与自动更新实施计划](../docs/superpowers/plans/2026-10-28-learning-hub.md),以及[GLM-5.3-Flash 执行提示词](GLM-HANDOFF.md)。

## 如何开始

1. Python 不熟先补阶段 0;能独立开发 API 的学习者可直接进入第 1 周。
2. 按下表选择指定内容,详细链接和核查状态见[课程资源目录](courses.md)。
3. 每周按[实践与进度表](weekly-plan.md)产出一个可检查的结果。
4. 在 `learning/notes/` 保存笔记,在 `learning/labs/` 放独立练习,在 `learning/outputs/` 保存脱敏的报告。这些目录按实际需要建立。

优先读中文主线;用英文官方课程补充状态机、MCP 和部署。主修表示本项目的学习建议,选修用于补短板。文档教程、工程文章和源码案例已明确标出,不将它们当作视频课。推荐从[统一课程中心页面](index.html)搜索、筛选并跟踪个人进度。

## 分阶段选课

| 阶段 | 主修与指定内容 | 选修 | 学完要能完成 |
|---|---|---|---|
| S00 工程基础 | C01(函数、异常、单元测试、文件、面向对象);C02(请求体、响应模型、错误处理、依赖、安全、测试) | C03(容器、镜像、应用栈) | 带校验和测试的 API |
| S01 模型调用 | C04(模型 API 入门、Prompt 内容);C05(第 3 章) | C02(流式传输);C12(指令、示例、迭代和文本处理) | 模型适配、结构校验、错误分类 |
| S02 工具接入 | C07(架构、Client/Server、工具/资源/提示模板、端到端应用);C05(第 10 章 MCP 部分) | C13(结构输出、工具选择和路由) | 工具注册、校验、拒绝与审计 |
| S03 Agent 执行 | C08(模块 1 图与 Agent、模块 2 状态、模块 3 人机协同);C05(第 4 章、第 7 章) | C06(Unit 1、Unit 2.3 LangGraph) | 有终止条件和恢复能力的 Agent |
| S04 上下文与知识 | C05(第 8 章、第 9 章);C04(知识库与 RAG 应用);C08(模块 5 记忆) | C09(上下文取舍、检索、压缩与长任务);C14(检索质量诊断、查询与召回优化);C15(长期记忆与 LangMem);C06(Unit 3 Agentic RAG) | 检索、引用、记忆与上下文预算 |
| S05 协作与评测 | C05(第 12 章);C08(模块 4 协作);C10(配置、断言、Provider、结果对比) | C16(系统化评测与迭代);C17(按需加载的技能);C18(把 LLM 评测接入变更检查和 CI) | 版本比较、失败分析、受控协作 |
| S06 生产工程 | C03(镜像、应用栈、健康检查与环境配置);C08(模块 6 部署);C11(LLMOps) | C19(环境要求、批量推理和在线服务、性能指标) | 可部署、可诊断、可回退的版本 |
| S07 综合交付 | C05(第 14 章、第 16 章);C20(README 与架构、入口、工具、上下文、沙箱、子代理、Skill 与持久化) | C11(UX for Language User Interfaces、askFSDL 项目讲解) | 可演示、可评测的综合项目 |

## 最少选课组合

已有开发基础时,先完成 C04、C05 的指定章节、C07、C08、C10 和 C03/C11 的指定内容。C06 可替代部分基础阅读,避免重复;DeepLearning.AI 专项均作为选修,不依赖其付费功能完成主线。

第一周就建立少量固定任务,后续逐步增加评测。多 Agent 和 GPU 推理部署在出现实际需求时再扩展。

## 与现有仓库的连接

| 入口 | 路径 | 学习动作 |
|---|---|---|
| 模型调用:models.py | [../platform/fde_product/models.py](../platform/fde_product/models.py) | 画出请求、重试、返回和用量统计链路;配套模型配置文档 |
| 模型配置 | [../docs/model-configuration.md](../docs/model-configuration.md) | 模型环境变量与网关配置说明 |
| 工具与业务:business.py | [../platform/fde_product/business.py](../platform/fde_product/business.py) | 区分分析与写入动作,检查校验与执行边界 |
| 工具与业务:actions.py | [../platform/fde_product/actions.py](../platform/fde_product/actions.py) | 区分分析与写入动作,检查校验与执行边界 |
| Agent:agent.py | [../platform/fde_product/agent.py](../platform/fde_product/agent.py) | 追踪状态、澄清、确认与任务结束 |
| 交互:interaction.py | [../platform/fde_product/interaction.py](../platform/fde_product/interaction.py) | 追踪状态、澄清、确认与任务结束 |
| 评测说明 | [../evals/README.md](../evals/README.md) | 对照现有场景,补充学习用失败分类 |
| 产品测试 | [../tests](../tests) | 对照现有场景,补充学习用失败分类 |
| 可观测性 | [../platform/fde_product/observability.py](../platform/fde_product/observability.py) | 从执行记录定位模型或工具故障 |
| FDE W1 立项材料 | [../course-materials/w01/00_使用说明.md](../course-materials/w01/00_使用说明.md) | 从业务目标推导指标、证据与接管节点 |

以上是研读入口,不代表现有产品已经包含 MCP、RAG 或完整学习路线中的所有能力。先在独立练习中实现,再判断是否适合产品。

## 课程之外仍需自行完成

通用课程不能直接提供本项目的工具权限规则、幂等策略、租户隔离、真实成本基线和业务验收标准。这些内容通过每周实践补齐。源码研究记录实际 commit/tag;课程代码依赖按其版本安装,迁移到产品前另做兼容验证。
