"""GitHub public-profile and search wrappers.

Uses the public GitHub REST API. Authentication is optional; without a token
the rate limit is ~60/hour. With GITHUB_TOKEN set, 5000/hour.
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from .._http import request_json

BASE = "https://api.github.com"
log = logging.getLogger("osint_agent.tools.github")


def _headers() -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "osint-interview-agent",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def github_user(username: str) -> dict[str, Any]:
    """Fetch a GitHub user's public profile."""
    log.info("github_user: %s", username)
    data = request_json("GET", f"{BASE}/users/{username}", headers=_headers())
    return {
        "backend": "github.user",
        "query": username,
        "login": data.get("login"),
        "name": data.get("name"),
        "company": data.get("company"),
        "blog": data.get("blog"),
        "location": data.get("location"),
        "bio": data.get("bio"),
        "public_repos": data.get("public_repos"),
        "followers": data.get("followers"),
        "html_url": data.get("html_url"),
        "created_at": data.get("created_at"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def github_user_repos(username: str, *, per_page: int = 20) -> dict[str, Any]:
    """List a GitHub user's public repositories, sorted by stars desc."""
    log.info("github_user_repos: %s", username)
    data = request_json(
        "GET",
        f"{BASE}/users/{username}/repos",
        headers=_headers(),
        params={"per_page": per_page, "sort": "pushed", "type": "owner"},
    )
    repos = [
        {
            "name": r.get("name"),
            "url": r.get("html_url"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count"),
            "forks": r.get("forks_count"),
            "pushed_at": r.get("pushed_at"),
            "archived": r.get("archived"),
            "fork": r.get("fork"),
        }
        for r in (data if isinstance(data, list) else [])
    ]
    return {
        "backend": "github.repos",
        "query": username,
        "repos": repos,
        "count": len(repos),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def github_search_users(query: str, *, per_page: int = 10) -> dict[str, Any]:
    """Search GitHub users by name / full name / bio."""
    log.info("github_search_users: %s", query)
    data = request_json(
        "GET",
        f"{BASE}/search/users",
        headers=_headers(),
        params={"q": query, "per_page": per_page},
    )
    items = [
        {
            "login": u.get("login"),
            "url": u.get("html_url"),
            "type": u.get("type"),
            "score": u.get("score"),
        }
        for u in data.get("items", [])
    ]
    return {
        "backend": "github.search.users",
        "query": query,
        "total_count": data.get("total_count"),
        "users": items,
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
