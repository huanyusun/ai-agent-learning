"""更新报告:把 observations 与 candidates 整理为人工可读的 Markdown。

报告只描述自动观测结果;标题、费用、章节、A/B 核查等人工数据不受影响。
同一输入重复渲染结果一致(确定性),便于 build --check 与测试。
"""

from __future__ import annotations

import html

REPORT_BANNER = (
    "<!-- 本文件由 tools/learning_hub 生成;请勿手工编辑,改动会被 build 覆盖。\n"
    "     数据来源:learning/data/observations.json 与 learning/data/candidates.json(自动观测数据)\n"
    "     重新生成:python3 -m tools.learning_hub build(或 refresh/discover --apply)\n"
    "     漂移检查:python3 -m tools.learning_hub build --check -->"
)

_OK_STATUSES = ("reachable", "redirected")
_ANOMALY_STATUSES = (
    "restricted",
    "rate_limited",
    "missing_once",
    "likely_unavailable",
    "network_error",
    "unsupported_content",
)

STATUS_LABELS = {
    "reachable": "可达",
    "redirected": "重定向(链接变化)",
    "restricted": "受限(403/登录/robots)",
    "rate_limited": "限流",
    "missing_once": "单次缺失",
    "likely_unavailable": "疑似失效",
    "network_error": "网络错误",
    "unsupported_content": "正文未定位",
}

CANDIDATE_STATUS_LABELS = {"new": "新候选", "accepted": "已接受", "dismissed": "已忽略"}


def _esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def render_update_report(observations: dict, candidates: dict) -> str:
    """渲染最近一次更新摘要;输入为空时如实说明,不编造时间或结论。"""
    observations = observations or {}
    candidates = candidates or {}
    courses = observations.get("courses") or {}
    lines: list[str] = [
        REPORT_BANNER,
        "",
        "# 最近一次更新摘要(生成)",
        "",
    ]

    lines.append("## 课程来源检查")
    lines.append("")
    if not courses:
        lines.append("尚无检查记录:运行 `python3 -m tools.learning_hub refresh --apply` 后,这里会出现真实结果。")
        lines.append("")
    else:
        last_run = observations.get("last_run_at") or "未知时间"
        counts: dict[str, int] = {}
        for record in courses.values():
            counts[record.get("status", "?")] = counts.get(record.get("status", "?"), 0) + 1
        total = len(courses)
        summary = ", ".join(f"{status} {count}" for status, count in sorted(counts.items()))
        lines.append(f"运行时间:{_esc(str(last_run))}(UTC);检查总数 {total} 门。")
        lines.append("")
        lines.append("状态计数:" + ";".join(
            f"{STATUS_LABELS.get(status, status)}({status}){count}" for status, count in sorted(counts.items())
        ) + "。")
        lines.append("")

        baseline = [
            course_id
            for course_id, record in courses.items()
            if "首次建立内容基线" in (record.get("note") or "")
        ]
        changed = [
            course_id
            for course_id, record in courses.items()
            if record.get("content_changed")
        ]
        redirected = [
            course_id
            for course_id, record in courses.items()
            if record.get("status") == "redirected"
        ]
        if baseline:
            lines.append(
                f"**首次建立基线 {len(baseline)} 门({_esc(', '.join(sorted(baseline)))}):这是第一次成功读取正文,不是内容更新。**"
            )
            lines.append("")
        if changed:
            lines.append(f"### 正文变化提醒({len(changed)} 门)")
            lines.append("")
            for course_id in sorted(changed):
                note = courses[course_id].get("note") or ""
                lines.append(f"- {course_id}:{_esc(note)}")
            lines.append("")
            lines.append(
                "正文变化只表示页面内容与上次不同,需要人工复核;自动流程不会修改课程标题、费用、"
                "主修/选修、阶段映射、指定章节、周计划和学习进度。"
            )
            lines.append("")
        else:
            lines.append("未发现正文变化。")
            lines.append("")
        if redirected:
            lines.append(f"链接变化(重定向):{', '.join(sorted(redirected))};最终地址见 observations.json 的 final_url。")
            lines.append("")

        anomalies = [
            (course_id, courses[course_id])
            for course_id in sorted(courses)
            if courses[course_id].get("status") in _ANOMALY_STATUSES
        ]
        network_failures = [
            course_id
            for course_id, record in courses.items()
            if record.get("status") == "network_error"
        ]
        if network_failures and len(network_failures) == total:
            lines.append(
                f"**全部 {total} 门课程检查失败(网络错误):通常是本机网络问题,不代表课程下架;请恢复网络后重新运行。**"
            )
            lines.append("")
        if anomalies:
            lines.append(f"### 异常与需关注({len(anomalies)} 门)")
            lines.append("")
            for course_id, record in anomalies:
                status = record.get("status", "?")
                note = record.get("note") or ""
                lines.append(f"- {course_id}:{STATUS_LABELS.get(status, status)} —— {_esc(note)}")
            lines.append(
                "403/429/超时不等同于课程下架;首个 404/410 仅提示,"
                "连续两次独立运行才标记疑似失效;任何异常都不会删除课程。"
            )
            lines.append("")

    lines.append("## 候选课程(未纳入学习路径)")
    lines.append("")
    candidate_items = candidates.get("candidates") or []
    source_checks = candidates.get("source_checks") or {}
    failed_sources = [sid for sid, check in source_checks.items() if check.get("status") != "ok"]
    new_items = [item for item in candidate_items if item.get("status") == "new"]

    if source_checks:
        for source_id, check in sorted(source_checks.items()):
            note = check.get("note") or ""
            month = check.get("last_success_month") or "—"
            if check.get("status") == "ok":
                lines.append(f"- 来源 {_esc(source_id)}:正常,最近成功月份 {month}。")
            else:
                lines.append(f"- 来源 {_esc(source_id)}:**发现失败** —— {_esc(note)}")
        lines.append("")
    if failed_sources:
        lines.append(
            f"注意:有 {len(failed_sources)} 个来源发现失败;失败不代表没有新课程,"
            "也不影响已有候选记录,下月运行会继续重试失败来源。"
        )
        lines.append("")
    if new_items:
        lines.append(f"新候选 {len(new_items)} 条(仅列出,不自动加入学习路径):")
        lines.append("")
        for item in new_items:
            title = _esc(item.get("title") or item.get("url") or "")
            lines.append(f"- [{title}]({item.get('url')})(来源 {_esc(item.get('source_id') or '?')})")
        lines.append("")
    elif not failed_sources and source_checks:
        lines.append("没有发现新候选:本次目录检查成功,但目录中没有学习路径之外的新课程入口。")
        lines.append("")
    elif failed_sources and not new_items:
        lines.append(
            "没有发现新候选;注意:上文有来源发现失败——失败说明本次没能完成检查,"
            "不代表目录里没有新课程,失败来源下月会继续重试。"
        )
        lines.append("")
    if candidate_items:
        accepted = sum(1 for item in candidate_items if item.get("status") == "accepted")
        dismissed = sum(1 for item in candidate_items if item.get("status") == "dismissed")
        if accepted or dismissed:
            lines.append(
                f"候选累计 {len(candidate_items)} 条:新候选 {len(new_items)}、已接受 {accepted}、已忽略 {dismissed};"
                f"最近发现月份 {candidates.get('last_discovery_month') or '—'}。"
            )
            lines.append("")

    lines.append("## 固定说明")
    lines.append("")
    lines.append(
        "- 课程标题、费用、主修/选修、阶段映射、指定章节、周计划属于人工策划数据,"
        "自动流程不会修改;展示“费用待核查”时不推断免费。"
    )
    lines.append("- 外站课程更新不会自动同步到个人学习进度;个人进度只存在本机浏览器。")
    lines.append(
        "- `file://` 与 `localhost:8000` 打开页面时浏览器视为不同来源,"
        "进度互不相通;切换入口请先用页面「导出进度 JSON」,再到新入口「导入进度 JSON」。"
    )
    lines.append(
        "- 恢复与维护步骤见 [MAINTENANCE.md](../MAINTENANCE.md);"
        "自动数据可随时从 Git 历史恢复后重新 build。"
    )
    lines.append("")
    return "\n".join(lines)
