"""Internet Archive Wayback Machine lookup."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .._http import request_json

ENDPOINT = "https://archive.org/wayback/available"
log = logging.getLogger("osint_agent.tools.archive")


def wayback(url: str, *, timestamp: str | None = None) -> dict[str, Any]:
    """Return the closest Wayback snapshot of a URL."""
    log.info("wayback: %s (ts=%s)", url, timestamp)
    params: dict[str, Any] = {"url": url}
    if timestamp:
        params["timestamp"] = timestamp
    data = request_json("GET", ENDPOINT, params=params)
    snapshot = ((data.get("archived_snapshots") or {}).get("closest") or {})
    return {
        "backend": "wayback",
        "query_url": url,
        "requested_timestamp": timestamp,
        "available": bool(snapshot.get("available")),
        "snapshot_url": snapshot.get("url"),
        "snapshot_timestamp": snapshot.get("timestamp"),
        "snapshot_status": snapshot.get("status"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
