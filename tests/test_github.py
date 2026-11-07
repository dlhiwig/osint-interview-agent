"""GitHub tool wrapper tests (mocked HTTP)."""
from __future__ import annotations

import pytest

from osint_agent.tools.github import (
    BASE,
    github_search_users,
    github_user,
    github_user_repos,
)

pytest_httpx = pytest.importorskip("pytest_httpx")


def test_github_user(httpx_mock):
    httpx_mock.add_response(
        url=f"{BASE}/users/octocat",
        json={
            "login": "octocat",
            "name": "The Octocat",
            "company": "@github",
            "blog": "https://example.com",
            "location": "SF",
            "bio": "mascot",
            "public_repos": 8,
            "followers": 1234,
            "html_url": "https://github.com/octocat",
            "created_at": "2008-01-14T04:33:35Z",
        },
    )
    out = github_user("octocat")
    assert out["backend"] == "github.user"
    assert out["login"] == "octocat"
    assert out["public_repos"] == 8


def test_github_user_repos(httpx_mock):
    import re

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(BASE)}/users/octocat/repos.*"),
        json=[
            {
                "name": "spoon-knife",
                "html_url": "https://github.com/octocat/spoon-knife",
                "description": "test repo",
                "language": "HTML",
                "stargazers_count": 1,
                "forks_count": 2,
                "pushed_at": "2024-01-01T00:00:00Z",
                "archived": False,
                "fork": False,
            }
        ],
    )
    out = github_user_repos("octocat")
    assert out["count"] == 1
    assert out["repos"][0]["name"] == "spoon-knife"


def test_github_search_users(httpx_mock):
    import re

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(BASE)}/search/users.*"),
        json={
            "total_count": 1,
            "items": [
                {
                    "login": "jane",
                    "html_url": "https://github.com/jane",
                    "type": "User",
                    "score": 1.0,
                }
            ],
        },
    )
    out = github_search_users("Jane Doe")
    assert out["total_count"] == 1
    assert out["users"][0]["login"] == "jane"
