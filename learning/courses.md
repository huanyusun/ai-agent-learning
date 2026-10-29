<!-- 本文件由 tools/learning_hub 生成;请勿手工编辑,改动会被 build 覆盖。
     数据来源:learning/data/catalog.json(人工策划数据)
     重新生成:python3 -m tools.learning_hub build
     漂移检查:python3 -m tools.learning_hub build --check
     整段人工文字在 tools/learning_hub/render.py 的 CURATED_* 常量中维护;
     迁移前的人工原稿存档于上游仓库 huanyusun/fde-study(提交 7aea723)。 -->

# 课程资源目录(生成)

核查日期:2026-10-28(人工核查,固定保留)。优先使用课程提供方、项目维护者和大学官网。建议投入包含练习,是本项目估算,不是官方时长。

核查标记:**A**=已读取官方课程/教程页面;**B**=官方目录或官方搜索摘要确认存在,但详情页抓取返回 403。未登录验证完整课堂、实验或证书。免费阅读不等于模型 API、云服务、GPU 或证书免费。

| ID | 课程 / 资源 | 提供方 | 语言 | 形式 | 访问与费用 | 指定学习范围与对应阶段 | 建议投入 | 核查 |
|---|---|---|---|---|---|---|---|---|
| C01 | [CS50's Introduction to Programming with Python](https://cs50.harvard.edu/python/) | Harvard | 英文 | 视频课 | OCW 内容公开;提交作业需账号;费用:OCW 内容公开;认证另看官方选项 | 工程基础(S00)主修:函数、异常、单元测试、文件、面向对象 | 20–40h;选学;零基础更长 | A(2026-10-28)；已读取官方课程页面 |
| C02 | [FastAPI 教程:用户指南](https://fastapi.tiangolo.com/zh/tutorial/) | FastAPI | 中文 | 文档教程 | 免费公开;费用:免费公开 | 工程基础(S00)主修:请求体、响应模型、错误处理、依赖、安全、测试;模型调用(S01)选修:流式传输 | 8–12h | A(2026-10-28)；已读取官方文档页面 |
| C03 | [Get started with Docker](https://docs.docker.com/get-started/) | Docker | 英文 | 文档教程 | 教程公开;软件和托管服务需按对应许可获取;费用:教程公开;软件和托管服务按对应许可/套餐 | 工程基础(S00)选修:容器、镜像、应用栈;生产工程(S06)主修:镜像、应用栈、健康检查与环境配置 | 6–10h | A(2026-10-28)；已读取官方教程页面 |
| C04 | [LLM Universe:大模型应用开发](https://github.com/datawhalechina/llm-universe) | Datawhale | 中文 | 图文课 | 仓库公开;费用:公开;模型调用可能收费 | 模型调用(S01)主修:模型 API 入门、Prompt 内容;上下文与知识(S04)主修:知识库与 RAG 应用 | 12–20h;选学 | A(2026-10-28)；已读取仓库页面 |
| C05 | [Hello-Agents:从零开始构建智能体](https://github.com/datawhalechina/hello-agents) | Datawhale | 中文 | 图文课 | 仓库公开;部分内容有配套视频;费用:公开;外部模型和服务另计 | 模型调用(S01)主修:第 3 章;工具接入(S02)主修:第 10 章 MCP 部分;Agent 执行(S03)主修:第 4 章、第 7 章;上下文与知识(S04)主修:第 8 章、第 9 章;协作与评测(S05)主修:第 12 章;综合交付(S07)主修:第 14 章、第 16 章 | 25–40h;选学 | A(2026-10-28)；已读取仓库页面 |
| C06 | [Hugging Face AI Agents Course](https://huggingface.co/learn/agents-course/en/unit0/introduction) | Hugging Face | 英文 | 图文课 | 部分实践/提交需账号;费用:免费课程;推理资源另计 | Agent 执行(S03)选修:Unit 1、Unit 2.3 LangGraph;上下文与知识(S04)选修:Unit 3 Agentic RAG | 8–15h;选学 | A(2026-10-28)；已读取官方课程页面 |
| C07 | [Hugging Face MCP Course](https://huggingface.co/learn/mcp-course/en/unit0/introduction) | Hugging Face × Anthropic | 英文 | 图文课 | 发布应用需账号;费用:免费课程;资源另计 | 工具接入(S02)主修:架构、Client/Server、工具/资源/提示模板、端到端应用 | 8–12h | A(2026-10-28)；已读取官方课程页面 |
| C08 | [Introduction to LangGraph — Python](https://academy.langchain.com/courses/intro-to-langgraph) | LangChain Academy | 英文 | 视频课 | 注册学习;费用:页面标明免费;模型与托管服务另计 | Agent 执行(S03)主修:模块 1 图与 Agent、模块 2 状态、模块 3 人机协同;上下文与知识(S04)主修:模块 5 记忆;协作与评测(S05)主修:模块 4 协作;生产工程(S06)主修:模块 6 部署 | 15–25h;官方视频 6h | A(2026-10-28)；已读取官方课程页面 |
| C09 | [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | Anthropic | 英文 | 文章 | 公开;费用:公开 | 上下文与知识(S04)选修:上下文取舍、检索、压缩与长任务 | 2–3h | A(2026-10-28)；已读取文章页面 |
| C10 | [Promptfoo Intro](https://www.promptfoo.dev/docs/intro/) | Promptfoo | 英文 | 文档教程 | 文档公开;本仓库已有 CLI 用法;费用:文档公开;模型/云功能另计 | 协作与评测(S05)主修:配置、断言、Provider、结果对比 | 5–8h | A(2026-10-28)；已读取官方文档 |
| C11 | [Full Stack LLM Bootcamp — Spring 2023](https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/) | Full Stack Deep Learning | 英文 | 视频课 | 官网公开访问;费用:官网标明免费 | 生产工程(S06)主修:LLMOps;综合交付(S07)选修:UX for Language User Interfaces、askFSDL 项目讲解 | 6–10h;选学 | A(2026-10-28)；2023 年材料,工程原则有参考价值,API 和工具示例需核对 |
| C12 | [ChatGPT Prompt Engineering for Developers](https://www.deeplearning.ai/courses/chatgpt-prompt-eng) | DeepLearning.AI × OpenAI | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:官方摘要出现限时免费说明,当前权益需在课堂确认 | 模型调用(S01)选修:指令、示例、迭代和文本处理 | 2–4h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;实际模型调用沿用项目当前适配层 |
| C13 | [Functions, Tools and Agents with LangChain](https://www.deeplearning.ai/courses/functions-tools-agents-langchain) | DeepLearning.AI × LangChain | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:免费范围/PRO 作业以登录后页面为准 | 工具接入(S02)选修:结构输出、工具选择和路由 | 3–5h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;早期 LCEL/API 示例只用于概念对照 |
| C14 | [Advanced Retrieval for AI with Chroma](https://www.deeplearning.ai/courses/advanced-retrieval-for-ai) | DeepLearning.AI × Chroma | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:费用待确认 | 上下文与知识(S04)选修:检索质量诊断、查询与召回优化 | 3–5h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;另补 BM25 与权限过滤练习 |
| C15 | [Long-Term Agentic Memory With LangGraph](https://www.deeplearning.ai/courses/long-term-agentic-memory-with-langgraph) | DeepLearning.AI × LangChain | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:费用待确认 | 上下文与知识(S04)选修:长期记忆与 LangMem | 3–5h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;与 C08 模块 5 内容重叠时选一门 |
| C16 | [Evaluating AI Agents](https://www.deeplearning.ai/courses/evaluating-ai-agents) | DeepLearning.AI × Arize AI | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:费用待确认 | 协作与评测(S05)选修:系统化评测与迭代 | 4–6h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;实践迁移到本仓库固定任务集 |
| C17 | [Agent Skills with Anthropic](https://www.deeplearning.ai/courses/agent-skills-with-anthropic) | DeepLearning.AI × Anthropic | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:费用待确认 | 协作与评测(S05)选修:按需加载的技能 | 4–6h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;写一份可评测的 Skill |
| C18 | [Automated Testing for LLMOps](https://www.deeplearning.ai/courses/automated-testing-llmops) | DeepLearning.AI × CircleCI | 英文 | 视频课 | 注册学习;详情页未直接核查;费用:费用待确认 | 协作与评测(S05)选修:把 LLM 评测接入变更检查和 CI | 3–5h | B(2026-10-28)；官方目录确认存在,详情页抓取返回 403;原目录标注适用阶段 5/6 |
| C19 | [vLLM Quickstart](https://docs.vllm.ai/en/latest/getting_started/quickstart/) | vLLM | 英文 | 文档教程 | 官方文档公开;费用:文档免费;算力另计 | 生产工程(S06)选修:环境要求、批量推理和在线服务、性能指标 | 原目录未估算;原目录未给出估算;需要私有化部署时开展 | A(2026-10-28)；已读取官方文档 |
| C20 | [DeerFlow 官方仓库](https://github.com/bytedance/deer-flow) | ByteDance | 英文为主 | 源码 | 仓库公开;费用:公开;模型与运行资源另计 | 综合交付(S07)主修:README 与架构、入口、工具、上下文、沙箱、子代理、Skill 与持久化 | 原目录未估算;原目录未给出估算;按所选综合项目场景开展 | A(2026-10-28)；已读取仓库页面 |

> C12–C18:以下课程已在 [DeepLearning.AI 官方课程目录](https://www.deeplearning.ai/courses?types=short_course)或官方课程搜索摘要中查到;本次详情页直接访问返回 403。保留直达入口,若访问失败,在官方目录搜索英文全名。未确认当前账号下的免费范围、字幕和实验权限,因此不填写确定价格,也不作为必修依赖。

## 覆盖边界与选择依据

- 中文主线:C04/C05;框架主线:C08;协议主线:C07。它们组合覆盖原大纲的大部分主题。
- C01/C02/C03 补基础,已有经验可用实践验收跳过。
- C09/C19/C20 是课程之外的补充材料;C11 明确是历史课程。
- C12–C18 用于专项补充,不把目录说明当成已验证全部课堂。主线中均有公开替代入口。
- 完整生产治理仍需项目实践:权限、幂等、日志脱敏、回滚、预算和业务验收不能靠看课替代。
- 未购买课程、注册账号或付费调用模型。资源表仅链接原内容,不复制课程正文或教学视频。
