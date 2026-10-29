"""课程链接与正文观测:把抓取结果整理为 observations 记录。

fetch 参数是"单次请求"函数(url -> fetch 字典),不做重定向跟随;
重定向的每一跳由本模块检查:仅允许课程原域与 course_rules 中
allowed_redirect_hosts 显式列出的域,不向未允许域继续请求。
自动流程只写观测数据,不修改 catalog 的人工字段。
"""

from __future__ import annotations

import hashlib
import math
import time
import urllib.parse
import urllib.robotparser
from html.parser import HTMLParser

SAME_HOST_INTERVAL_SECONDS = 2
ROBOTS_UA_TOKEN = "learning-hub"

_IGNORED_TAGS = {"script", "style", "nav", "footer", "noscript"}
_CHALLENGE_TITLE_PATTERNS = (
    "just a moment",
    "cf-browser-verification",
    "checking your browser",
    "captcha",
    "attention required",
    "access denied",
    "sign in",
    "log in",
    "login",
    "登录",
)


def refresh_courses(catalog: dict, previous: dict, *, fetch, now: str, run_id: str, sources=None, sleep=None) -> dict:
    """检查 catalog 全部课程,返回 {课程 ID: 观测记录}。

    previous 是 observations 载荷(含 courses 键)或空;单个课程失败不阻断其余课程。
    """
    do_sleep = sleep or time.sleep
    rules = (sources or {}).get("course_rules") or {}
    previous_courses = (previous or {}).get("courses") or {}
    host_last: dict[str, float] = {}
    robots_cache: dict[str, tuple] = {}
    records: dict[str, dict] = {}
    for course in catalog["courses"]:
        course_id = course["id"]
        rule = rules.get(course_id) or {}
        allowed_hosts = _allowed_hosts(course["url"], rule)
        records[course_id] = _refresh_course(
            course,
            previous_courses.get(course_id),
            fetch=fetch,
            now=now,
            run_id=run_id,
            allowed_hosts=allowed_hosts,
            region=rule.get("content_region"),
            robots_cache=robots_cache,
            host_last=host_last,
            do_sleep=do_sleep,
        )
    return records


def _allowed_hosts(url: str, rule: dict) -> set[str]:
    hostname = (urllib.parse.urlsplit(url).hostname or "").lower()
    hosts = {hostname} if hostname else set()
    for extra in rule.get("allowed_redirect_hosts", []) or []:
        if isinstance(extra, str) and extra:
            hosts.add(extra.lower())
    return hosts


def _pace(hostname: str | None, host_last: dict[str, float], do_sleep) -> None:
    """同域请求之间至少间隔 2 秒。"""
    if not hostname:
        return
    key = hostname.lower()
    last = host_last.get(key)
    if last is not None:
        remaining = SAME_HOST_INTERVAL_SECONDS - (time.monotonic() - last)
        if remaining > 0:
            do_sleep(max(1, math.ceil(remaining)))
    host_last[key] = time.monotonic()


def _robots_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def _robots_state(url: str, fetch, robots_cache: dict, host_last: dict, do_sleep) -> tuple:
    """返回 ("allow"|"denied"|"unavailable", 说明)。robots 4xx 视为无规则(允许)。"""
    robots_url = _robots_url(url)
    if robots_url in robots_cache:
        return robots_cache[robots_url]
    _pace(urllib.parse.urlsplit(url).hostname, host_last, do_sleep)
    response = fetch(robots_url)
    status = response.get("status_code") or 0
    if response.get("error") or status >= 500 or status == 429:
        reason = response.get("error") or f"HTTP {status}"
        state = ("unavailable", f"robots.txt 无法获取({reason}),本次跳过课程页检查")
    elif 400 <= status < 500:
        state = ("allow", None)
    else:
        parser = urllib.robotparser.RobotFileParser()
        parser.parse((response.get("body") or "").splitlines())
        path = urllib.parse.urlsplit(url).path or "/"
        if parser.can_fetch(ROBOTS_UA_TOKEN, path) and parser.can_fetch("*", path):
            state = ("allow", None)
        else:
            state = ("denied", "robots.txt 禁止抓取,本次未访问课程页")
    robots_cache[robots_url] = state
    return state


def _refresh_course(
    course: dict,
    previous: dict | None,
    *,
    fetch,
    now: str,
    run_id: str,
    allowed_hosts: set[str],
    region: dict | None,
    robots_cache: dict,
    host_last: dict,
    do_sleep,
) -> dict:
    url = course["url"]
    previous = previous or {}

    def record(status: str, http_status=None, note: str = "") -> dict:
        return {
            "checked_at": now,
            "status": status,
            "http_status": http_status,
            "final_url": url,
            "last_success_at": previous.get("last_success_at"),
            "last_good_hash": previous.get("last_good_hash"),
            "content_changed": False,
            "consecutive_missing": previous.get("consecutive_missing", 0),
            "missing_run_id": previous.get("missing_run_id"),
            "note": note,
        }

    state, reason = _robots_state(url, fetch, robots_cache, host_last, do_sleep)
    if state == "denied":
        return record("restricted", None, reason)
    if state == "unavailable":
        keep = previous.get("status") or "network_error"
        return record(keep, None, reason)

    current = url
    hops = 0
    headers: dict = {}
    while True:
        _pace(urllib.parse.urlsplit(current).hostname, host_last, do_sleep)
        response = fetch(current)
        headers = {
            str(key).lower(): value
            for key, value in (response.get("headers") or {}).items()
        }
        error = response.get("error")
        if error == "blocked_private_address":
            return record("restricted", None, "目标地址被安全检查拦截(私有/回环地址),未继续访问")
        if error:
            note = f"抓取失败:{error};访问失败不等同于课程下架"
            return record("network_error", None, note)
        status = response.get("status_code") or 0
        if 300 <= status < 400:
            location = (headers.get("location") or "").strip()
            if not location:
                return record("network_error", status, f"HTTP {status} 重定向缺少 Location")
            if hops >= 5:
                return record("network_error", status, "重定向超过 5 跳,已停止")
            next_url = urllib.parse.urljoin(current, location)
            next_host = (urllib.parse.urlsplit(next_url).hostname or "").lower()
            if next_host not in allowed_hosts:
                return record("restricted", status, f"重定向目标 {next_host} 不在允许域内,已停止跟踪")
            current = next_url
            hops += 1
            continue
        break

    body = response.get("body") or ""
    if status == 429:
        return record("rate_limited", status, "HTTP 429 限流;本次未建立或更新内容指纹")
    if status == 403:
        return record("restricted", status, "HTTP 403 访问受限;不等于课程下架,保留既有内容指纹")
    if status in (404, 410):
        if previous.get("missing_run_id") == run_id:
            count = previous.get("consecutive_missing", 0)
            note = "同一次运行重复观测,不重复累计缺失次数"
        else:
            count = previous.get("consecutive_missing", 0) + 1
            note = "首个 404/410 仅提示;连续两次独立运行才标记疑似失效" if count < 2 else "连续两次独立运行缺失,标记疑似失效"
        outcome = record("likely_unavailable" if count >= 2 else "missing_once", status, note)
        outcome["consecutive_missing"] = count
        outcome["missing_run_id"] = run_id
        return outcome
    if status < 200 or status >= 300:
        return record("network_error", status, f"HTTP {status};访问失败不等同于课程下架")

    final_host = (urllib.parse.urlsplit(current).hostname or "").lower()
    if final_host not in allowed_hosts:
        return record("restricted", status, f"最终地址 {final_host} 不在允许域内")

    title = _extract_title(body)
    if _looks_like_challenge(title, current):
        return record("restricted", status, "页面特征为登录/挑战页,不建立内容指纹")

    content_type = (headers.get("content-type") or "").lower()
    if content_type and not any(kind in content_type for kind in ("html", "xml")):
        outcome = record("unsupported_content", status)
        outcome["final_url"] = current
        outcome["note"] = f"内容类型 {content_type} 非 HTML 页面;仅记录可达性,不建立内容指纹"
        return outcome

    text = _extract_text(body, region)
    if text is None:
        outcome = record("unsupported_content", status)
        outcome["final_url"] = current
        outcome["note"] = "定位不到课程正文区域(依次尝试配置区域、main、article);仅记录可达性,不用整页冒充正文"
        return outcome

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    previous_hash = previous.get("last_good_hash")
    if not previous_hash:
        note = "首次建立内容基线"
        changed = False
    elif digest == previous_hash:
        note = ""
        changed = False
    else:
        note = "正文内容变化,建议人工复核"
        changed = True
    outcome = record("redirected" if current != url else "reachable", status, note)
    outcome["final_url"] = current
    outcome["last_success_at"] = now
    outcome["last_good_hash"] = digest
    outcome["content_changed"] = changed
    outcome["consecutive_missing"] = 0
    outcome["missing_run_id"] = None
    return outcome


def _extract_title(html: str) -> str:
    lower = html.lower()
    start = lower.find("<title")
    if start == -1:
        return ""
    open_end = lower.find(">", start)
    close = lower.find("</title>", open_end)
    if open_end == -1 or close == -1:
        return ""
    return html[open_end + 1 : close].strip()


def _looks_like_challenge(title: str, url: str) -> bool:
    lowered = title.lower()
    if any(pattern in lowered for pattern in _CHALLENGE_TITLE_PATTERNS):
        return True
    path = urllib.parse.urlsplit(url).path.lower()
    return "/login" in path or "/signin" in path


class _RegionExtractor(HTMLParser):
    """捕获第一个匹配区域内的文本;忽略 script/style/nav/footer/noscript。"""

    def __init__(self, tag: str, want_id: str | None = None, want_class: str | None = None):
        super().__init__(convert_charrefs=True)
        self.tag = tag.lower()
        self.want_id = want_id
        self.want_class = want_class
        self.depth = 0
        self.ignore_depth = 0
        self.matched = False
        self.done = False
        self.parts: list[str] = []

    def _attrs_match(self, attrs) -> bool:
        if not self.want_id and not self.want_class:
            return True
        mapping = dict(attrs)
        if self.want_id and mapping.get("id") != self.want_id:
            return False
        if self.want_class and self.want_class not in (mapping.get("class") or "").split():
            return False
        return True

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.done:
            return
        if self.depth:
            if tag == self.tag:
                self.depth += 1
            if tag in _IGNORED_TAGS:
                self.ignore_depth += 1
        elif tag == self.tag and self._attrs_match(attrs):
            self.matched = True
            self.depth = 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.done or not self.depth:
            return
        if tag in _IGNORED_TAGS and self.ignore_depth:
            self.ignore_depth -= 1
        elif tag == self.tag:
            self.depth -= 1
            if self.depth == 0:
                self.done = True

    def handle_data(self, data):
        if self.depth and not self.done and self.ignore_depth == 0:
            self.parts.append(data)


def _extract_text(html: str, region: dict | None) -> str | None:
    if region and region.get("tag"):
        candidates = [(region["tag"], region.get("id"), region.get("class_name"))]
    else:
        candidates = [("main", None, None), ("article", None, None)]
    for tag, want_id, want_class in candidates:
        parser = _RegionExtractor(tag, want_id, want_class)
        try:
            parser.feed(html)
            parser.close()
        except Exception:
            return None
        if parser.matched:
            text = " ".join("".join(parser.parts).split())
            if text:
                return text
    return None
