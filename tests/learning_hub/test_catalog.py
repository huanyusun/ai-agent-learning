"""catalog 数据与校验器离线测试。全部离线,不访问网络。

校验错误必须包含明确字段路径,便于人工定位。
"""

from copy import deepcopy
from pathlib import Path

from tools.learning_hub.catalog import load_catalog, validate_catalog

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "learning" / "data" / "catalog.json"


def _real_catalog() -> dict:
    return deepcopy(load_catalog(CATALOG_PATH))


def test_real_catalog_loads_with_schema_version():
    catalog = load_catalog(CATALOG_PATH)
    assert catalog["schema_version"] == 1


def test_real_catalog_is_valid():
    errors = validate_catalog(load_catalog(CATALOG_PATH), REPO_ROOT)
    assert errors == []


def test_real_catalog_counts_20_courses_8_stages_18_weeks():
    catalog = load_catalog(CATALOG_PATH)
    assert len(catalog["courses"]) == 20
    assert len(catalog["stages"]) == 8
    assert len(catalog["weeks"]) == 18


def test_dangling_course_reference():
    catalog = _real_catalog()
    catalog["stages"][0]["assignments"][0]["course_id"] = "C99"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("C99" in error for error in errors)


def test_dangling_week_assignment_reference():
    catalog = _real_catalog()
    catalog["weeks"][0]["assignment_ids"].append("S09-C01-01")
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("S09-C01-01" in error for error in errors)


def test_duplicate_course_id():
    catalog = _real_catalog()
    catalog["courses"].append(deepcopy(catalog["courses"][0]))
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("重复" in error and "C01" in error for error in errors)


def test_duplicate_assignment_id_across_stages():
    catalog = _real_catalog()
    duplicated = deepcopy(catalog["stages"][0]["assignments"][0])
    catalog["stages"][1]["assignments"].append(duplicated)
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("重复" in error and duplicated["id"] in error for error in errors)


def test_missing_week_is_reported():
    catalog = _real_catalog()
    catalog["weeks"] = [week for week in catalog["weeks"] if week["id"] != "W07"]
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("W07" in error for error in errors)


def test_missing_stage_is_reported():
    catalog = _real_catalog()
    catalog["stages"] = [s for s in catalog["stages"] if s["id"] != "S05"]
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("S05" in error for error in errors)


def test_stage_dependency_cycle():
    catalog = _real_catalog()
    by_id = {stage["id"]: stage for stage in catalog["stages"]}
    for stage in catalog["stages"]:
        stage["prerequisites"] = []
    by_id["S00"]["prerequisites"] = ["S01"]
    by_id["S01"]["prerequisites"] = ["S00"]
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("循环" in error for error in errors)


def test_self_prerequisite_is_a_cycle():
    catalog = _real_catalog()
    catalog["stages"][0]["prerequisites"] = ["S00"]
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("循环" in error for error in errors)


def test_unknown_prerequisite_stage():
    catalog = _real_catalog()
    catalog["stages"][0]["prerequisites"] = ["S09"]
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("S09" in error and "prerequisites" in error for error in errors)


def test_invalid_url_scheme_is_rejected():
    catalog = _real_catalog()
    catalog["courses"][0]["url"] = "javascript:alert(1)"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("courses[0].url" in error for error in errors)


def test_effort_min_greater_than_max():
    catalog = _real_catalog()
    catalog["courses"][0]["effort_hours"] = {"min": 10, "max": 5, "note": ""}
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("effort_hours" in error for error in errors)


def test_negative_effort_is_rejected():
    catalog = _real_catalog()
    catalog["courses"][3]["effort_hours"] = {"min": -1, "max": 5, "note": ""}
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("effort_hours" in error for error in errors)


def test_invalid_review_level():
    catalog = _real_catalog()
    catalog["courses"][0]["manual_review"]["level"] = "C"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("manual_review" in error for error in errors)


def test_invalid_review_date():
    catalog = _real_catalog()
    catalog["courses"][0]["manual_review"]["reviewed_on"] = "2026/10/28"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("reviewed_on" in error for error in errors)


def test_invalid_course_kind():
    catalog = _real_catalog()
    catalog["courses"][0]["kind"] = "podcast"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("courses[0].kind" in error for error in errors)


def test_invalid_cost_status():
    catalog = _real_catalog()
    catalog["courses"][0]["cost_status"] = "free_everything"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("courses[0].cost_status" in error for error in errors)


def test_missing_repo_path_in_repo_links():
    catalog = _real_catalog()
    catalog["repo_links"].append(
        {"label": "不存在", "path": "platform/fde_product/nope.py", "description": ""}
    )
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("nope.py" in error for error in errors)


def test_missing_repo_path_in_week():
    catalog = _real_catalog()
    catalog["weeks"][0]["repo_paths"].append("learning/notes/ghost.md")
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("ghost.md" in error for error in errors)


def test_week_referencing_unknown_stage():
    catalog = _real_catalog()
    catalog["weeks"][0]["stage_id"] = "S09"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("weeks[0].stage_id" in error for error in errors)


def test_auto_observation_fields_rejected_in_catalog():
    catalog = _real_catalog()
    catalog["courses"][0]["last_checked_at"] = "2026-10-28T00:00:00Z"
    errors = validate_catalog(catalog, REPO_ROOT)
    assert any("last_checked_at" in error for error in errors)
