"""discover 模块离线测试:两个目录 fixture,全部离线。"""

from pathlib import Path

from tools.learning_hub.catalog import load_catalog
from tools.learning_hub.discover import discover_candidates, normalize_url

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-11-05T02:17:00Z"

HF_DIR = """<html><body>
<a href="/learn/llm-course">LLM Course</a>
<a href="/learn/agents-course/en/unit0/introduction">Agents Course(已有课程)</a>
<a href="https://huggingface.co/learn/deep-rl-course?utm_source=nav&amp;utm_medium=menu">Deep RL</a>
<a href="/blog/post">博客文章</a>
<a href="https://evil.test/learn/fake">外站</a>
<a href="javascript:void(0)">脚本链接</a>
<a href="/learn/query-course?tab=1&amp;utm_campaign=x&amp;ref=nav">Query Course</a>
<a href="/learn/dup-course">重复一</a>
<a href="/learn/dup-course/">重复二(尾斜杠)</a>
</body></html>"""

LC_DIR = """<html><body>
<main>
<a href="/courses/intro-to-langgraph">Intro to LangGraph(已有课程)</a>
<a href="/courses/academy-first?source=menu">Academy First</a>
<a href="/paths/other">路径页(前缀不符)</a>
</main></body></html>"""


def _sources(**robots_mode):
    def mode_for(url):
        return robots_mode.get(url, "allow")
    return mode_for


class FakeWeb:
    """url -> 响应;robots 模式可控;记录请求。"""

    def __init__(self, pages=None, robots_mode=None):
        self.pages = pages or {}
        self.robots_mode = robots_mode or {}
        self.requested = []

    def __call__(self, url):
        self.requested.append(url)
        if url.endswith("/robots.txt"):
            mode = self.robots_mode.get(url.replace("/robots.txt", ""), "allow")
            if mode == "deny":
                return {"status_code": 200, "headers": {}, "body": "User-agent: *\nDisallow: /\n", "error": None}
            if mode == "error":
                return {"status_code": None, "headers": {}, "body": "", "error": "timeout"}
            return {"status_code": 404, "headers": {}, "body": "", "error": None}
        page = self.pages.get(url)
        if page is None:
            return {"status_code": None, "headers": {}, "body": "", "error": "network_error"}
        return {"status_code": page.get("status", 200), "headers": page.get("headers", {}), "body": page["body"], "error": None}


def _sources_config():
    return {
        "schema_version": 1,
        "sources": [
            {
                "id": "hf-learn",
                "url": "https://huggingface.co/learn",
                "mode": "html_links",
                "allowed_hosts": ["huggingface.co"],
                "item_path_prefix": "/learn/",
                "enabled": True,
                "note": "",
            },
            {
                "id": "langchain-academy",
                "url": "https://academy.langchain.com/",
                "mode": "html_links",
                "allowed_hosts": ["academy.langchain.com"],
                "item_path_prefix": "/courses/",
                "enabled": True,
                "note": "",
            },
        ],
        "course_rules": {},
    }


def _web():
    return FakeWeb(pages={
        "https://huggingface.co/learn": {"body": HF_DIR},
        "https://academy.langchain.com/": {"body": LC_DIR},
    })


def _catalog():
    return load_catalog(REPO_ROOT / "learning" / "data" / "catalog.json")


def _urls(payload):
    return {item["url"] for item in payload["candidates"]}


def by_last_seen(payload, url):
    return next(item["last_seen_at"] for item in payload["candidates"] if item["url"] == url)


def test_normalize_url_strips_tracking_and_trailing_slash():
    assert normalize_url("https://A.example/learn/x/?utm_source=a&utm_medium=b&tab=1") == \
        "https://a.example/learn/x?tab=1"
    assert normalize_url("https://a.example/learn/x?ref=nav&source=menu&id=9") == \
        "https://a.example/learn/x?id=9"
    assert normalize_url("https://a.example/") == "https://a.example/"


def test_discover_parses_both_directories_with_filters():
    web = _web()
    payload = discover_candidates(_catalog(), _sources_config(), {}, fetch=web, now=NOW, sleep=lambda s: None)
    urls = _urls(payload)
    # 相对链接解析 + 前缀/允许域过滤
    assert "https://huggingface.co/learn/llm-course" in urls
    assert "https://huggingface.co/learn/deep-rl-course" in urls
    assert "https://huggingface.co/blog/post" not in urls
    assert "https://evil.test/learn/fake" not in urls
    assert "https://huggingface.co/paths/other" not in urls
    assert "https://academy.langchain.com/courses/academy-first" in urls
    # 已有课程 URL 被排除
    assert "https://huggingface.co/learn/agents-course/en/unit0/introduction" not in urls
    assert "https://academy.langchain.com/courses/intro-to-langgraph" not in urls
    # 功能参数保留、跟踪参数去除
    assert "https://huggingface.co/learn/query-course?tab=1" in urls
    assert not any("utm_" in u or "ref=nav" in u for u in urls)
    # 同课程去重(尾斜杠视为同一 URL)
    assert sum(1 for u in urls if "dup-course" in u) == 1


def test_new_candidates_have_status_and_dates():
    payload = discover_candidates(_catalog(), _sources_config(), {}, fetch=_web(), now=NOW, sleep=lambda s: None)
    for item in payload["candidates"]:
        assert item["status"] == "new"
        assert item["first_seen_at"] == NOW
        assert item["last_seen_at"] == NOW
        assert item["title"]
        assert item["source_id"] in ("hf-learn", "langchain-academy")
    assert payload["last_discovery_month"] == "2026-11"
    assert all(check["status"] == "ok" for check in payload["source_checks"].values())


def test_second_run_does_not_duplicate_and_keeps_first_seen():
    web = _web()
    first = discover_candidates(_catalog(), _sources_config(), {}, fetch=web, now=NOW, sleep=lambda s: None)
    later = "2026-12-03T02:17:00Z"
    second = discover_candidates(_catalog(), _sources_config(), first, fetch=web, now=later, sleep=lambda s: None)
    assert len(second["candidates"]) == len(first["candidates"])
    by_url = {item["url"]: item for item in second["candidates"]}
    assert by_url["https://huggingface.co/learn/llm-course"]["first_seen_at"] == NOW
    assert by_url["https://huggingface.co/learn/llm-course"]["last_seen_at"] == later


def test_manual_status_and_first_seen_survive():
    first = discover_candidates(_catalog(), _sources_config(), {}, fetch=_web(), now=NOW, sleep=lambda s: None)
    for item in first["candidates"]:
        if item["url"].endswith("llm-course"):
            item["status"] = "accepted"
        if item["url"].endswith("deep-rl-course"):
            item["status"] = "dismissed"
    second = discover_candidates(_catalog(), _sources_config(), first, fetch=_web(), now="2026-12-03T02:17:00Z", sleep=lambda s: None)
    by_url = {item["url"]: item for item in second["candidates"]}
    assert by_url["https://huggingface.co/learn/llm-course"]["status"] == "accepted"
    assert by_url["https://huggingface.co/learn/deep-rl-course"]["status"] == "dismissed"


def test_disappeared_candidates_are_kept():
    first = discover_candidates(_catalog(), _sources_config(), {}, fetch=_web(), now=NOW, sleep=lambda s: None)
    # HF 目录本轮整体失效:已有候选(llm-course 等)必须保留
    web = FakeWeb(pages={"https://academy.langchain.com/": {"body": LC_DIR}})
    second = discover_candidates(_catalog(), _sources_config(), first, fetch=web, now="2026-12-03T02:17:00Z", sleep=lambda s: None)
    urls = _urls(second)
    assert "https://huggingface.co/learn/llm-course" in urls  # 消失候选保留记录
    assert by_last_seen(second, "https://huggingface.co/learn/llm-course") == NOW  # last_seen 不变
    assert second["source_checks"]["hf-learn"]["status"] == "failed"
    assert second["last_discovery_month"] != "2026-12"  # 有来源失败,月份不推进


def test_failed_source_does_not_clear_history_and_month_stays():
    first = discover_candidates(_catalog(), _sources_config(), {}, fetch=_web(), now=NOW, sleep=lambda s: None)
    broken = FakeWeb(pages={"https://huggingface.co/learn": {"body": HF_DIR}})  # academy 网络错误
    second = discover_candidates(_catalog(), _sources_config(), first, fetch=broken, now="2026-12-03T02:17:00Z", sleep=lambda s: None)
    assert len(second["candidates"]) == len(first["candidates"])
    assert second["source_checks"]["langchain-academy"]["status"] == "failed"
    assert second["source_checks"]["langchain-academy"]["note"]
    assert second["last_discovery_month"] == "2026-11"


def test_robots_denied_source_records_anomaly():
    web = FakeWeb(
        pages={"https://academy.langchain.com/": {"body": LC_DIR}},
        robots_mode={"https://huggingface.co": "deny"},
    )
    payload = discover_candidates(_catalog(), _sources_config(), {}, fetch=web, now=NOW, sleep=lambda s: None)
    assert payload["source_checks"]["hf-learn"]["status"] == "failed"
    assert "robots" in payload["source_checks"]["hf-learn"]["note"]
    assert "https://huggingface.co/learn" not in web.requested
    assert payload["last_discovery_month"] is None


def test_directory_without_parsable_links_is_anomaly():
    web = FakeWeb(pages={
        "https://huggingface.co/learn": {"body": "<html><body><p>没有链接</p></body></html>"},
        "https://academy.langchain.com/": {"body": LC_DIR},
    })
    payload = discover_candidates(_catalog(), _sources_config(), {}, fetch=web, now=NOW, sleep=lambda s: None)
    assert payload["source_checks"]["hf-learn"]["status"] == "failed"
    assert "人工" in payload["source_checks"]["hf-learn"]["note"]


def test_catalog_input_not_mutated():
    catalog = _catalog()
    before = [dict(c) for c in catalog["courses"]]
    discover_candidates(catalog, _sources_config(), {}, fetch=_web(), now=NOW, sleep=lambda s: None)
    assert catalog["courses"] == before


def test_only_configured_source_hosts_requested():
    web = _web()
    discover_candidates(_catalog(), _sources_config(), {}, fetch=web, now=NOW, sleep=lambda s: None)
    hosts = {url.split("/")[2] for url in web.requested}
    assert hosts <= {"huggingface.co", "academy.langchain.com"}
