"""OpenCorporates officer search.

The free tier returns limited data without an API key; an `OPENCORPORATES_API_KEY`
env var is used if present.
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from .._http import request_json

BASE = "https://api.opencorporates.com/v0.4.8"
log = logging.getLogger("osint_agent.tools.opencorporates")


def officer_search(
    name: str,
    *,
    country: str | None = None,
    per_page: int = 20,
) -> dict[str, Any]:
    """Search company officers by name across OpenCorporates' jurisdictions."""
    log.info("opencorporates.officer_search: %s (country=%s)", name, country)
    params: dict[str, Any] = {"q": name, "per_page": per_page}
    if country:
        params["jurisdiction_code"] = country.lower()
    token = os.environ.get("OPENCORPORATES_API_KEY")
    if token:
        params["api_token"] = token
    data = request_json(
        "GET",
        f"{BASE}/officers/search",
        params=params,
        headers={"Accept": "application/json"},
    )
    results = (data.get("results") or {}).get("officers") or []
    officers = []
    for row in results:
        o = row.get("officer") or {}
        company = o.get("company") or {}
        officers.append(
            {
                "name": o.get("name"),
                "position": o.get("position"),
                "jurisdiction": o.get("jurisdiction_code"),
                "start_date": o.get("start_date"),
                "end_date": o.get("end_date"),
                "company_name": company.get("name"),
                "company_number": company.get("company_number"),
                "company_url": company.get("opencorporates_url"),
                "officer_url": o.get("opencorporates_url"),
            }
        )
    return {
        "backend": "opencorporates.officers",
        "query": name,
        "country": country,
        "officers": officers,
        "total": (data.get("results") or {}).get("total_count"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
