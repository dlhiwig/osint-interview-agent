"""Unit tests for the retrying HTTP helper."""
from __future__ import annotations

import httpx
import pytest

from osint_agent._http import DEFAULT_MAX_ATTEMPTS, request_json

pytest_httpx = pytest.importorskip("pytest_httpx")


def test_request_json_single_success(httpx_mock):
    httpx_mock.add_response(url="https://x.example/api", method="POST", json={"ok": True})
    out = request_json("POST", "https://x.example/api", json={})
    assert out == {"ok": True}


def test_request_json_retries_on_503_then_succeeds(httpx_mock):
    slept: list[float] = []
    httpx_mock.add_response(url="https://x.example/api", method="GET", status_code=503, text="busy")
    httpx_mock.add_response(url="https://x.example/api", method="GET", status_code=503, text="busy")
    httpx_mock.add_response(url="https://x.example/api", method="GET", json={"ok": True})

    out = request_json(
        "GET", "https://x.example/api", sleeper=lambda s: slept.append(s)
    )
    assert out == {"ok": True}
    # Slept twice (between attempts 1→2 and 2→3)
    assert len(slept) == 2
    assert slept[1] > slept[0]  # exponential


def test_request_json_does_not_retry_on_400(httpx_mock):
    httpx_mock.add_response(
        url="https://x.example/api", method="GET", status_code=400, text="bad"
    )
    with pytest.raises(httpx.HTTPStatusError):
        request_json("GET", "https://x.example/api", sleeper=lambda s: None)


def test_request_json_gives_up_after_max_attempts(httpx_mock):
    for _ in range(DEFAULT_MAX_ATTEMPTS):
        httpx_mock.add_response(
            url="https://x.example/api", method="GET", status_code=503, text="busy"
        )
    with pytest.raises(httpx.HTTPStatusError):
        request_json("GET", "https://x.example/api", sleeper=lambda s: None)
