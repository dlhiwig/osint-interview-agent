"""OpenCorporates officer-search tests."""
from __future__ import annotations

import re

import pytest

from osint_agent.tools.opencorporates import BASE, officer_search

pytest_httpx = pytest.importorskip("pytest_httpx")


def test_officer_search(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(rf"^{re.escape(BASE)}/officers/search.*"),
        json={
            "results": {
                "total_count": 1,
                "officers": [
                    {
                        "officer": {
                            "name": "Jane Doe",
                            "position": "director",
                            "jurisdiction_code": "us_ky",
                            "start_date": "2020-01-01",
                            "end_date": None,
                            "company": {
                                "name": "Acme LLC",
                                "company_number": "12345",
                                "opencorporates_url": "https://opencorporates.com/companies/us_ky/12345",
                            },
                            "opencorporates_url": "https://opencorporates.com/officers/999",
                        }
                    }
                ],
            }
        },
    )
    out = officer_search("Jane Doe", country="US")
    assert out["backend"] == "opencorporates.officers"
    assert out["officers"][0]["position"] == "director"
    assert out["officers"][0]["company_name"] == "Acme LLC"
    assert out["total"] == 1
