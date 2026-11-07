"""SEC EDGAR full-text filing search."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..._http import request_json

ENDPOINT = "https://efts.sec.gov/LATEST/search-index"
log = logging.getLogger("osint_agent.tools.sec_edgar")


def search_edgar(
    query: str,
    *,
    user_agent: str,
    forms: list[str] | None = None,
) -> dict[str, Any]:
    """Full-text search of SEC EDGAR filings.

    `user_agent` must comply with SEC's fair-access policy — include a contact email.
    """
    log.info("search_edgar: %s (forms=%s)", query, forms)
    params: dict[str, Any] = {"q": f'"{query}"'}
    if forms:
        params["forms"] = ",".join(forms)
    data = request_json(
        "GET",
        ENDPOINT,
        params=params,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    hits = (data.get("hits") or {}).get("hits") or []
    filings = []
    for h in hits:
        src = h.get("_source") or {}
        adsh = (h.get("_id") or "").split(":")[0]
        link = None
        if adsh:
            cik = (src.get("ciks") or [None])[0]
            if cik:
                link = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                    f"&CIK={cik}&type=&dateb=&owner=include&count=40"
                )
        filings.append(
            {
                "form": src.get("form"),
                "filed_at": src.get("file_date"),
                "ciks": src.get("ciks"),
                "display_names": src.get("display_names"),
                "accession": adsh,
                "sec_link": link,
            }
        )
    return {
        "backend": "sec-edgar-fts",
        "query": query,
        "forms": forms,
        "filings": filings,
        "total": (data.get("hits") or {}).get("total"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
