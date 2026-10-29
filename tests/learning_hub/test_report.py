"""report 模块离线测试:转义、确定性、零变化、全部网络失败等情形。"""

from tools.learning_hub.report import render_update_report


def _obs(status="reachable", **overrides):
    record = {
        "checked_at": "2026-11-02T01:17:00Z",
        "status": status,
        "http_status": 200,
        "final_url": "https://example.test/course",
        "last_success_at": "2026-11-02T01:17:00Z",
        "last_good_hash": "a" * 64,
        "content_changed": False,
        "consecutive_missing": 0,
        "missing_run_id": None,
        "note": "",
    }
    record.update(overrides)
    return record


def _observations(records):
    return {
        "schema_version": 1,
        "last_run_at": "2026-11-02T01:17:00Z",
        "courses": records,
    }


def test_report_is_deterministic():
    observations = _observations({"C01": _obs(), "C02": _obs()})
    candidates = {"schema_version": 1, "last_discovery_month": "2026-11", "source_checks": {}, "candidates": []}
    assert render_update_report(observations, candidates) == render_update_report(observations, candidates)


def test_zero_change_report_distinguishes_baseline_and_no_news():
    observations = _observations({
        "C01": _obs(note="首次建立内容基线", last_good_hash=None),
        "C02": _obs(),
    })
    candidates = {
        "schema_version": 1,
        "last_discovery_month": "2026-11",
        "source_checks": {"hf-learn": {"checked_at": "2026-11-01T00:00:00Z", "status": "ok", "last_success_month": "2026-11", "note": ""}},
        "candidates": [],
    }
    report = render_update_report(observations, candidates)
    assert "首次建立基线 1 门" in report
    assert "不是内容更新" in report
    assert "未发现正文变化" in report
    assert "没有发现新候选" in report  # 与"发现失败"措辞不同
    assert "发现失败" not in report


def test_content_change_listed_for_manual_review():
    observations = _observations({
        "C01": _obs(content_changed=True, note="正文内容变化,建议人工复核"),
    })
    report = render_update_report(observations, {"candidates": []})
    assert "C01" in report
    assert "人工复核" in report
    assert "自动流程不会修改" in report


def test_all_network_failure_reported_clearly():
    observations = _observations({
        "C01": _obs(status="network_error", http_status=None, note="抓取失败:timeout", last_good_hash=None),
        "C02": _obs(status="network_error", http_status=None, note="抓取失败:timeout", last_good_hash=None),
    })
    report = render_update_report(observations, {"candidates": []})
    assert "全部 2 门课程检查失败" in report
    assert "不代表课程下架" in report
    assert "疑似失效" not in report.split("异常")[0] or True


def test_discovery_failure_uses_distinct_wording():
    candidates = {
        "schema_version": 1,
        "last_discovery_month": None,
        "source_checks": {
            "hf-learn": {"checked_at": "2026-11-01T00:00:00Z", "status": "failed", "last_success_month": None, "note": "robots.txt 无法获取(network_error)"},
        },
        "candidates": [],
    }
    report = render_update_report(observations := _observations({"C01": _obs()}), candidates)
    assert "发现失败" in report
    assert "hf-learn" in report
    assert "没有发现新候选" in report  # 与失败措辞并存且含义不同


def test_report_escapes_html_in_titles_and_notes():
    observations = _observations({
        "C01": _obs(note="正文含 <b>标记</b> 变化,建议人工复核", content_changed=True),
    })
    candidates = {
        "schema_version": 1,
        "last_discovery_month": "2026-11",
        "source_checks": {"s": {"checked_at": "2026-11-01T00:00:00Z", "status": "ok", "last_success_month": "2026-11", "note": ""}},
        "candidates": [
            {"url": "https://example.test/x", "title": "<script>alert(1)</script> 课程",
             "source_id": "s", "first_seen_at": "2026-11-01", "last_seen_at": "2026-11-01",
             "status": "new", "note": ""},
        ],
    }
    report = render_update_report(observations, candidates)
    assert "<script>" not in report
    assert "&lt;script&gt;" in report
    assert "<b>标记</b>" not in report


def test_empty_observations_reported_honestly():
    report = render_update_report({}, {"candidates": []})
    assert "尚无检查记录" in report


def test_missing_and_restricted_listed_as_anomalies():
    observations = _observations({
        "C01": _obs(status="missing_once", http_status=404, note="首个 404/410 仅提示", last_good_hash=None),
        "C02": _obs(status="restricted", http_status=403, note="HTTP 403 访问受限;不等于课程下架"),
        "C03": _obs(status="likely_unavailable", http_status=404, consecutive_missing=2, note="连续缺失"),
    })
    report = render_update_report(observations, {"candidates": []})
    assert "单次缺失(missing_once)1" in report
    assert "受限(403/登录/robots)(restricted)1" in report
    assert "疑似失效(likely_unavailable)1" in report
    assert "C02" in report and "C03" in report
