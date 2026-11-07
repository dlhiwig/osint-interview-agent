"""ORCID + Crossref scholar tool tests."""
from __future__ import annotations

import re

import pytest

from osint_agent.tools.scholar import (
    CROSSREF_WORKS,
    ORCID_SEARCH,
    crossref_works,
    orcid_search,
)

pytest_httpx = pytest.importorskip("pytest_httpx")


def test_orcid_search(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(ORCID_SEARCH)}.*"),
        json={
            "num-found": 1,
            "expanded-result": [
                {
                    "orcid-id": "0000-0001-2345-6789",
                    "given-names": "Jane",
                    "family-names": "Doe",
                    "credit-name": "Jane Doe",
                    "other-name": [],
                    "institution-name": ["Example University"],
                }
            ],
        },
    )
    out = orcid_search("Jane Doe")
    assert out["num_found"] == 1
    p = out["people"][0]
    assert p["orcid_id"] == "0000-0001-2345-6789"
    assert p["orcid_url"].endswith("/0000-0001-2345-6789")


def test_crossref_works(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(CROSSREF_WORKS)}.*"),
        json={
            "message": {
                "total-results": 1,
                "items": [
                    {
                        "title": ["A paper"],
                        "DOI": "10.1000/xyz",
                        "URL": "https://doi.org/10.1000/xyz",
                        "type": "journal-article",
                        "container-title": ["Journal"],
                        "publisher": "Example",
                        "issued": {"date-parts": [[2023]]},
                        "author": [
                            {"given": "Jane", "family": "Doe"},
                            {"given": "John", "family": "Smith"},
                        ],
                        "is-referenced-by-count": 5,
                    }
                ],
            }
        },
    )
    out = crossref_works("Jane Doe", year_from=2020)
    assert out["total"] == 1
    w = out["works"][0]
    assert w["doi"] == "10.1000/xyz"
    assert w["year"] == 2023
    assert "Jane Doe" in w["authors"]
