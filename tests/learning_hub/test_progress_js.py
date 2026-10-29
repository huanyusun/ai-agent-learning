"""个人进度导入校验测试。

校验逻辑是模板中的纯 JS(LEARNING_HUB_PROGRESS.validateImport),
用 node 执行;页面结构要求用 Python 断言。全部离线。
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO_ROOT / "learning" / "web" / "template.html"
CORE_START = "/* PROGRESS-CORE-START */"
CORE_END = "/* PROGRESS-CORE-END */"

KNOWN_ASSIGNMENTS = ["S01-C04-01", "S01-C05-01", "S03-C08-01"]
KNOWN_WEEKS = ["W01", "W02"]


def _core_js() -> str:
    source = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = source.index(CORE_START) + len(CORE_START)
    end = source.index(CORE_END)
    return source[start:end]


def _validate(raw, known_assignments=None, known_weeks=None) -> dict:
    harness = (
        _core_js()
        + "\nlet input='';process.stdin.on('data',d=>input+=d);"
        + "process.stdin.on('end',()=>{"
        + "const req=JSON.parse(input);"
        + "const result=LEARNING_HUB_PROGRESS.validateImport("
        + "req.raw,req.knownAssignments,req.knownWeeks);"
        + "process.stdout.write(JSON.stringify(result));});"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", harness],
        input=json.dumps(
            {
                "raw": raw,
                "knownAssignments": known_assignments or KNOWN_ASSIGNMENTS,
                "knownWeeks": known_weeks or KNOWN_WEEKS,
            }
        ),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_statuses_are_fixed():
    core = _core_js()
    # 枚举以数据形式存在,且页面提示与之一致
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", _core_js()
         + "\nprocess.stdout.write(JSON.stringify(LEARNING_HUB_PROGRESS.STATUSES));"],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(proc.stdout) == ["未开始", "进行中", "已完成", "待复盘"]
    assert "learning-hub.progress.v1" in core or "learning-hub.progress.v1" in TEMPLATE_PATH.read_text(encoding="utf-8")


def test_valid_import_replaces_progress():
    result = _validate(
        {"schema_version": 1, "assignments": {"S01-C04-01": "已完成"}, "weeks": {"W01": "进行中"}}
    )
    assert result["ok"] is True
    assert result["progress"]["assignments"] == {"S01-C04-01": "已完成"}
    assert result["progress"]["weeks"] == {"W01": "进行中"}
    assert result["ignored"] == []


def test_missing_sections_default_to_empty():
    result = _validate({"schema_version": 1})
    assert result["ok"] is True
    assert result["progress"]["assignments"] == {}
    assert result["progress"]["weeks"] == {}


def test_unknown_ids_ignored_and_reported():
    result = _validate(
        {
            "schema_version": 1,
            "assignments": {"S01-C04-01": "已完成", "S09-C01-01": "已完成"},
            "weeks": {"W99": "已完成"},
        }
    )
    assert result["ok"] is True
    assert result["progress"]["assignments"] == {"S01-C04-01": "已完成"}
    assert result["progress"]["weeks"] == {}
    assert sorted(result["ignored"]) == ["S09-C01-01", "W99"]


def test_invalid_status_rejects_whole_import():
    result = _validate(
        {
            "schema_version": 1,
            "assignments": {"S01-C04-01": "已完成", "S01-C05-01": "已通过"},
        }
    )
    assert result["ok"] is False
    assert "S01-C05-01" in result["error"]
    assert "progress" not in result  # 失败时不返回任何可应用数据


def test_non_object_rejected():
    for raw in (None, [], "进度", 42):
        result = _validate(raw)
        assert result["ok"] is False, raw


def test_wrong_schema_version_rejected():
    result = _validate({"schema_version": 2, "assignments": {}})
    assert result["ok"] is False
    assert "schema_version" in result["error"]


def test_unknown_top_level_fields_tolerated_and_preserved():
    result = _validate(
        {
            "schema_version": 1,
            "assignments": {},
            "weeks": {},
            "future_field": {"note": "未来版本字段"},
        }
    )
    assert result["ok"] is True
    assert result["progress"]["future_field"] == {"note": "未来版本字段"}


def test_page_declares_progress_key_and_import_export_controls():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "learning-hub.progress.v1" in template
    assert 'id="btn-export"' in template
    assert 'id="file-import"' in template
    assert 'id="f-search"' in template
    assert 'id="f-stage"' in template
    assert 'id="f-language"' in template
    assert 'id="f-kind"' in template
    assert 'id="f-priority"' in template
    # 进度按钮以 assignment ID / W ID 为数据键
    assert 'progressButton("assignments"' in template
    assert 'progressButton("weeks"' in template
    # 空结果提示
    assert "empty-courses" in template
    assert "empty-stages" in template
