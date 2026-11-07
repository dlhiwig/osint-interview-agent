"""Per-session audit log of tool invocations."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result_summary: dict[str, Any],
        started_at: datetime,
    ) -> None:
        ended = datetime.now(UTC)
        self._entries.append(
            {
                "tool": tool_name,
                "args": arguments,
                "result": result_summary,
                "started_at": started_at.isoformat(),
                "ended_at": ended.isoformat(),
                "duration_s": (ended - started_at).total_seconds(),
            }
        )

    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for entry in self._entries:
                f.write(json.dumps(entry, default=str) + "\n")
