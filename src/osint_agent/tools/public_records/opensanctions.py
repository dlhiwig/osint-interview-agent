"""OpenSanctions search — sanctions, PEPs, watchlists."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..._http import request_json

ENDPOINT = "https://api.opensanctions.org/search/default"
log = logging.getLogger("osint_agent.tools.opensanctions")


def match(
    name: str,
    *,
    country: str | None = None,
    schema: str = "Person",
    limit: int = 10,
) -> dict[str, Any]:
    """Search OpenSanctions for a name. Free tier; no API key required."""
    log.info("opensanctions.match: %s (country=%s)", name, country)
    params: dict[str, Any] = {"q": name, "schema": schema, "limit": limit}
    if country:
        params["countries"] = country
    data = request_json(
        "GET", ENDPOINT, params=params, headers={"Accept": "application/json"}
    )
    matches = [
        {
            "id": r.get("id"),
            "schema": r.get("schema"),
            "name": (r.get("caption") or r.get("name")),
            "score": r.get("score"),
            "countries": (r.get("properties") or {}).get("country"),
            "topics": (r.get("properties") or {}).get("topics"),
            "datasets": r.get("datasets"),
            "link": f"https://www.opensanctions.org/entities/{r.get('id')}/" if r.get("id") else None,
        }
        for r in data.get("results", [])
    ]
    total = data.get("total")
    if isinstance(total, dict):
        total = total.get("value")
    return {
        "backend": "opensanctions",
        "query": name,
        "country": country,
        "schema": schema,
        "matches": matches,
        "total": total,
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
