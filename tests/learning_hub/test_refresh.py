"""refresh 模块离线测试:fake fetch,不访问公网。"""

import hashlib
from pathlib import Path

from tools.learning_hub.catalog import load_catalog
from tools.learning_hub.refresh import refresh_courses

REPO_ROOT = Path(__file__).resolve().parents[2]

NOW1 = "2026-11-02T01:17:00Z"
NOW2 = "2026-11-09T01:17:00Z"
NOW3 = "2026-11-16T01:17:00Z"
RUN1 = "run-1"
RUN2 = "run-2"


class FakeSite:
    """按 URL 提供响应的 fake fetch;记录全部请求。"""

    def __init__(self, pages=None, robots=None):
        self.pages = pages or {}
        self.robots = robots or {}
        self.requested = []

    def __call__(self, url):
        self.requested.append(url)
        if url.endswith("/robots.txt"):
            mode = self.robots.get(url, "allow-all-404")
            if mode == "allow-all-404":
                return {"status_code": 404, "headers": {}, "body": "", "error": None}
            if mode == "deny":
                return {
                    "status_code": 200,
                    "headers": {},
                    "body": "User-agent: *\nDisallow: /\n",
                    "error": None,
                }
            if mode == "error":
                return {"status_code": None, "headers": {}, "body": "", "error": "timeout"}
            return {"status_code": 200, "headers": {}, "body": "User-agent: *\nAllow: /\n", "error": None}
        page = self.pages.get(url)
        if page is None:
            return {"status_code": None, "headers": {}, "body": "", "error": "network_error"}
        return {
            "status_code": page.get("status", 200),
            "headers": page.get("headers", {}),
            "body": page["body"],
            "error": None,
        }


def _catalog():
    catalog = load_catalog(REPO_ROOT / "learning" / "data" / "catalog.json")
    # 用两门课做受控测试,URL 全部指向 fake 域
    replacements = {
        "https://cs50.harvard.edu/python/": "https://site-one.test/p/",
        "https://fastapi.tiangolo.com/zh/tutorial/": "https://site-two.test/",
    }
    courses = []
    for course in catalog["courses"][:2]:
        item = dict(course)
        item["url"] = replacements.get(course["url"], course["url"])
        courses.append(item)
    return {
        "schema_version": 1,
        "courses": courses,
        "stages": catalog["stages"],
        "weeks": catalog["weeks"],
        "repo_links": catalog["repo_links"],
    }


def _page(text, status=200):
    return {"status": status, "body": f"<html><head><title>t</title></head><body><nav>导航</nav><main>{text}</main><footer>脚</footer></body></html>"}


def _no_region_page(status=200):
    return {"status": status, "body": "<html><body><div>只有整页</div></body></html>"}


def test_first_run_establishes_baseline():
    site = FakeSite(pages={"https://site-one.test/p/": _page("正文一"), "https://site-two.test/": _page("正文二")})
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    record = out["C01"]
    assert record["status"] == "reachable"
    assert record["content_changed"] is False
    assert record["last_good_hash"] == hashlib.sha256("正文一".encode()).hexdigest()
    assert record["last_success_at"] == NOW1
    assert record["consecutive_missing"] == 0


def test_same_content_and_changed_content():
    site = FakeSite(pages={"https://site-one.test/p/": _page("正文一"), "https://site-two.test/": _page("正文二")})
    first = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    second = refresh_courses(_catalog(), {"schema_version": 1, "last_run_at": NOW1, "courses": first},
                             fetch=site, now=NOW2, run_id=RUN2, sleep=lambda s: None)
    assert second["C01"]["content_changed"] is False

    site.pages["https://site-one.test/p/"] = _page("正文一改版")
    third = refresh_courses(_catalog(), {"courses": second}, fetch=site, now=NOW3, run_id="run-3", sleep=lambda s: None)
    assert third["C01"]["content_changed"] is True
    assert third["C01"]["last_good_hash"] == hashlib.sha256("正文一改版".encode()).hexdigest()


def test_ignored_tags_excluded_from_fingerprint():
    site = FakeSite(pages={
        "https://site-one.test/p/": _page("正文一"),
        "https://site-two.test/": _page("正文二"),
    })
    # 导航/脚本文本变化不影响指纹
    site.pages["https://site-one.test/p/"] = {
        "status": 200,
        "body": "<html><head><title>改</title><style>x{y:1}</style></head><body><nav>导航完全不同了</nav>"
                "<main>正文一</main><script>var a=1;</script><footer>脚</footer></body></html>",
    }
    first = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    second = refresh_courses(_catalog(), {"courses": first}, fetch=site, now=NOW2, run_id=RUN2, sleep=lambda s: None)
    assert second["C01"]["content_changed"] is False


def test_error_page_does_not_overwrite_good_hash():
    site = FakeSite(pages={"https://site-one.test/p/": _page("正文一"), "https://site-two.test/": _page("正文二")})
    first = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    good_hash = first["C01"]["last_good_hash"]

    site.pages["https://site-one.test/p/"] = {"status": 403, "body": "<html><body>Forbidden</body></html>"}
    second = refresh_courses(_catalog(), {"courses": first}, fetch=site, now=NOW2, run_id=RUN2, sleep=lambda s: None)
    record = second["C01"]
    assert record["status"] == "restricted"
    assert record["last_good_hash"] == good_hash
    assert record["last_success_at"] == NOW1

    site.pages["https://site-one.test/p/"] = {"status": 404, "body": "not found"}
    third = refresh_courses(_catalog(), {"courses": second}, fetch=site, now=NOW3, run_id="run-3", sleep=lambda s: None)
    assert third["C01"]["status"] == "missing_once"
    assert third["C01"]["last_good_hash"] == good_hash


def test_repeated_run_id_does_not_increase_missing():
    site = FakeSite(pages={"https://site-one.test/p/": {"status": 404, "body": "gone"}, "https://site-two.test/": _page("x")})
    first = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    assert first["C01"]["status"] == "missing_once"
    assert first["C01"]["consecutive_missing"] == 1
    # 同一次运行重跑(run_id 相同)不得重复累计
    again = refresh_courses(_catalog(), {"courses": first}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    assert again["C01"]["consecutive_missing"] == 1


def test_two_independent_missing_runs_then_unavailable():
    site = FakeSite(pages={"https://site-one.test/p/": {"status": 404, "body": "gone"}, "https://site-two.test/": _page("x")})
    first = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    second = refresh_courses(_catalog(), {"courses": first}, fetch=site, now=NOW2, run_id=RUN2, sleep=lambda s: None)
    assert second["C01"]["status"] == "likely_unavailable"
    assert second["C01"]["consecutive_missing"] == 2


def test_recovery_clears_missing_state():
    site = FakeSite(pages={"https://site-one.test/p/": {"status": 404, "body": "gone"}, "https://site-two.test/": _page("x")})
    first = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    second = refresh_courses(_catalog(), {"courses": first}, fetch=site, now=NOW2, run_id=RUN2, sleep=lambda s: None)
    site.pages["https://site-one.test/p/"] = _page("回来了")
    third = refresh_courses(_catalog(), {"courses": second}, fetch=site, now=NOW3, run_id="run-3", sleep=lambda s: None)
    record = third["C01"]
    assert record["status"] == "reachable"
    assert record["consecutive_missing"] == 0
    assert record["missing_run_id"] is None


def test_single_site_failure_does_not_block_others():
    site = FakeSite(pages={"https://site-one.test/p/": _page("正文一")})  # site-two 网络错误
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    assert out["C01"]["status"] == "reachable"
    assert out["C02"]["status"] == "network_error"
    assert "https://site-two.test/" in site.requested  # 仍尝试访问
    assert out["C02"]["last_good_hash"] is None


def test_page_without_content_region_is_unsupported_content():
    site = FakeSite(pages={"https://site-one.test/p/": _no_region_page(), "https://site-two.test/": _page("x")})
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    record = out["C01"]
    assert record["status"] == "unsupported_content"
    assert record["http_status"] == 200
    assert record["last_good_hash"] is None  # 不用整页 hash 冒充正文


def test_non_html_content_is_not_fingerprinted():
    site = FakeSite(pages={
        "https://site-one.test/p/": {
            "status": 200,
            "headers": {"Content-Type": "application/pdf"},
            "body": "%PDF-1.4 <main>伪装正文的二进制</main>",
        },
        "https://site-two.test/": _page("x"),
    })
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    record = out["C01"]
    assert record["status"] == "unsupported_content"
    assert record["last_good_hash"] is None
    assert "HTML" in record["note"]


def test_redirect_to_disallowed_host_is_stopped():
    pages = {
        "https://site-one.test/p/": {"status": 301, "headers": {"location": "https://evil.test/next"}, "body": ""},
        "https://site-two.test/": _page("x"),
    }
    site = FakeSite(pages=pages)
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    assert out["C01"]["status"] == "restricted"
    assert "https://evil.test/next" not in site.requested


def test_redirect_to_allowed_host_lands_reachable():
    pages = {
        "https://site-one.test/p/": {"status": 302, "headers": {"location": "/final"}, "body": ""},
        "https://site-one.test/final": _page("正文一"),
        "https://site-two.test/": _page("x"),
    }
    site = FakeSite(pages=pages)
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    assert out["C01"]["status"] == "redirected"
    assert out["C01"]["final_url"] == "https://site-one.test/final"
    assert out["C01"]["last_good_hash"] is not None


def test_robots_disallow_reports_restricted_without_visit():
    site = FakeSite(
        pages={"https://site-two.test/": _page("x")},
        robots={"https://site-one.test/robots.txt": "deny"},
    )
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    record = out["C01"]
    assert record["status"] == "restricted"
    assert "robots" in record["note"]
    assert "https://site-one.test/p/" not in site.requested


def test_robots_unavailable_skips_with_reason():
    site = FakeSite(
        pages={"https://site-two.test/": _page("x")},
        robots={"https://site-one.test/robots.txt": "error"},
    )
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    record = out["C01"]
    assert record["status"] == "network_error"
    assert "robots" in record["note"]


def test_rate_limited_is_reported_separately():
    site = FakeSite(pages={"https://site-one.test/p/": {"status": 429, "body": "slow down"}, "https://site-two.test/": _page("x")})
    out = refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    assert out["C01"]["status"] == "rate_limited"


def test_same_host_requests_are_paced():
    pages = {"https://site-one.test/p/": _page("正文一"), "https://site-two.test/": _page("x")}
    site = FakeSite(pages=pages, robots={"https://site-one.test/robots.txt": "allow", "https://site-two.test/robots.txt": "allow"})
    sleeps = []
    refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=sleeps.append)
    # 同域课程页与 robots 之间至少间隔 2 秒(由注入 sleep 承担)
    assert any(s == 2 for s in sleeps)


def test_catalog_input_not_mutated():
    catalog = _catalog()
    before = {c["id"]: dict(c) for c in catalog["courses"]}
    site = FakeSite(pages={"https://site-one.test/p/": _page("正文一"), "https://site-two.test/": _page("x")})
    refresh_courses(catalog, {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    for course in catalog["courses"]:
        assert course == before[course["id"]]


def test_only_configured_course_hosts_requested():
    site = FakeSite(pages={"https://site-one.test/p/": _page("x"), "https://site-two.test/": _page("x")})
    refresh_courses(_catalog(), {}, fetch=site, now=NOW1, run_id=RUN1, sleep=lambda s: None)
    hosts = {url.split("/")[2] for url in site.requested}
    assert hosts <= {"site-one.test", "site-two.test"}
