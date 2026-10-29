"""fetch 模块离线测试:全部使用 fake transport,不访问公网。"""

import ipaddress
import socket

import pytest

from tools.learning_hub import fetch as fetch_module
from tools.learning_hub.fetch import fetch_url


def _ok_transport(body="<html><body>ok</body></html>", status=200, headers=None):
    calls = []

    def transport(url, timeout=15.0):
        calls.append(url)
        return {
            "status_code": status,
            "headers": headers or {},
            "body": body,
            "error": None,
        }

    transport.calls = calls
    return transport


def _error_transport(error, status=None, headers=None, body=""):
    calls = []

    def transport(url, timeout=15.0):
        calls.append(url)
        return {"status_code": status, "headers": headers or {}, "body": body, "error": error}

    transport.calls = calls
    return transport


def _redirect_transport(chain):
    """chain: {url: location};终点返回 200。"""
    calls = []

    def transport(url, timeout=15.0):
        calls.append(url)
        if url in chain:
            return {"status_code": 301, "headers": {"location": chain[url]}, "body": "", "error": None}
        return {"status_code": 200, "headers": {}, "body": "<main>end</main>", "error": None}

    transport.calls = calls
    return transport


def test_200_returns_body():
    sleeps = []
    result = fetch_url("https://example.com/a", transport=_ok_transport(), sleep=sleeps.append)
    assert result["status_code"] == 200
    assert result["error"] is None
    assert "ok" in result["body"]
    assert result["final_url"] == "https://example.com/a"
    assert sleeps == []


def test_redirect_followed_and_relative_location_resolved():
    transport = _redirect_transport({"https://a.example/x": "/final"})
    result = fetch_url("https://a.example/x", transport=transport)
    assert result["final_url"] == "https://a.example/final"
    assert transport.calls == ["https://a.example/x", "https://a.example/final"]


def test_more_than_five_hops_rejected():
    chain = {f"https://a.example/{i}": f"/{i+1}" for i in range(6)}
    transport = _redirect_transport(chain)
    result = fetch_url("https://a.example/0", transport=transport)
    assert result["error"] == "too_many_redirects"
    assert len(transport.calls) == 6  # 最多 5 跳


def test_http_error_statuses_pass_through():
    for status in (403, 404, 410, 429, 500):
        transport = _ok_transport(status=status)
        result = fetch_url("https://example.com/x", transport=transport)
        assert result["status_code"] == status
        assert result["error"] is None


def test_timeout_retried_twice_then_returned():
    transport = _error_transport("timeout")
    sleeps = []
    result = fetch_url("https://example.com/x", transport=transport, sleep=sleeps.append)
    assert result["error"] == "timeout"
    assert len(transport.calls) == 3  # 首次 + 最多 2 次额外重试
    assert sleeps == [2, 2]


def test_500_retried_then_returned():
    transport = _ok_transport(status=500)
    result = fetch_url("https://example.com/x", transport=transport, sleep=lambda s: None)
    assert result["status_code"] == 500
    assert len(transport.calls) == 3


def test_429_with_retry_after_respected():
    transport = _ok_transport(status=429, headers={"Retry-After": "5"})
    sleeps = []
    result = fetch_url("https://example.com/x", transport=transport, sleep=sleeps.append)
    assert result["status_code"] == 429
    assert sleeps == [5, 5]  # 每次重试前等待 Retry-After


def test_retry_after_over_60_gives_up_immediately():
    transport = _ok_transport(status=429, headers={"Retry-After": "120"})
    sleeps = []
    result = fetch_url("https://example.com/x", transport=transport, sleep=sleeps.append)
    assert result["status_code"] == 429
    assert transport.calls == ["https://example.com/x"]
    assert sleeps == []


def test_body_over_2mib_rejected():
    transport = _ok_transport(body="x" * (2 * 1024 * 1024 + 1))
    result = fetch_url("https://example.com/big", transport=transport)
    assert result["error"] == "body_too_large"


def test_non_retryable_transport_error_not_retried():
    transport = _error_transport("blocked_private_address")
    result = fetch_url("https://127.0.0.1/x", transport=transport)
    assert result["error"] == "blocked_private_address"
    assert len(transport.calls) == 1


def test_default_user_agent_declared():
    assert "learning-hub" in fetch_module.DEFAULT_USER_AGENT


def test_private_addresses_rejected_by_default_transport(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(fetch_module.BlockedAddressError):
        fetch_module.assert_public_host("localhost")


def test_public_address_allowed_by_default_transport(monkeypatch):
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    fetch_module.assert_public_host("example.com")
