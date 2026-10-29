"""render 生成器离线测试:确定性、转义、内容完整性与 --check 行为。"""

from copy import deepcopy
from pathlib import Path

from tools.learning_hub.catalog import load_catalog
from tools.learning_hub.render import build_outputs, check_outputs, write_outputs

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "learning" / "data" / "catalog.json"

MD_OUTPUTS = ("learning/README.md", "learning/courses.md", "learning/weekly-plan.md", "learning/updates/latest.md")


def _outputs(catalog=None, observations=None, candidates=None):
    return build_outputs(
        catalog if catalog is not None else load_catalog(CATALOG_PATH),
        observations or {},
        candidates or {},
    )


def test_build_is_deterministic():
    assert _outputs() == _outputs()


def test_generated_files_have_banner_and_commands():
    outputs = _outputs()
    for rel in MD_OUTPUTS:
        assert "由 tools/learning_hub 生成" in outputs[rel], rel
        assert "python3 -m tools.learning_hub build" in outputs[rel], rel
    assert "由 tools/learning_hub 生成" in outputs["learning/index.html"]


def test_write_then_check_has_no_drift(tmp_path):
    outputs = _outputs()
    write_outputs(outputs, tmp_path)
    assert check_outputs(outputs, tmp_path) == []


def test_check_detects_drift_without_writing(tmp_path):
    outputs = _outputs()
    write_outputs(outputs, tmp_path)
    target = tmp_path / "learning" / "courses.md"
    target.write_text("被手工改过", encoding="utf-8")
    drift = check_outputs(outputs, tmp_path)
    assert drift == ["learning/courses.md: 与生成结果不一致"]
    assert target.read_text(encoding="utf-8") == "被手工改过"


def test_check_reports_missing_file(tmp_path):
    outputs = _outputs()
    drift = check_outputs(outputs, tmp_path)
    assert len(drift) == len(outputs)
    assert all("缺失" in item for item in drift)


def test_script_title_is_escaped_everywhere():
    catalog = deepcopy(load_catalog(CATALOG_PATH))
    catalog["courses"][0]["title"] = "<script>alert(1)</script> 课程"
    outputs = _outputs(catalog=catalog)
    html = outputs["learning/index.html"]
    assert "<script>alert(1)</script>" not in html
    assert "\\u003cscript\\u003e" in html
    for rel in MD_OUTPUTS:
        assert "<script>" not in outputs[rel], rel


def test_embedded_payload_cannot_close_script_tag():
    html = _outputs()["learning/index.html"]
    marker = "window.LEARNING_HUB_DATA = "
    start = html.index(marker) + len(marker)
    end = html.index(";\n", start)
    payload = html[start:end]
    assert "<" not in payload and ">" not in payload


def test_all_courses_and_weeks_present():
    outputs = _outputs()
    catalog = load_catalog(CATALOG_PATH)
    html = outputs["learning/index.html"]
    for course in catalog["courses"]:
        assert course["id"] in html
    for week in catalog["weeks"]:
        assert week["id"] in html
    md = outputs["learning/courses.md"]
    for course in catalog["courses"]:
        assert course["id"] in md
    weekly = outputs["learning/weekly-plan.md"]
    for week in catalog["weeks"]:
        assert week["id"] in weekly


def test_review_level_b_is_not_upgraded():
    md = _outputs()["learning/courses.md"]
    c12_line = next(line for line in md.splitlines() if line.startswith("| C12 |"))
    assert "B(2026-10-28)" in c12_line
    assert "A(2026-10-28)" not in c12_line


def test_missing_observations_show_pending_not_fabricated():
    html = _outputs()["learning/index.html"]
    assert "尚未检查" in html


def test_repo_links_and_outline_link_preserved():
    readme = _outputs()["learning/README.md"]
    assert "platform/fde_product/models.py" in readme
    assert "course-materials/w01/00_使用说明.md" in readme
    assert "../AI学习路径与大纲.md" in readme
    assert "../docs/superpowers/plans/2026-10-28-learning-hub.md" in readme
    assert "GLM-HANDOFF.md" in readme


def test_curated_boundary_text_preserved():
    outputs = _outputs()
    assert "覆盖边界与选择依据" in outputs["learning/courses.md"]
    assert "综合项目二选一" in outputs["learning/weekly-plan.md"]
    assert "课程之外仍需自行完成" in outputs["learning/README.md"]
    assert "最少选课组合" in outputs["learning/README.md"]
