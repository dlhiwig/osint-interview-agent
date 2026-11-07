"""Tavily search + news wrappers."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..._http import request_json

ENDPOINT = "https://api.tavily.com/search"
log = logging.getLogger("osint_agent.tools.tavily")


def _post(payload: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    return request_json(
        "POST",
        ENDPOINT,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )


def tavily_search(
    query: str,
    *,
    api_key: str,
    max_results: int = 8,
    include_answer: bool = True,
) -> dict[str, Any]:
    log.info("tavily_search: %s", query)
    data = _post(
        {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": include_answer,
            "search_depth": "advanced",
        }
    )
    results = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
            "score": r.get("score"),
            "published_at": r.get("published_date"),
        }
        for r in data.get("results", [])
    ]
    return {
        "backend": "tavily",
        "query": query,
        "answer": data.get("answer"),
        "results": results,
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def tavily_news(query: str, *, api_key: str, days: int = 90, max_results: int = 10) -> dict[str, Any]:
    log.info("tavily_news: %s (days=%d)", query, days)
    data = _post(
        {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "topic": "news",
            "days": days,
            "search_depth": "advanced",
            "include_answer": False,
        }
    )
    news = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
            "published_at": r.get("published_date"),
        }
        for r in data.get("results", [])
    ]
    return {
        "backend": "tavily-news",
        "query": query,
        "days": days,
        "news": news,
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
