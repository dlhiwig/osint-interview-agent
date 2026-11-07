"""HTTP-mocked tests for each tool wrapper."""
from __future__ import annotations

import re

import pytest

pytest_httpx = pytest.importorskip("pytest_httpx")


def test_perplexity_search(httpx_mock):
    from osint_agent.tools.search.perplexity import ENDPOINT, perplexity_search

    httpx_mock.add_response(
        url=ENDPOINT,
        method="POST",
        json={
            "choices": [{"message": {"content": "Jane Doe is a product manager."}}],
            "citations": ["https://example.com/bio"],
        },
    )
    out = perplexity_search("Who is Jane Doe?", api_key="k")
    assert out["backend"] == "perplexity"
    assert out["answer"].startswith("Jane Doe")
    assert out["citations"] == ["https://example.com/bio"]
    assert "retrieved_at" in out


def test_tavily_search(httpx_mock):
    from osint_agent.tools.search.tavily import ENDPOINT, tavily_search

    httpx_mock.add_response(
        url=ENDPOINT,
        method="POST",
        json={
            "answer": "Summary",
            "results": [
                {
                    "title": "Bio",
                    "url": "https://example.com/bio",
                    "content": "snippet",
                    "score": 0.9,
                    "published_date": "2025-01-01",
                }
            ],
        },
    )
    out = tavily_search("Jane Doe", api_key="k")
    assert out["backend"] == "tavily"
    assert out["answer"] == "Summary"
    assert out["results"][0]["url"] == "https://example.com/bio"


def test_tavily_news(httpx_mock):
    from osint_agent.tools.search.tavily import ENDPOINT, tavily_news

    httpx_mock.add_response(
        url=ENDPOINT,
        method="POST",
        json={
            "results": [
                {
                    "title": "Article",
                    "url": "https://news.example.com/a",
                    "content": "news snippet",
                    "published_date": "2026-11-01",
                }
            ]
        },
    )
    out = tavily_news("Jane Doe", api_key="k", days=30)
    assert out["backend"] == "tavily-news"
    assert out["news"][0]["url"] == "https://news.example.com/a"


def test_serper_search(httpx_mock):
    from osint_agent.tools.search.serper import ENDPOINT, serper_search

    httpx_mock.add_response(
        url=ENDPOINT,
        method="POST",
        json={
            "organic": [
                {
                    "title": "LinkedIn",
                    "link": "https://www.linkedin.com/in/janedoe/",
                    "snippet": "Senior PM",
                    "position": 1,
                    "date": None,
                }
            ]
        },
    )
    out = serper_search('site:linkedin.com "Jane Doe"', api_key="k")
    assert out["backend"] == "serper"
    assert out["organic"][0]["url"] == "https://www.linkedin.com/in/janedoe/"


def test_brave_search(httpx_mock):
    from osint_agent.tools.search.brave import ENDPOINT, brave_search

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(ENDPOINT)}.*"),
        method="GET",
        json={
            "web": {
                "results": [
                    {
                        "title": "About",
                        "url": "https://example.com/about",
                        "description": "bio",
                        "age": "1 year",
                    }
                ]
            }
        },
    )
    out = brave_search("Jane Doe", api_key="k")
    assert out["backend"] == "brave"
    assert out["results"][0]["url"] == "https://example.com/about"


def test_fec_search(httpx_mock):
    from osint_agent.tools.public_records.fec import BASE, search_fec

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(BASE)}/schedules/schedule_a/.*"),
        method="GET",
        json={
            "results": [
                {
                    "contributor_name": "DOE, JANE",
                    "contributor_employer": "Acme",
                    "contributor_occupation": "PM",
                    "contribution_receipt_amount": 500.0,
                    "contribution_receipt_date": "2024-06-01",
                    "committee": {"name": "Someone For Senate"},
                    "contributor_state": "KY",
                    "contributor_city": "Louisville",
                    "pdf_url": "https://docquery.fec.gov/x.pdf",
                    "sub_id": 1,
                }
            ],
            "pagination": {"count": 1},
        },
    )
    out = search_fec("Jane Doe", api_key="k", state="KY")
    assert out["backend"].startswith("fec.")
    assert out["contributions"][0]["amount"] == 500.0


def test_sec_edgar_search(httpx_mock):
    from osint_agent.tools.public_records.sec_edgar import ENDPOINT, search_edgar

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(ENDPOINT)}.*"),
        method="GET",
        json={
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "0000000000-00-000000:filename.htm",
                        "_source": {
                            "form": "DEF 14A",
                            "file_date": "2024-04-15",
                            "ciks": ["0000000001"],
                            "display_names": ["Acme Corp (0000000001)"],
                        },
                    }
                ],
            }
        },
    )
    out = search_edgar("Jane Doe", user_agent="Test test@example.com")
    assert out["backend"] == "sec-edgar-fts"
    assert out["filings"][0]["form"] == "DEF 14A"


def test_opensanctions_match(httpx_mock):
    from osint_agent.tools.public_records.opensanctions import ENDPOINT, match

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(ENDPOINT)}.*"),
        method="GET",
        json={
            "results": [
                {
                    "id": "ofac-123",
                    "schema": "Person",
                    "caption": "Jane Doe",
                    "score": 0.9,
                    "properties": {"country": ["us"], "topics": ["role.pep"]},
                    "datasets": ["ofac"],
                }
            ],
            "total": {"value": 1},
        },
    )
    out = match("Jane Doe")
    assert out["backend"] == "opensanctions"
    assert out["matches"][0]["id"] == "ofac-123"
    assert out["matches"][0]["link"].endswith("/ofac-123/")


def test_wayback(httpx_mock):
    from osint_agent.tools.archive import ENDPOINT, wayback

    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(ENDPOINT)}.*"),
        method="GET",
        json={
            "archived_snapshots": {
                "closest": {
                    "available": True,
                    "url": "https://web.archive.org/web/20200101000000/http://example.com/",
                    "timestamp": "20200101000000",
                    "status": "200",
                }
            }
        },
    )
    out = wayback("http://example.com/")
    assert out["available"] is True
    assert out["snapshot_timestamp"] == "20200101000000"


def test_fetch_page(httpx_mock):
    from osint_agent.tools.fetch import fetch_page

    html = "<html><head><title>Hi</title></head><body><p>hello world</p></body></html>"
    httpx_mock.add_response(url="https://example.com/x", text=html)
    out = fetch_page("https://example.com/x")
    assert out["status"] == 200
    assert "hello world" in out["text"] or out["title"] == "Hi"
