"""Shared HTTP helpers for tool wrappers: single retrying request path."""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_BASE = 1.0  # seconds; grows 1, 2, 4, ...
MAX_BACKOFF = 30.0

RETRY_STATUSES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})

log = logging.getLogger("osint_agent.http")


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header value (seconds or HTTP-date) into seconds."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = (dt - datetime.now(UTC)).total_seconds()
    return max(0.0, delta)


class _Retrier:
    """Encapsulates one retrying request. Keep tests deterministic via `sleeper`."""

    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        sleeper=time.sleep,
    ) -> None:
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.sleeper = sleeper

    def _should_retry(self, exc: BaseException) -> bool:
        if isinstance(
            exc,
            (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
                httpx.RemoteProtocolError,
            ),
        ):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in RETRY_STATUSES
        return False

    def _wait_for(self, exc: BaseException, attempt: int) -> float:
        # Honor Retry-After on 429 / 503 when present.
        if isinstance(exc, httpx.HTTPStatusError):
            ra = _parse_retry_after(exc.response.headers.get("Retry-After"))
            if ra is not None:
                return min(MAX_BACKOFF, ra)
        return min(MAX_BACKOFF, self.backoff_base * (2 ** attempt))

    def run(self, call):  # type: ignore[no-untyped-def]
        last_exc: BaseException | None = None
        for attempt in range(self.max_attempts):
            try:
                return call()
            except Exception as e:
                last_exc = e
                if attempt == self.max_attempts - 1 or not self._should_retry(e):
                    raise
                wait = self._wait_for(e, attempt)
                log.warning(
                    "http retry %d/%d after %s: sleeping %.2fs",
                    attempt + 1,
                    self.max_attempts - 1,
                    type(e).__name__,
                    wait,
                )
                self.sleeper(wait)
        raise last_exc or RuntimeError("retrier exhausted with no exception")


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json: Any = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    sleeper=time.sleep,
) -> dict[str, Any]:
    """HTTP request returning parsed JSON, with retry on transient failures."""
    retrier = _Retrier(max_attempts=max_attempts, sleeper=sleeper)

    def _call() -> dict[str, Any]:
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(
                method, url, headers=headers, params=params, json=json
            )
            resp.raise_for_status()
            return resp.json()

    return retrier.run(_call)


def request_text(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    follow_redirects: bool = True,
    sleeper=time.sleep,
) -> tuple[str, str, int]:
    """HTTP request returning (text, final_url, status). Retries on transient failures."""
    retrier = _Retrier(max_attempts=max_attempts, sleeper=sleeper)

    def _call() -> tuple[str, str, int]:
        with httpx.Client(timeout=timeout, follow_redirects=follow_redirects) as client:
            resp = client.request(method, url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.text, str(resp.url), resp.status_code

    return retrier.run(_call)


def head_ok(url: str, *, timeout: float = 15.0) -> tuple[bool, int]:
    """Return (ok, status). ok is True iff the URL returns < 400. Follows redirects.

    Does not retry: this is a liveness probe, not a fetch.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                resp = client.head(url)
                if resp.status_code == 405:
                    raise httpx.HTTPStatusError("HEAD unsupported", request=resp.request, response=resp)
            except httpx.HTTPStatusError:
                resp = client.get(url, headers={"Range": "bytes=0-1024"})
        return resp.status_code < 400, resp.status_code
    except Exception as e:
        log.info("head_ok(%s) failed: %s", url, type(e).__name__)
        return False, 0
