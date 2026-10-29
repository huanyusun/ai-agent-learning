"""HTTP 抓取:受控的超时、重定向、重试与安全限制。

fetch_url 是公开入口,返回固定字段字典而非抛异常:
{url, final_url, status_code, headers, body, error}。
transport 可注入用于离线测试;默认 transport 单次请求、不跟随重定向
(重定向策略由调用方控制),逐跳检查目标为公网地址,响应体上限 2MiB。
"""

from __future__ import annotations

import ipaddress
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

DEFAULT_USER_AGENT = "learning-hub-bot/0.1 (local study catalog link checker)"
TIMEOUT_SECONDS = 15.0
MAX_REDIRECT_HOPS = 5
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_EXTRA_RETRIES = 2
DEFAULT_RETRY_DELAY = 2
MAX_RETRY_AFTER = 60

RETRYABLE_ERRORS = {"timeout"}


class BlockedAddressError(Exception):
    """目标解析到私有/回环等非公网地址,拒绝请求。"""


def assert_public_host(hostname: str) -> None:
    """解析主机名;命中私有/回环/链路本地/保留/多播地址时抛出 BlockedAddressError。"""
    infos = socket.getaddrinfo(hostname, None)
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise BlockedAddressError(f"{hostname} 解析到非公网地址 {address}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _result(url: str, status_code, headers, body, error) -> dict:
    return {
        "url": url,
        "final_url": url,
        "status_code": status_code,
        "headers": headers or {},
        "body": body,
        "error": error,
    }


def _http_transport(url: str, timeout: float = TIMEOUT_SECONDS) -> dict:
    """默认 transport:单次 HTTP 请求,不跟随重定向。"""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return _result(url, None, {}, None, "invalid_url")
    try:
        assert_public_host(parts.hostname)
    except BlockedAddressError:
        return _result(url, None, {}, None, "blocked_private_address")
    except OSError:
        return _result(url, None, {}, None, "network_error")

    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                return _result(url, None, {}, None, "body_too_large")
            charset = response.headers.get_content_charset() or "utf-8"
            headers = {k.lower(): v for k, v in response.headers.items()}
            return _result(url, response.status, headers, raw.decode(charset, errors="replace"), None)
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(MAX_BODY_BYTES + 1)
        except Exception:
            raw = b""
        if len(raw) > MAX_BODY_BYTES:
            return _result(url, exc.code, {}, None, "body_too_large")
        charset = exc.headers.get_content_charset() if exc.headers else None
        headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
        return _result(url, exc.code, headers, raw.decode(charset or "utf-8", errors="replace"), None)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason).lower():
            return _result(url, None, {}, None, "timeout")
        return _result(url, None, {}, None, "network_error")
    except (socket.timeout, TimeoutError):
        return _result(url, None, {}, None, "timeout")
    except OSError:
        return _result(url, None, {}, None, "network_error")


def _follow(url: str, transport) -> dict:
    """顺序请求并逐跳跟随重定向,最多 5 跳;每跳由 transport 负责安全检查。"""
    current = url
    for hop in range(MAX_REDIRECT_HOPS + 1):
        response = transport(current, TIMEOUT_SECONDS)
        headers = {
            str(key).lower(): value
            for key, value in (response.get("headers") or {}).items()
        }
        result = _result(
            url,
            response.get("status_code"),
            headers,
            response.get("body"),
            response.get("error"),
        )
        result["final_url"] = current
        if result["error"]:
            return result
        status = result["status_code"] or 0
        if 300 <= status < 400:
            location = (result["headers"] or {}).get("location")
            if not location:
                result["error"] = "invalid_redirect"
                return result
            if hop == MAX_REDIRECT_HOPS:
                result["error"] = "too_many_redirects"
                return result
            current = urllib.parse.urljoin(current, location)
            continue
        body = result.get("body")
        if isinstance(body, str) and len(body.encode("utf-8")) > MAX_BODY_BYTES:
            result["error"] = "body_too_large"
            return result
        return result
    return _result(url, None, {}, None, "too_many_redirects")


def _should_retry(result: dict) -> bool:
    if result.get("error") in RETRYABLE_ERRORS:
        return True
    if result.get("error"):
        return False
    status = result.get("status_code") or 0
    return status == 429 or 500 <= status < 600


def _retry_delay(result: dict):
    """返回本次重试前等待秒数;Retry-After 超过上限时返回 None(放弃本次)。"""
    raw = ((result.get("headers") or {}).get("retry-after") or "").strip()
    if raw:
        if raw.isdigit():
            seconds = int(raw)
        else:
            try:
                seconds = max(0, int(parsedate_to_datetime(raw).timestamp() - time.time()))
            except (TypeError, ValueError):
                seconds = DEFAULT_RETRY_DELAY
        if seconds > MAX_RETRY_AFTER:
            return None
        return seconds
    return DEFAULT_RETRY_DELAY


def fetch_url(url: str, *, transport=None, sleep=None) -> dict:
    """抓取 URL:超时/5xx/429 最多额外重试 2 次;任何结果都以固定字段字典返回。"""
    transport = transport or _http_transport
    do_sleep = sleep or time.sleep
    attempt = 0
    while True:
        attempt += 1
        result = _follow(url, transport)
        if attempt > MAX_EXTRA_RETRIES or not _should_retry(result):
            return result
        delay = _retry_delay(result)
        if delay is None:
            return result
        do_sleep(delay)
