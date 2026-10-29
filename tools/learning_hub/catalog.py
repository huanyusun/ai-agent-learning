"""catalog.json 的加载与离线校验。

只校验人工策划数据;自动观测结果属于 observations.json,禁止混入本文件。
所有校验错误都带字段路径,便于人工定位。数据契约见
docs/superpowers/plans/2026-10-28-learning-hub.md 第 3.1 节。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_VERSION = 1

COURSE_ID_RE = re.compile(r"^C\d{2}$")
STAGE_ID_RE = re.compile(r"^S\d{2}$")
ASSIGNMENT_ID_RE = re.compile(r"^S\d{2}-C\d{2}-\d{2}$")
WEEK_ID_RE = re.compile(r"^W\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

KINDS = {"video_course", "text_course", "documentation", "article", "source_code"}
COST_STATUSES = {"free_content", "mixed", "unknown"}
PRIORITIES = {"core", "elective"}
REVIEW_LEVELS = {"A", "B"}

EXPECTED_STAGE_IDS = [f"S0{i}" for i in range(8)]
EXPECTED_WEEK_IDS = [f"W{i:02d}" for i in range(1, 19)]

COURSE_REQUIRED_FIELDS = (
    "id",
    "title",
    "provider",
    "url",
    "language",
    "kind",
    "access_note",
    "cost_status",
    "cost_note",
    "effort_hours",
    "manual_review",
)

# 自动观测字段只允许出现在 observations.json;注意 course 自身的 note 是人工字段。
OBSERVATION_FIELDS = {
    "checked_at",
    "status",
    "http_status",
    "final_url",
    "last_success_at",
    "last_good_hash",
    "content_changed",
    "consecutive_missing",
    "missing_run_id",
    "last_checked_at",
}


def load_catalog(path: Path) -> dict:
    """读取 catalog JSON;解析失败由调用方处理异常。"""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_catalog(catalog: dict, repo_root: Path) -> list[str]:
    """校验 catalog 结构与引用完整性,返回带字段路径的错误列表;合法时为空。"""
    if not isinstance(catalog, dict):
        return ["catalog: 顶层必须是 JSON 对象"]

    errors: list[str] = []
    if catalog.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version: 必须为 1")

    top_keys = ("courses", "stages", "weeks", "repo_links")
    for key in top_keys:
        if not isinstance(catalog.get(key), list):
            errors.append(f"{key}: 缺少或不是数组")
    if any(not isinstance(catalog.get(key), list) for key in top_keys):
        return errors

    course_ids: dict[str, int] = {}
    for index, course in enumerate(catalog["courses"]):
        _validate_course(course, index, course_ids, errors)

    stage_ids: list[str] = []
    assignment_ids: dict[str, str] = {}
    for index, stage in enumerate(catalog["stages"]):
        _validate_stage(stage, index, stage_ids, course_ids, assignment_ids, errors)

    known_stage_ids = set(stage_ids)
    missing_stages = [sid for sid in EXPECTED_STAGE_IDS if sid not in known_stage_ids]
    if missing_stages:
        errors.append("stages: 缺少阶段 " + ", ".join(missing_stages))

    for index, stage in enumerate(catalog["stages"]):
        if not isinstance(stage, dict):
            continue
        prerequisites = stage.get("prerequisites")
        if isinstance(prerequisites, list):
            for prereq in prerequisites:
                if prereq not in known_stage_ids:
                    errors.append(
                        f"stages[{index}].prerequisites: 引用了不存在的阶段 {prereq}"
                    )

    cycle = _find_prerequisite_cycle(catalog["stages"])
    if cycle:
        errors.append("stages: 阶段依赖存在循环: " + " -> ".join(cycle))

    week_ids: set[str] = set()
    for index, week in enumerate(catalog["weeks"]):
        _validate_week(week, index, week_ids, known_stage_ids, assignment_ids, repo_root, errors)
    missing_weeks = [wid for wid in EXPECTED_WEEK_IDS if wid not in week_ids]
    if missing_weeks:
        errors.append("weeks: 缺少周 " + ", ".join(missing_weeks))

    _validate_repo_links(catalog["repo_links"], repo_root, errors)
    return errors


def _validate_course(course: object, index: int, course_ids: dict[str, int], errors: list[str]) -> None:
    where = f"courses[{index}]"
    if not isinstance(course, dict):
        errors.append(f"{where}: 必须是对象")
        return

    for field in sorted(OBSERVATION_FIELDS & set(course)):
        errors.append(f"{where}.{field}: 禁止写入自动观测字段(应保存在 observations.json)")

    course_id = course.get("id")
    if not isinstance(course_id, str) or not COURSE_ID_RE.match(course_id):
        errors.append(f"{where}.id: 课程 ID 缺少或不符合 C 编号格式(如 C01)")
    elif course_id in course_ids:
        errors.append(
            f"{where}.id: 课程 ID 重复({course_id},首次出现在 courses[{course_ids[course_id]}])"
        )
    else:
        course_ids[course_id] = index

    for field in COURSE_REQUIRED_FIELDS:
        if field != "id" and field not in course:
            errors.append(f"{where}.{field}: 缺少必填字段")

    url = course.get("url")
    if url is not None and not (
        isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))
    ):
        errors.append(f"{where}.url: URL 必须以 http:// 或 https:// 开头,当前为 {url!r}")

    kind = course.get("kind")
    if kind is not None and kind not in KINDS:
        errors.append(f"{where}.kind: 非法资源类型 {kind!r},允许 {sorted(KINDS)}")

    cost_status = course.get("cost_status")
    if cost_status is not None and cost_status not in COST_STATUSES:
        errors.append(f"{where}.cost_status: 非法费用状态 {cost_status!r},允许 {sorted(COST_STATUSES)}")

    effort = course.get("effort_hours")
    if effort is not None:
        if not isinstance(effort, dict):
            errors.append(f"{where}.effort_hours: 必须是含 min/max/note 的对象")
        else:
            low, high = effort.get("min"), effort.get("max")
            numbers = all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                for value in (low, high)
            )
            if not numbers:
                errors.append(f"{where}.effort_hours: min/max 必须是数字")
            else:
                if low < 0 or high < 0:
                    errors.append(f"{where}.effort_hours: min/max 不能为负")
                if low > high:
                    errors.append(f"{where}.effort_hours: min({low}) 不能大于 max({high})")
            if not isinstance(effort.get("note"), str):
                errors.append(f"{where}.effort_hours.note: 必须是字符串")

    review = course.get("manual_review")
    if review is not None:
        if not isinstance(review, dict):
            errors.append(f"{where}.manual_review: 必须是含 level/reviewed_on/note 的对象")
        else:
            if review.get("level") not in REVIEW_LEVELS:
                errors.append(f"{where}.manual_review.level: 核查级别必须是 A 或 B")
            reviewed_on = review.get("reviewed_on")
            if not isinstance(reviewed_on, str) or not DATE_RE.match(reviewed_on):
                errors.append(f"{where}.manual_review.reviewed_on: 日期必须是 YYYY-MM-DD")
            if not isinstance(review.get("note"), str):
                errors.append(f"{where}.manual_review.note: 必须是字符串")


def _validate_stage(
    stage: object,
    index: int,
    stage_ids: list[str],
    course_ids: dict[str, int],
    assignment_ids: dict[str, str],
    errors: list[str],
) -> None:
    where = f"stages[{index}]"
    if not isinstance(stage, dict):
        errors.append(f"{where}: 必须是对象")
        return

    stage_id = stage.get("id")
    if not isinstance(stage_id, str) or not STAGE_ID_RE.match(stage_id):
        errors.append(f"{where}.id: 阶段 ID 缺少或不符合格式(如 S00)")
    elif stage_id in stage_ids:
        errors.append(f"{where}.id: 阶段 ID 重复({stage_id})")
    else:
        stage_ids.append(stage_id)

    for field in ("title", "objective", "deliverables", "acceptance", "prerequisites", "assignments"):
        if field not in stage:
            errors.append(f"{where}.{field}: 缺少必填字段")

    for field in ("deliverables", "acceptance"):
        value = stage.get(field)
        if value is not None and not _is_string_array(value):
            errors.append(f"{where}.{field}: 必须是非空字符串数组")

    prerequisites = stage.get("prerequisites")
    if prerequisites is not None and not (
        isinstance(prerequisites, list) and all(isinstance(item, str) for item in prerequisites)
    ):
        errors.append(f"{where}.prerequisites: 必须是阶段 ID 字符串数组")

    assignments = stage.get("assignments")
    if assignments is not None:
        if not isinstance(assignments, list):
            errors.append(f"{where}.assignments: 必须是数组")
        else:
            for aindex, assignment in enumerate(assignments):
                _validate_assignment(assignment, index, aindex, course_ids, assignment_ids, errors)


def _validate_assignment(
    assignment: object,
    sindex: int,
    aindex: int,
    course_ids: dict[str, int],
    assignment_ids: dict[str, str],
    errors: list[str],
) -> None:
    where = f"stages[{sindex}].assignments[{aindex}]"
    if not isinstance(assignment, dict):
        errors.append(f"{where}: 必须是对象")
        return

    assignment_id = assignment.get("id")
    if not isinstance(assignment_id, str) or not ASSIGNMENT_ID_RE.match(assignment_id):
        errors.append(f"{where}.id: 作业 ID 缺少或不符合格式(如 S03-C08-01)")
    elif assignment_id in assignment_ids:
        errors.append(
            f"{where}.id: 作业 ID 重复({assignment_id},首次出现在 {assignment_ids[assignment_id]})"
        )
    else:
        assignment_ids[assignment_id] = where

    for field in ("course_id", "priority", "sections", "why"):
        if field not in assignment:
            errors.append(f"{where}.{field}: 缺少必填字段")

    course_id = assignment.get("course_id")
    if course_id is not None:
        if not isinstance(course_id, str):
            errors.append(f"{where}.course_id: 必须是字符串")
        elif course_id not in course_ids:
            errors.append(f"{where}.course_id: 引用了不存在的课程 {course_id}")

    priority = assignment.get("priority")
    if priority is not None and priority not in PRIORITIES:
        errors.append(f"{where}.priority: 必须是 core 或 elective")

    sections = assignment.get("sections")
    if sections is not None and not _is_string_array(sections):
        errors.append(f"{where}.sections: 必须是非空字符串数组")

    why = assignment.get("why")
    if why is not None and not (isinstance(why, str) and why.strip()):
        errors.append(f"{where}.why: 必须是非空字符串")


def _validate_week(
    week: object,
    index: int,
    week_ids: set[str],
    stage_ids: set[str],
    assignment_ids: dict[str, str],
    repo_root: Path,
    errors: list[str],
) -> None:
    where = f"weeks[{index}]"
    if not isinstance(week, dict):
        errors.append(f"{where}: 必须是对象")
        return

    week_id = week.get("id")
    if not isinstance(week_id, str) or not WEEK_ID_RE.match(week_id):
        errors.append(f"{where}.id: 周 ID 缺少或不符合格式(如 W01)")
    elif week_id in week_ids:
        errors.append(f"{where}.id: 周 ID 重复({week_id})")
    else:
        week_ids.add(week_id)

    for field in ("stage_id", "assignment_ids", "study", "practice", "deliverables", "acceptance", "repo_paths"):
        if field not in week:
            errors.append(f"{where}.{field}: 缺少必填字段")

    stage_id = week.get("stage_id")
    if stage_id is not None and (not isinstance(stage_id, str) or stage_id not in stage_ids):
        errors.append(f"{where}.stage_id: 引用了不存在的阶段 {stage_id!r}")

    assignment_refs = week.get("assignment_ids")
    if assignment_refs is not None:
        if not isinstance(assignment_refs, list) or not all(
            isinstance(item, str) for item in assignment_refs
        ):
            errors.append(f"{where}.assignment_ids: 必须是作业 ID 字符串数组")
        else:
            for ref in assignment_refs:
                if ref not in assignment_ids:
                    errors.append(f"{where}.assignment_ids: 引用了不存在的作业 {ref}")

    for field in ("study", "practice", "deliverables", "acceptance"):
        value = week.get(field)
        if value is not None and not _is_string_array(value):
            errors.append(f"{where}.{field}: 必须是非空字符串数组")

    repo_paths = week.get("repo_paths")
    if isinstance(repo_paths, list):
        for path in repo_paths:
            if not isinstance(path, str) or not path:
                errors.append(f"{where}.repo_paths: 必须是非空仓库相对路径字符串")
            elif not (repo_root / path).exists():
                errors.append(f"{where}.repo_paths: 仓库中不存在路径 {path}")


def _validate_repo_links(links: list, repo_root: Path, errors: list[str]) -> None:
    for index, link in enumerate(links):
        where = f"repo_links[{index}]"
        if not isinstance(link, dict):
            errors.append(f"{where}: 必须是对象")
            continue
        for field in ("label", "path", "description"):
            if field not in link:
                errors.append(f"{where}.{field}: 缺少必填字段")
        path = link.get("path")
        if path is None:
            continue
        if not isinstance(path, str) or not path:
            errors.append(f"{where}.path: 必须是非空字符串")
        elif not (repo_root / path).exists():
            errors.append(f"{where}.path: 仓库中不存在路径 {path}")


def _is_string_array(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _find_prerequisite_cycle(stages: list) -> list[str] | None:
    graph: dict[str, list[str]] = {}
    for stage in stages:
        if isinstance(stage, dict) and isinstance(stage.get("id"), str):
            prerequisites = stage.get("prerequisites")
            if isinstance(prerequisites, list):
                graph[stage["id"]] = [item for item in prerequisites if isinstance(item, str)]

    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        path.append(node)
        for nxt in graph.get(node, []):
            if nxt not in graph:
                continue
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            if state.get(nxt, 0) == 0:
                found = visit(nxt)
                if found:
                    return found
        path.pop()
        state[node] = 2
        return None

    for node in graph:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return None
