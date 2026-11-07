"""Append-only evidence ledger backing the report's Evidence & Confidence table."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

Confidence = Literal["Low", "Medium", "High"]

FIELDS = (
    "claim",
    "source_url",
    "source_type",
    "pub_date",
    "accessed_at",
    "extract",
    "identity_match_rationale",
    "corroboration",
    "caveats",
    "confidence",
    "notes",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EvidenceRecord:
    claim: str
    source_url: str
    confidence: Confidence = "Low"
    source_type: str = ""
    pub_date: str = ""
    accessed_at: str = field(default_factory=_now_iso)
    extract: str = ""
    identity_match_rationale: str = ""
    corroboration: str = ""
    caveats: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.confidence not in ("Low", "Medium", "High"):
            # Coerce; the LLM may slip and send something else.
            self.confidence = "Low"


class EvidenceLedger:
    """Thin collection that enforces append-only semantics."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []

    def add(self, record: EvidenceRecord) -> None:
        self._records.append(record)

    def records(self) -> list[EvidenceRecord]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)


def write_csv(records: list[EvidenceRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(FIELDS))
        writer.writeheader()
        for r in records:
            writer.writerow({k: getattr(r, k, "") for k in FIELDS})
