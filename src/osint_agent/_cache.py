"""In-session cache keyed by (tool_name, canonical-args-json).

Only one scope today: per-OSINTAgent-instance / per-research-session.
Write-style tools (`record_evidence`) must opt out via `cacheable=False`.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("osint_agent.cache")

NEVER_CACHE: frozenset[str] = frozenset({"record_evidence"})


def _canonical(args: dict[str, Any]) -> str:
    return json.dumps(args, sort_keys=True, default=str)


class ToolCache:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], Any] = {}

    def get(self, tool_name: str, args: dict[str, Any]) -> Any:
        if tool_name in NEVER_CACHE:
            return None
        return self._store.get((tool_name, _canonical(args)))

    def put(self, tool_name: str, args: dict[str, Any], value: Any) -> None:
        if tool_name in NEVER_CACHE:
            return
        self._store[(tool_name, _canonical(args))] = value

    def __len__(self) -> int:
        return len(self._store)

    def stats(self) -> dict[str, int]:
        return {"entries": len(self._store)}
