"""官方目录候选发现:只抓已配置目录页,提取同域课程链接。

不递归遍历、不抓取候选详情页;发现结果只是"候选",不写入 courses/stages/weeks。
fetch 参数为单次请求函数(约定与 refresh 一致);重定向逐跳检查 allowed_hosts。
"""

from __future__ import annotations

import time
import urllib.parse
from html.parser import HTMLParser

from tools.learning_hub.refresh import _pace, _robots_state

_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAMS = {"ref", "source"}
_MAX_SOURCE_HOPS = 3


def normalize_url(url: str) -> str:
    """归一化用于去重:小写 scheme/host、去 fragment、仅去已知跟踪参数、去无意义尾斜杠。"""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return ""
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if not (key.lower().startswith(_TRACKING_PARAM_PREFIXES) or key.lower() in _TRACKING_PARAMS)
    ]
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urllib.parse.urlencode(query), "")
    )


class _LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self._open_index: int | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "a" and self._open_index is None:
            href = (dict(attrs).get("href") or "").strip()
            if href:
                self._open_index = len(self.links)
                self.links.append({"href": href, "text": ""})

    def handle_endtag(self, tag):
        if tag == "a":
            self._open_index = None

    def handle_data(self, data):
        if self._open_index is not None:
            self.links[self._open_index]["text"] += data


def _collect_links(html: str) -> list[dict]:
    collector = _LinkCollector()
    try:
        collector.feed(html)
        collector.close()
    except Exception:
        return []
    return collector.links


def discover_candidates(catalog: dict, sources: dict, previous: dict, *, fetch, now: str, sleep=None) -> dict:
    """检查全部启用来源,返回新的 candidates 载荷;单来源失败不清空历史候选。"""
    do_sleep = sleep or time.sleep
    previous_payload = previous or {}
    month = now[:7]

    existing_urls = set()
    for course in catalog["courses"]:
        key = normalize_url(course.get("url", ""))
        if key:
            existing_urls.add(key)

    prev_by_key: dict[str, dict] = {}
    for item in previous_payload.get("candidates") or []:
        key = normalize_url(item.get("url", ""))
        if key:
            prev_by_key[key] = dict(item)

    source_checks: dict[str, dict] = {}
    seen_keys: set[str] = set()
    host_last: dict[str, float] = {}
    all_ok = True

    for source in sources.get("sources") or []:
        if not source.get("enabled", True):
            continue
        source_id = source.get("id", "")
        outcome = _discover_source(source, fetch=fetch, now=now, do_sleep=do_sleep, host_last=host_last)
        source_checks[source_id] = outcome["check"]
        if outcome["check"]["status"] != "ok":
            all_ok = False
            continue
        for link_url, title in outcome["links"]:
            key = normalize_url(link_url)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            if key in existing_urls:
                continue
            existing = prev_by_key.get(key)
            if existing is not None:
                existing["last_seen_at"] = now
                if title and existing.get("status") in ("new",):
                    existing["title"] = title
                continue
            prev_by_key[key] = {
                "url": key,
                "title": title or key,
                "source_id": source_id,
                "first_seen_at": now,
                "last_seen_at": now,
                "status": "new",
                "note": "",
            }

    return {
        "schema_version": 1,
        "last_discovery_month": month if all_ok else previous_payload.get("last_discovery_month"),
        "source_checks": source_checks,
        "candidates": list(prev_by_key.values()),
    }


def _discover_source(source: dict, *, fetch, now: str, do_sleep, host_last: dict) -> dict:
    check = {"checked_at": now, "status": "failed", "last_success_month": None, "note": ""}

    def failed(note: str) -> dict:
        check["note"] = note
        return {"check": check, "links": []}

    url = source["url"]
    allowed_hosts = {host.lower() for host in source.get("allowed_hosts") or []}
    state, reason = _robots_state(url, fetch, {}, host_last, do_sleep)
    if state == "denied":
        return failed(reason)
    if state == "unavailable":
        return failed(reason)

    current = url
    hops = 0
    headers: dict = {}
    while True:
        _pace(urllib.parse.urlsplit(current).hostname, host_last, do_sleep)
        response = fetch(current)
        if response.get("error"):
            return failed(f"目录抓取失败:{response['error']}")
        status = response.get("status_code") or 0
        headers = {str(k).lower(): v for k, v in (response.get("headers") or {}).items()}
        if 300 <= status < 400:
            location = (headers.get("location") or "").strip()
            if not location or hops >= _MAX_SOURCE_HOPS:
                return failed(f"目录重定向异常(HTTP {status})")
            next_url = urllib.parse.urljoin(current, location)
            if (urllib.parse.urlsplit(next_url).hostname or "").lower() not in allowed_hosts:
                return failed(f"目录重定向到未允许域 {next_url},已停止")
            current = next_url
            hops += 1
            continue
        break

    if status != 200:
        return failed(f"目录抓取失败:HTTP {status};需人工检查")
    content_type = (headers.get("content-type") or "").lower()
    if content_type and "html" not in content_type:
        return failed(f"目录内容类型 {content_type} 非 HTML,无法解析链接")

    accepted: list[tuple[str, str]] = []
    prefix = source.get("item_path_prefix") or ""
    for link in _collect_links(response.get("body") or ""):
        href = link["href"]
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = urllib.parse.urljoin(current, href)
        parts = urllib.parse.urlsplit(absolute)
        if parts.scheme not in ("http", "https"):
            continue
        if (parts.hostname or "").lower() not in allowed_hosts:
            continue
        if prefix and not parts.path.startswith(prefix):
            continue
        accepted.append((absolute, " ".join(link["text"].split())))

    if not accepted:
        return failed("目录未解析到课程链接,需人工检查")
    check["status"] = "ok"
    check["last_success_month"] = now[:7]
    return {"check": check, "links": accepted}
