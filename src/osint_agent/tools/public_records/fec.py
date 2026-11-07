"""FEC (api.open.fec.gov) contribution and candidate search."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..._http import request_json

BASE = "https://api.open.fec.gov/v1"
log = logging.getLogger("osint_agent.tools.fec")


def search_fec(
    name: str,
    *,
    api_key: str,
    state: str | None = None,
    min_amount: float | None = None,
    per_page: int = 20,
) -> dict[str, Any]:
    """Search FEC individual contributions by contributor name."""
    log.info("search_fec: %s (state=%s, min=%s)", name, state, min_amount)
    params: dict[str, Any] = {
        "api_key": api_key,
        "contributor_name": name,
        "per_page": per_page,
        "sort": "-contribution_receipt_amount",
    }
    if state:
        params["contributor_state"] = state
    if min_amount is not None:
        params["min_amount"] = min_amount

    data = request_json("GET", f"{BASE}/schedules/schedule_a/", params=params)
    contributions = [
        {
            "contributor_name": r.get("contributor_name"),
            "employer": r.get("contributor_employer"),
            "occupation": r.get("contributor_occupation"),
            "amount": r.get("contribution_receipt_amount"),
            "date": r.get("contribution_receipt_date"),
            "committee": (r.get("committee") or {}).get("name"),
            "state": r.get("contributor_state"),
            "city": r.get("contributor_city"),
            "pdf_url": r.get("pdf_url"),
            "sub_id": r.get("sub_id"),
        }
        for r in data.get("results", [])
    ]
    return {
        "backend": "fec.schedules.schedule_a",
        "query": name,
        "state": state,
        "min_amount": min_amount,
        "contributions": contributions,
        "total_count": (data.get("pagination") or {}).get("count"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
