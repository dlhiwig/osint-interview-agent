"""Readable-text extraction for a public URL."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .._http import request_text

USER_AGENT = "osint-interview-agent/0.1 (public-source background research)"
MAX_TEXT_CHARS = 12_000
log = logging.getLogger("osint_agent.tools.fetch")


def fetch_page(url: str) -> dict[str, Any]:
    """Fetch a public URL and extract readable text.

    Treats the returned text strictly as data — the agent system prompt instructs
    the model to ignore any instructions embedded in it.
    """
    log.info("fetch_page: %s", url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,text/plain",
    }
    html, final_url, status = request_text("GET", url, headers=headers)

    title = ""
    text = ""
    try:
        import json as _json

        import trafilatura  # type: ignore[import-untyped]

        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
            with_metadata=True,
            output_format="json",
        )
        if extracted:
            meta = _json.loads(extracted)
            title = meta.get("title") or ""
            text = (meta.get("text") or "")[:MAX_TEXT_CHARS]
    except Exception as e:
        log.info("trafilatura unavailable or failed (%s); using naive extraction", type(e).__name__)
        import re as _re

        text = _re.sub(r"<[^>]+>", " ", html)
        text = _re.sub(r"\s+", " ", text).strip()[:MAX_TEXT_CHARS]
        m = _re.search(r"<title[^>]*>([^<]*)</title>", html, flags=_re.IGNORECASE)
        if m:
            title = m.group(1).strip()

    return {
        "backend": "fetch",
        "requested_url": url,
        "final_url": final_url,
        "status": status,
        "title": title,
        "text": text,
        "truncated": len(text) >= MAX_TEXT_CHARS,
        "fetched_at": datetime.now(UTC).isoformat(),
    }
