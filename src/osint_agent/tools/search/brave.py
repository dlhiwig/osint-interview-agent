"""Brave Search API wrapper."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..._http import request_json

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
log = logging.getLogger("osint_agent.tools.brave")


def brave_search(query: str, *, api_key: str, count: int = 10) -> dict[str, Any]:
    log.info("brave_search: %s", query)
    data = request_json(
        "GET",
        ENDPOINT,
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        params={"q": query, "count": count},
    )
    web_results = (data.get("web") or {}).get("results") or []
    results = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("description"),
            "age": r.get("age"),
        }
        for r in web_results
    ]
    return {
        "backend": "brave",
        "query": query,
        "results": results,
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
