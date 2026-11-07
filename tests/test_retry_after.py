"""Honor Retry-After on 429/503 responses."""
from __future__ import annotations

import pytest

from osint_agent._http import _parse_retry_after, request_json

pytest_httpx = pytest.importorskip("pytest_httpx")


def test_parse_retry_after_seconds():
    assert _parse_retry_after("5") == 5.0


def test_parse_retry_after_none():
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("") is None
    assert _parse_retry_after("not-a-number-or-date") is None


def test_request_json_waits_retry_after_seconds(httpx_mock):
    slept: list[float] = []
    httpx_mock.add_response(
        url="https://x.example/api",
        method="GET",
        status_code=429,
        headers={"Retry-After": "7"},
        text="slow down",
    )
    httpx_mock.add_response(
        url="https://x.example/api",
        method="GET",
        json={"ok": True},
    )
    out = request_json("GET", "https://x.example/api", sleeper=lambda s: slept.append(s))
    assert out == {"ok": True}
    # Should sleep ~7s, not the default exponential backoff of 1.
    assert slept == [7.0]
