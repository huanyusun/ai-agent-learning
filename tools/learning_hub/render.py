"""由 catalog 生成 Markdown 导航与静态页面。

输出全部由 build_outputs 确定性生成:同一输入字节一致,便于 build --check。
整段人工策划文字(如何开始、最少选课组合、覆盖边界等)保存在本文件
CURATED_* 常量中;编辑这些文字请改这里,再运行 build 重建。
自动观测数据只来自 observations.json,本模块不改写 catalog。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO_ROOT / "learning" / "web" / "template.html"
DATA_PLACEHOLDER = "__LEARNING_HUB_DATA__"

KIND_LABELS = {
    "video_course": "视频课",
    "text_course": "图文课",
    "documentation": "文档教程",
    "article": "文章",
    "source_code": "源码",
}
COST_LABELS = {
    "free_content": "内容免费",
    "mixed": "部分免费",
    "unknown": "费用待核查",
}
PRIORITY_LABELS = {"core": "主修", "elective": "选修"}

BANNER_MD = (
    "<!-- 本文件由 tools/learning_hub 生成;请勿手工编辑,改动会被 build 覆盖。\n"
    "     数据来源:learning/data/catalog.json(人工策划数据)\n"
    "     重新生成:python3 -m tools.learning_hub build\n"
    "     漂移检查:python3 -m tools.learning_hub build --check\n"
    "     整段人工文字在 tools/learning_hub/render.py 的 CURATED_* 常量中维护;\n"
    "     迁移前的人工原稿存档于上游仓库 huanyusun/fde-study(提交 7aea723)。 -->"
)

BANNER_HTML = (
    "<!-- 由 tools/learning_hub 生成;请勿手工编辑,改动会被 build 覆盖。\n"
    "     数据来源:learning/data/catalog.json;重建:python3 -m tools.learning_hub build;\n"
    "     漂移检查:python3 -m tools.learning_hub build --check。 -->"
)

CURATED_COURSES_INTRO = (
    "核查日期:2026-10-28(人工核查,固定保留)。优先使用课程提供方、项目维护者和大学官网。"
    "建议投入包含练习,是本项目估算,不是官方时长。"
)
CURATED_REVIEW_LEGEND = (
    "核查标记:**A**=已读取官方课程/教程页面;**B**=官方目录或官方搜索摘要确认存在,"
    "但详情页抓取返回 403。未登录验证完整课堂、实验或证书。"
    "免费阅读不等于模型 API、云服务、GPU 或证书免费。"
)
CURATED_DEEPLARNING_NOTE = (
    "> C12–C18:以下课程已在 [DeepLearning.AI 官方课程目录]"
    "(https://www.deeplearning.ai/courses?types=short_course)或官方课程搜索摘要中查到;"
    "本次详情页直接访问返回 403。保留直达入口,若访问失败,在官方目录搜索英文全名。"
    "未确认当前账号下的免费范围、字幕和实验权限,因此不填写确定价格,也不作为必修依赖。"
)
CURATED_COURSE_BOUNDARY = [
    "中文主线:C04/C05;框架主线:C08;协议主线:C07。它们组合覆盖原大纲的大部分主题。",
    "C01/C02/C03 补基础,已有经验可用实践验收跳过。",
    "C09/C19/C20 是课程之外的补充材料;C11 明确是历史课程。",
    "C12–C18 用于专项补充,不把目录说明当成已验证全部课堂。主线中均有公开替代入口。",
    "完整生产治理仍需项目实践:权限、幂等、日志脱敏、回滚、预算和业务验收不能靠看课替代。",
    "未购买课程、注册账号或付费调用模型。资源表仅链接原内容,不复制课程正文或教学视频。",
]
CURATED_WEEKLY_INTRO = (
    "课程编号对应[资源目录](courses.md)。按每周 8–12 小时规划,已有编程基础;"
    "基础不足先完成 C01/C02。课程投入包含在周预算内,选修只针对短板。"
)
CURATED_WEEKLY_STATUS = (
    "状态统一用:未开始 / 进行中 / 已完成 / 待复盘。完成一周需要交付可检查成果,"
    "观看视频不直接等于完成。个人学习进度保存在 [learning/index.html](index.html) 页面"
    "(本机存储,支持导入导出),不再写在本表;自动化流程也不会修改个人进度。"
)
CURATED_CAPSTONE = """## 综合项目二选一

### A. 证据可追溯的研究助手

输入一项明确研究问题,检索公开来源,输出结构化结论、引用与未知项。先限制来源范围,再增加冲突核验和人工复核。用可回答/不可回答问题、冲突来源和过期资料测试系统。

交付:报告、来源索引、任务 Trace、人工评分与成本记录。

### B. 受控的代码库助手

输入代码理解、补测试或小型修复任务,在隔离副本中执行搜索、读取、修改和测试。开始时只支持小范围任务,再加入审查、失败恢复和 CI 对接。

交付:变更 diff、测试记录、审查报告、任务 Trace 与恢复演示。"""
CURATED_W1_RELATION = """## 与 W1 交付的关系

这里的周数是 AI 工程学习进度,与 FDE 的课程周编号独立。练习数据、评测和输出放 `learning/`,避免覆盖 `contracts/w01/`、`artifacts/w01/` 和课程要求的固定交付物。真实客户材料和日志使用前先脱敏。"""
CURATED_README_INTRO = (
    "从[完整学习大纲](../AI学习路径与大纲.md)出发,按能力依赖组织网上课程,并配套本仓库实践。"
    "资源核查日期:2026-10-28。"
)
CURATED_README_NEXT = (
    "下一步建设:[统一课程中心与自动更新实施计划]"
    "(../docs/superpowers/plans/2026-10-28-learning-hub.md),"
    "以及[GLM-5.3-Flash 执行提示词](GLM-HANDOFF.md)。"
)
CURATED_HOW_TO_START = [
    "Python 不熟先补阶段 0;能独立开发 API 的学习者可直接进入第 1 周。",
    "按下表选择指定内容,详细链接和核查状态见[课程资源目录](courses.md)。",
    "每周按[实践与进度表](weekly-plan.md)产出一个可检查的结果。",
    "在 `learning/notes/` 保存笔记,在 `learning/labs/` 放独立练习,在 `learning/outputs/` 保存脱敏的报告。这些目录按实际需要建立。",
]
CURATED_README_PREFERENCE = (
    "优先读中文主线;用英文官方课程补充状态机、MCP 和部署。主修表示本项目的学习建议,"
    "选修用于补短板。文档教程、工程文章和源码案例已明确标出,不将它们当作视频课。"
    "推荐从[统一课程中心页面](index.html)搜索、筛选并跟踪个人进度。"
)
CURATED_MINIMAL_COMBO = """## 最少选课组合

已有开发基础时,先完成 C04、C05 的指定章节、C07、C08、C10 和 C03/C11 的指定内容。C06 可替代部分基础阅读,避免重复;DeepLearning.AI 专项均作为选修,不依赖其付费功能完成主线。

第一周就建立少量固定任务,后续逐步增加评测。多 Agent 和 GPU 推理部署在出现实际需求时再扩展。"""
CURATED_README_BEYOND = """## 课程之外仍需自行完成

通用课程不能直接提供本项目的工具权限规则、幂等策略、租户隔离、真实成本基线和业务验收标准。这些内容通过每周实践补齐。源码研究记录实际 commit/tag;课程代码依赖按其版本安装,迁移到产品前另做兼容验证。"""


def build_outputs(catalog: dict, observations: dict, candidates: dict) -> dict[str, str]:
    """根据 catalog 与自动数据生成全部输出文件内容;路径为仓库相对路径。"""
    from tools.learning_hub.report import render_update_report

    return {
        "learning/index.html": _render_html(catalog, observations, candidates),
        "learning/README.md": _render_readme(catalog),
        "learning/courses.md": _render_courses_md(catalog),
        "learning/weekly-plan.md": _render_weekly_md(catalog),
        "learning/updates/latest.md": render_update_report(observations, candidates),
    }


def write_outputs(outputs: dict[str, str], repo_root: Path) -> None:
    """原子写入生成文件:先写临时文件,成功后再替换,失败不截断现有文件。"""
    for rel, content in outputs.items():
        path = repo_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)


def check_outputs(outputs: dict[str, str], repo_root: Path) -> list[str]:
    """比较磁盘文件与生成结果;返回漂移列表(含缺失),不写任何文件。"""
    drift: list[str] = []
    for rel, content in outputs.items():
        path = repo_root / rel
        if not path.exists():
            drift.append(f"{rel}: 缺失")
        elif path.read_text(encoding="utf-8") != content:
            drift.append(f"{rel}: 与生成结果不一致")
    return drift


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def _render_html(catalog: dict, observations: dict, candidates: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = {"catalog": catalog, "observations": observations, "candidates": candidates}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    # 内嵌 <script> 前转义 < > &,防止 "</script>" 提前闭合标签或触发 HTML 解析。
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    count = template.count(DATA_PLACEHOLDER)
    if count != 1:
        raise ValueError(
            f"模板占位符 {DATA_PLACEHOLDER} 必须恰好出现一次,当前 {count} 次:{TEMPLATE_PATH}"
        )
    return template.replace(DATA_PLACEHOLDER, text)


# ---------------------------------------------------------------------------
# 共用格式化
# ---------------------------------------------------------------------------


def _md_escape(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _fmt_effort(effort: dict) -> str:
    low, high = effort.get("min"), effort.get("max")
    note = effort.get("note", "")
    if low == 0 and high == 0:
        base = "原目录未估算"
    elif low == high:
        base = f"{low}h"
    else:
        base = f"{low}–{high}h"
    return f"{base}{';' + note if note else ''}"


def _fmt_review(review: dict) -> str:
    level = review.get("level", "?")
    date = review.get("reviewed_on", "")
    note = review.get("note", "")
    return f"{level}({date}){'；' + note if note else ''}"


def _course_assignments(catalog: dict) -> dict[str, list[dict]]:
    mapping: dict[str, list[dict]] = {}
    for stage in catalog["stages"]:
        for assignment in stage["assignments"]:
            mapping.setdefault(assignment["course_id"], []).append(
                {"stage": stage, "assignment": assignment}
            )
    return mapping


def _scope_cell(catalog: dict, course_id: str) -> str:
    entries = _course_assignments(catalog).get(course_id, [])
    parts = []
    for entry in entries:
        assignment = entry["assignment"]
        priority = PRIORITY_LABELS.get(assignment["priority"], assignment["priority"])
        parts.append(
            f"{entry['stage']['title']}({entry['stage']['id']}){priority}:"
            + "、".join(assignment["sections"])
        )
    return ";".join(parts) if parts else "未指定"


# ---------------------------------------------------------------------------
# Markdown:课程资源目录
# ---------------------------------------------------------------------------


def _render_courses_md(catalog: dict) -> str:
    lines: list[str] = [BANNER_MD, "", "# 课程资源目录(生成)", ""]
    lines.append(CURATED_COURSES_INTRO)
    lines.append("")
    lines.append(CURATED_REVIEW_LEGEND)
    lines.append("")
    lines.append(
        "| ID | 课程 / 资源 | 提供方 | 语言 | 形式 | 访问与费用 | 指定学习范围与对应阶段 "
        "| 建议投入 | 核查 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for course in catalog["courses"]:
        access = f"{course['access_note']};费用:{course['cost_note']}"
        title = _md_escape(course["title"])
        row = (
            f"| {course['id']} | [{title}]({course['url']}) | {_md_escape(course['provider'])} "
            f"| {course['language']} | {KIND_LABELS[course['kind']]} "
            f"| {_md_escape(access)} | {_md_escape(_scope_cell(catalog, course['id']))} "
            f"| {_md_escape(_fmt_effort(course['effort_hours']))} "
            f"| {_md_escape(_fmt_review(course['manual_review']))} |"
        )
        lines.append(row)
    lines.append("")
    lines.append(CURATED_DEEPLARNING_NOTE)
    lines.append("")
    lines.append("## 覆盖边界与选择依据")
    lines.append("")
    for item in CURATED_COURSE_BOUNDARY:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown:18 周计划
# ---------------------------------------------------------------------------


def _render_weekly_md(catalog: dict) -> str:
    stage_titles = {stage["id"]: stage["title"] for stage in catalog["stages"]}
    lines: list[str] = [BANNER_MD, "", "# 18 周学习、实践与进度表(生成)", ""]
    lines.append(CURATED_WEEKLY_INTRO)
    lines.append("")
    lines.append(CURATED_WEEKLY_STATUS)
    lines.append("")
    lines.append("## 每周安排")
    lines.append("")
    lines.append("| 周 | 阶段 | 必修内容(作业 ID) | 仓库关联或独立练习 | 本周交付 | 验收 |")
    lines.append("|---|---|---|---|---|---|")
    for week in catalog["weeks"]:
        study = ";".join(week["study"])
        refs = "、".join(week["assignment_ids"])
        required_cell = f"{_md_escape(study)}<br>({refs})"
        practice = _md_escape(";".join(week["practice"]))
        deliverables = _md_escape(";".join(week["deliverables"]))
        acceptance = _md_escape(";".join(week["acceptance"]))
        repo = _md_escape(";".join(week["repo_paths"])) if week["repo_paths"] else "—"
        row = (
            f"| {week['id']} | {stage_titles.get(week['stage_id'], week['stage_id'])} "
            f"| {required_cell} | {repo or '—'} | {deliverables} | {acceptance} |"
        )
        lines.append(row)
    lines.append("")
    lines.append("## 学习记录模板")
    lines.append("")
    lines.append(
        "见 [templates/weekly-note.md](templates/weekly-note.md);"
        "复制为 `learning/notes/wXX.md` 使用,不预建空文件。"
    )
    lines.append("")
    lines.append(CURATED_CAPSTONE)
    lines.append("")
    lines.append(CURATED_W1_RELATION)
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown:课程导航 README
# ---------------------------------------------------------------------------


def _render_readme(catalog: dict) -> str:
    lines: list[str] = [BANNER_MD, "", "# AI Agent 工程课程导航(生成)", ""]
    lines.append(CURATED_README_INTRO)
    lines.append("")
    lines.append(
        "统一入口:[learning/index.html](index.html)——搜索、筛选、18 周进度与导入导出都在这一个页面。"
    )
    lines.append("")
    lines.append(CURATED_README_NEXT)
    lines.append("")
    lines.append("## 如何开始")
    lines.append("")
    for index, item in enumerate(CURATED_HOW_TO_START, start=1):
        lines.append(f"{index}. {item}")
    lines.append("")
    lines.append(CURATED_README_PREFERENCE)
    lines.append("")
    lines.append("## 分阶段选课")
    lines.append("")
    lines.append("| 阶段 | 主修与指定内容 | 选修 | 学完要能完成 |")
    lines.append("|---|---|---|---|")
    for stage in catalog["stages"]:
        core = ";".join(
            f"{a['course_id']}({'、'.join(a['sections'])})"
            for a in stage["assignments"]
            if a["priority"] == "core"
        )
        elective = ";".join(
            f"{a['course_id']}({'、'.join(a['sections'])})"
            for a in stage["assignments"]
            if a["priority"] == "elective"
        )
        goal = stage["acceptance"][0] if stage["acceptance"] else ""
        lines.append(
            f"| {stage['id']} {stage['title']} | {_md_escape(core) or '—'} "
            f"| {_md_escape(elective) or '—'} | {_md_escape(goal)} |"
        )
    lines.append("")
    lines.append(CURATED_MINIMAL_COMBO)
    lines.append("")
    lines.append("## 与现有仓库的连接")
    lines.append("")
    lines.append("| 入口 | 路径 | 学习动作 |")
    lines.append("|---|---|---|")
    for link in catalog["repo_links"]:
        lines.append(
            f"| {_md_escape(link['label'])} | [../{link['path']}](../{link['path']}) "
            f"| {_md_escape(link['description'])} |"
        )
    lines.append("")
    lines.append(
        "以上是研读入口,不代表现有产品已经包含 MCP、RAG 或完整学习路线中的所有能力。"
        "先在独立练习中实现,再判断是否适合产品。"
    )
    lines.append("")
    lines.append(CURATED_README_BEYOND)
    lines.append("")
    return "\n".join(lines)
