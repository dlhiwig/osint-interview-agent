"""Verify that every evidence URL still resolves (link-rot check)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ._http import head_ok


@dataclass
class VerifyRow:
    claim: str
    url: str
    confidence: str
    ok: bool
    status: int


def verify_csv(path: Path) -> list[VerifyRow]:
    """Read an evidence CSV produced by this package and probe each URL."""
    rows: list[VerifyRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("source_url", "").strip()
            if not url:
                continue
            ok, status = head_ok(url)
            rows.append(
                VerifyRow(
                    claim=(row.get("claim") or "").strip(),
                    url=url,
                    confidence=(row.get("confidence") or "").strip(),
                    ok=ok,
                    status=status,
                )
            )
    return rows


def summarize(rows: list[VerifyRow]) -> dict[str, int]:
    return {
        "total": len(rows),
        "reachable": sum(1 for r in rows if r.ok),
        "unreachable": sum(1 for r in rows if not r.ok),
    }
