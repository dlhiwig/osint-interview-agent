"""ORCID person search + Crossref works-by-author.

ORCID identifies researchers; Crossref indexes scholarly works by author name.
Both are free and do not require API keys. ORCID looks for a researcher
identifier (ORCID iD); Crossref returns publications.

When `MAILTO` env var is set, it is appended to the Crossref User-Agent per
their "polite pool" guidance, which gives more reliable throughput.
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from .._http import request_json

ORCID_SEARCH = "https://pub.orcid.org/v3.0/expanded-search"
CROSSREF_WORKS = "https://api.crossref.org/works"
log = logging.getLogger("osint_agent.tools.scholar")


def _polite_ua() -> str:
    mailto = os.environ.get("MAILTO")
    base = "osint-interview-agent/0.3 (public-source background research)"
    return f"{base} (mailto:{mailto})" if mailto else base


def orcid_search(name: str, *, rows: int = 10) -> dict[str, Any]:
    """Search ORCID for researcher records matching a name."""
    log.info("orcid_search: %s", name)
    data = request_json(
        "GET",
        ORCID_SEARCH,
        params={"q": name, "rows": rows},
        headers={"Accept": "application/json"},
    )
    results = data.get("expanded-result") or []
    people = [
        {
            "orcid_id": r.get("orcid-id"),
            "given_names": r.get("given-names"),
            "family_names": r.get("family-names"),
            "credit_name": r.get("credit-name"),
            "other_names": r.get("other-name"),
            "institution_name": r.get("institution-name"),
            "orcid_url": f"https://orcid.org/{r.get('orcid-id')}" if r.get("orcid-id") else None,
        }
        for r in (results or [])
    ]
    return {
        "backend": "orcid.search",
        "query": name,
        "num_found": data.get("num-found"),
        "people": people,
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def crossref_works(
    author: str,
    *,
    rows: int = 10,
    year_from: int | None = None,
) -> dict[str, Any]:
    """Return scholarly works by author from Crossref."""
    log.info("crossref_works: %s (year_from=%s)", author, year_from)
    params: dict[str, Any] = {"query.author": author, "rows": rows, "sort": "published", "order": "desc"}
    if year_from is not None:
        params["filter"] = f"from-pub-date:{year_from}-01-01"
    data = request_json(
        "GET",
        CROSSREF_WORKS,
        params=params,
        headers={"User-Agent": _polite_ua(), "Accept": "application/json"},
    )
    items = (data.get("message") or {}).get("items") or []
    works = []
    for w in items:
        title = (w.get("title") or [None])[0]
        year = None
        issued = (w.get("issued") or {}).get("date-parts") or []
        if issued and isinstance(issued[0], list) and issued[0]:
            year = issued[0][0]
        authors = []
        for a in w.get("author") or []:
            full = " ".join([p for p in [a.get("given"), a.get("family")] if p])
            if full:
                authors.append(full)
        works.append(
            {
                "title": title,
                "doi": w.get("DOI"),
                "url": w.get("URL"),
                "type": w.get("type"),
                "container_title": (w.get("container-title") or [None])[0],
                "publisher": w.get("publisher"),
                "year": year,
                "authors": authors,
                "citations": w.get("is-referenced-by-count"),
            }
        )
    return {
        "backend": "crossref.works",
        "query": author,
        "year_from": year_from,
        "works": works,
        "total": ((data.get("message") or {}).get("total-results")),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
