# AI Agent 工程学习中心(ai-agent-learning)

从零构建能调用工具、检索知识、恢复失败、通过评测并部署运行的 Agent 系统——课程目录、分阶段路径、18 周实践与自动化来源检查,都在这一个仓库。

## 统一入口

- **页面:`learning/index.html`**——双击直接打开(file:// 可用,无 CDN、无运行时请求):搜索、筛选、18 周进度跟踪与导入导出。
- [学习路径与能力大纲](AI学习路径与大纲.md) · [课程导航](learning/README.md) · [课程资源目录](learning/courses.md) · [18 周实践表](learning/weekly-plan.md) · [最近更新报告](learning/updates/latest.md)

## 目录结构

```
├── learning/                # 学习中心:数据、生成文件、维护文档
│   ├── data/                #   catalog.json(人工策划)/ observations.json(自动)/ candidates.json(自动)/ sources.json
│   ├── templates/           #   每周学习记录模板
│   ├── web/template.html    #   页面源文件(生成 index.html)
│   ├── updates/latest.md    #   最近一次更新摘要(生成)
│   ├── MAINTENANCE.md       #   维护手册:改课程、处理候选、恢复数据
│   └── IMPLEMENTATION-RESULTS.md  # 实施与验收记录
├── tools/learning_hub/      # 校验、生成、抓取、发现、报告
├── tests/learning_hub/      # 离线测试(不访问公网)
├── platform/fde_product/    # 研读引用:课程产品源码(只读参考)
├── evals/                   # 研读引用:Promptfoo 评估配置
└── .github/workflows/       # CI + 每周定时刷新
```

## 常用命令

```sh
python3 -m tools.learning_hub validate        # 校验课程数据
python3 -m tools.learning_hub build           # 重新生成页面与 Markdown
python3 -m tools.learning_hub build --check   # 检测生成漂移
python3 -m tools.learning_hub refresh         # 检查课程链接(默认写 .runtime/)
python3 -m tools.learning_hub discover        # 官方目录候选发现(默认写 .runtime/)
python3 -m pytest tests/learning_hub -q       # 离线测试
python3 -m http.server 8000 --bind 127.0.0.1  # 本地预览 /learning/
```

需要 pytest:`python3 -m pip install pytest`。

## 数据边界

- `catalog.json` 是人工策划数据(课程、阶段、章节、周计划、费用、A/B 核查),只有人改;
- `observations.json` / `candidates.json` 只由 `refresh` / `discover --apply` 写;
- 个人学习进度只存本机浏览器(localStorage),导出/导入迁移,不进 Git。

自动流程不会修改标题、费用、学习顺序;403/429/超时不等于课程下架。维护步骤见 [learning/MAINTENANCE.md](learning/MAINTENANCE.md)。

## 自动化

- `learning-hub-ci`:改动学习文件时跑 validate + 离线测试 + 漂移检查。
- `learning-hub-refresh`:每周一 UTC 01:17(北京时间 09:17)检查课程链接;每月(或手动勾选)从 Hugging Face Learn、LangChain Academy 两个官方目录发现候选课程;结果经固定分支 PR 提交,人工审核合并。

## 来源

2026-10 从 [huanyusun/fde-study](https://github.com/huanyusun/fde-study) 的学习模块独立而来;FDE 课程交付仍在上游仓库进行。
