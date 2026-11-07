"""Serper (Google SERP) search wrapper."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..._http import request_json

ENDPOINT = "https://google.serper.dev/search"
log = logging.getLogger("osint_agent.tools.serper")


def serper_search(query: str, *, api_key: str, num: int = 10) -> dict[str, Any]:
    log.info("serper_search: %s", query)
    data = request_json(
        "POST",
        ENDPOINT,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "num": num},
    )
    organic = [
        {
            "title": r.get("title"),
            "url": r.get("link"),
            "snippet": r.get("snippet"),
            "position": r.get("position"),
            "date": r.get("date"),
        }
        for r in data.get("organic", [])
    ]
    return {
        "backend": "serper",
        "query": query,
        "organic": organic,
        "answer_box": data.get("answerBox"),
        "knowledge_graph": data.get("knowledgeGraph"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
