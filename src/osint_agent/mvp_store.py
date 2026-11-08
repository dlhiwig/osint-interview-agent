"""Local SQLite evidence store and explicit analyst approval gate.

This module is offline and does not collect information about individuals.
Evidence captures contain source bytes; no LLM decides review status.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_CAPTURE_BYTES = 1_048_576
SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _digest(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _uid() -> str:
    return uuid.uuid4().hex


def _present(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    research_question TEXT NOT NULL,
    authorization TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK (length(trim(authorization)) > 0)
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(case_id, url)
);
CREATE TABLE IF NOT EXISTS captures (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    sha256 TEXT NOT NULL,
    media_type TEXT NOT NULL,
    content BLOB NOT NULL,
    retrieved_at TEXT NOT NULL,
    UNIQUE(source_id, sha256)
);
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    capture_id TEXT NOT NULL REFERENCES captures(id),
    claim TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    locator TEXT NOT NULL DEFAULT '',
    identity_rationale TEXT NOT NULL DEFAULT '',
    verification TEXT NOT NULL CHECK (verification IN ('passage_matched','unsupported')),
    review_status TEXT NOT NULL DEFAULT 'unreviewed'
        CHECK (review_status IN ('unreviewed','verified','rejected')),
    reviewer TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    action TEXT NOT NULL,
    action_digest TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','revoked')),
    reviewed_by TEXT,
    reviewed_at TEXT,
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS approvals_action ON approvals(case_id, action, action_digest);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update
BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete
BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
"""


class EvidenceStore:
    """A single-operator, local persistent case store.

    Store data only on an approved local disk, never in Git. The actor identity
    passed to methods is a *label*, not an authentication mechanism.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=15.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=15000")
        self.conn.execute("PRAGMA journal_mode=WAL")
        current = int(self.conn.execute("PRAGMA user_version").fetchone()[0])
        if current > SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported database version: {current}")
        if current == 0:
            with self.conn:
                self.conn.executescript(_SCHEMA)
                self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def __enter__(self) -> EvidenceStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _audit(self, actor: str, event: str, details: dict[str, Any]) -> None:
        previous = self.conn.execute(
            "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_hash = previous["event_hash"] if previous else "0" * 64
        now = _now()
        payload = _json(details)
        checksum = _digest(_json([prev_hash, now, actor, event, payload]))
        self.conn.execute(
            "INSERT INTO audit_events(occurred_at,actor,event_type,details,previous_hash,event_hash)"
            " VALUES (?,?,?,?,?,?)",
            (now, actor, event, payload, prev_hash, checksum),
        )

    def verify_audit(self) -> bool:
        previous = "0" * 64
        rows = self.conn.execute("SELECT * FROM audit_events ORDER BY id")
        for row in rows:
            if row["previous_hash"] != previous:
                return False
            expected = _digest(
                _json([previous, row["occurred_at"], row["actor"], row["event_type"], row["details"]])
            )
            if row["event_hash"] != expected:
                return False
            previous = expected
        return True

    def create_case(self, title: str, research_question: str, authorization: str) -> str:
        title = _present(title, "title")
        research_question = _present(research_question, "research question")
        authorization = _present(authorization, "authorization")
        case_id = _uid()
        with self.conn:
            self.conn.execute(
                "INSERT INTO cases VALUES (?,?,?,?,?)",
                (case_id, title, research_question, authorization, _now()),
            )
            self._audit("operator", "case.created", {"case_id": case_id})
        return case_id

    def get_case(self, case_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown case: {case_id}")
        return dict(row)

    def add_source(self, case_id: str, url: str, title: str = "") -> str:
        from .safe_fetch import validate_public_url

        self.get_case(case_id)
        canonical = validate_public_url(url)
        row = self.conn.execute(
            "SELECT id FROM sources WHERE case_id=? AND url=?", (case_id, canonical)
        ).fetchone()
        if row:
            return str(row["id"])
        source_id = _uid()
        with self.conn:
            self.conn.execute(
                "INSERT INTO sources(id,case_id,url,title,created_at) VALUES(?,?,?,?,?)",
                (source_id, case_id, canonical, title, _now()),
            )
            self._audit("operator", "source.created", {"case_id": case_id, "source_id": source_id})
        return source_id

    def capture(
        self, source_id: str, content: bytes, media_type: str = "text/plain"
    ) -> tuple[str, str]:
        if not content or len(content) > MAX_CAPTURE_BYTES:
            raise ValueError("Capture content must contain 1 to 1048576 bytes")
        if media_type not in ("text/plain", "text/html", "application/json"):
            raise ValueError("Unsupported capture content type")
        row = self.conn.execute("SELECT id FROM sources WHERE id=?", (source_id,)).fetchone()
        if not row:
            raise KeyError(f"Unknown source: {source_id}")
        sha256 = _digest(content)
        existing = self.conn.execute(
            "SELECT id FROM captures WHERE source_id=? AND sha256=?", (source_id, sha256)
        ).fetchone()
        if existing:
            return str(existing["id"]), sha256
        capture_id = _uid()
        with self.conn:
            self.conn.execute(
                "INSERT INTO captures VALUES(?,?,?,?,?,?)",
                (capture_id, source_id, sha256, media_type, sqlite3.Binary(content), _now()),
            )
            self._audit("operator", "capture.recorded", {
                "source_id": source_id, "capture_id": capture_id, "sha256": sha256
            })
        return capture_id, sha256

    def check_capture(self, capture_id: str, comparison: bytes | None = None) -> bool:
        row = self.conn.execute(
            "SELECT content,sha256 FROM captures WHERE id=?", (capture_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown capture: {capture_id}")
        actual = _digest(bytes(row["content"]))
        return actual == row["sha256"] and (
            comparison is None or _digest(comparison) == actual
        )

    def add_claim(
        self,
        case_id: str,
        capture_id: str,
        claim: str,
        excerpt: str,
        locator: str = "",
        identity_rationale: str = "",
    ) -> tuple[str, str]:
        self.get_case(case_id)
        claim = _present(claim, "claim")
        excerpt = _present(excerpt, "source excerpt")
        row = self.conn.execute(
            "SELECT c.content FROM captures c "
            "JOIN sources s ON s.id=c.source_id "
            "WHERE c.id=? AND s.case_id=?", (capture_id, case_id)
        ).fetchone()
        if row is None:
            raise ValueError("Capture does not belong to this case")
        source_text = bytes(row["content"]).decode("utf-8", errors="replace")
        # Literal passage matching checks quotation existence, not factual entailment.
        normalized = lambda s: re.sub(r"\s+", " ", s).strip()
        verified = normalized(excerpt) in normalized(source_text)
        state = "passage_matched" if verified else "unsupported"
        claim_id = _uid()
        with self.conn:
            self.conn.execute(
                "INSERT INTO claims "
                "(id,case_id,capture_id,claim,excerpt,locator,identity_rationale,"
                "verification,review_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (claim_id, case_id, capture_id, claim, excerpt, locator,
                 identity_rationale, state, "unreviewed", _now()),
            )
            self._audit("operator", "claim.created", {
                "case_id": case_id, "claim_id": claim_id, "verification": state
            })
        return claim_id, state

    def review_claim(self, claim_id: str, reviewer: str, *, approve: bool) -> None:
        reviewer = _present(reviewer, "human reviewer")
        if reviewer.lower() in {"agent", "model", "llm", "system", "bot"}:
            raise PermissionError("AI/system identities cannot approve claims")
        row = self.conn.execute(
            "SELECT verification,review_status FROM claims WHERE id=?", (claim_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown claim: {claim_id}")
        if row["review_status"] != "unreviewed":
            raise ValueError("Claim was already reviewed; create a new review revision")
        if approve and row["verification"] != "passage_matched":
            raise ValueError("Cannot approve a claim without its matching source excerpt")
        with self.conn:
            self.conn.execute(
                "UPDATE claims SET review_status=?,reviewer=?,reviewed_at=? WHERE id=?",
                ("verified" if approve else "rejected", reviewer, _now(), claim_id),
            )
            self._audit(reviewer, "claim.reviewed", {
                "claim_id": claim_id, "approved": bool(approve)
            })

    def list_claims(self, case_id: str) -> list[dict[str, Any]]:
        self.get_case(case_id)
        rows = self.conn.execute(
            "SELECT cl.*,s.url,s.title AS source_title,c.sha256,c.retrieved_at "
            "FROM claims cl JOIN captures c ON c.id=cl.capture_id "
            "JOIN sources s ON s.id=c.source_id "
            "WHERE cl.case_id=? ORDER BY cl.created_at,cl.id", (case_id,)
        )
        return [dict(row) for row in rows]

    def _snapshot_digest(self, case_id: str) -> str:
        case = self.get_case(case_id)
        claims = self.list_claims(case_id)
        material = {
            "case": [case["id"], case["research_question"], case["authorization"]],
            "claims": [
                [c["id"], c["sha256"], c["claim"], c["excerpt"],
                 c["verification"], c["review_status"], c["reviewer"]]
                for c in claims
            ],
        }
        return _digest(_json(material))

    def _action_digest(self, case_id: str, action: str, config: dict[str, Any]) -> str:
        self.get_case(case_id)
        return _digest(_json({
            "case_id": case_id, "action": action, "config": config,
            "snapshot": self._snapshot_digest(case_id),
        }))

    def request_approval(
        self,
        case_id: str,
        action: str,
        requested_by: str = "agent",
        config: dict[str, Any] | None = None,
        expires_at: str | None = None,
    ) -> str:
        action = _present(action, "action")
        requested_by = _present(requested_by, "requester")
        action_digest = self._action_digest(case_id, action, config or {})
        approval_id = _uid()
        with self.conn:
            self.conn.execute(
                "INSERT INTO approvals(id,case_id,action,action_digest,requested_by,"
                "requested_at,expires_at,status) VALUES(?,?,?,?,?,?,?,'pending')",
                (approval_id, case_id, action, action_digest, requested_by, _now(), expires_at),
            )
            self._audit(requested_by, "approval.requested", {
                "approval_id": approval_id, "action": action, "digest": action_digest
            })
        return approval_id

    def decide_approval(self, approval_id: str, reviewer: str, *, approve: bool,
                        note: str = "") -> None:
        reviewer = _present(reviewer, "reviewer")
        if reviewer.lower() in {"agent", "model", "llm", "system", "bot"}:
            raise PermissionError("AI/system identities cannot approve actions")
        row = self.conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        if not row:
            raise KeyError(f"Unknown approval: {approval_id}")
        if row["status"] != "pending":
            raise ValueError("Approval request is no longer pending")
        if reviewer.casefold() == str(row["requested_by"]).casefold():
            raise PermissionError("Requester cannot approve their own action")
        with self.conn:
            self.conn.execute(
                "UPDATE approvals SET status=?,reviewed_by=?,reviewed_at=?,note=? WHERE id=?",
                ("approved" if approve else "rejected", reviewer, _now(), note, approval_id),
            )
            self._audit(reviewer, "approval.decided", {
                "approval_id": approval_id, "approved": bool(approve)
            })

    def revoke_approval(self, approval_id: str, reviewer: str) -> None:
        reviewer = _present(reviewer, "reviewer")
        with self.conn:
            cursor = self.conn.execute(
                "UPDATE approvals SET status='revoked',reviewed_by=?,reviewed_at=? "
                "WHERE id=? AND status='approved'", (reviewer, _now(), approval_id)
            )
            if cursor.rowcount != 1:
                raise ValueError("Only approved decisions may be revoked")
            self._audit(reviewer, "approval.revoked", {"approval_id": approval_id})

    def require_approval(
        self, case_id: str, action: str, config: dict[str, Any] | None = None
    ) -> str:
        target = self._action_digest(case_id, action, config or {})
        now = _now()
        row = self.conn.execute(
            "SELECT id FROM approvals WHERE case_id=? AND action=? "
            "AND action_digest=? AND status='approved' "
            "AND (expires_at IS NULL OR expires_at>?) "
            "ORDER BY reviewed_at DESC LIMIT 1", (case_id, action, target, now)
        ).fetchone()
        if row is None:
            raise PermissionError("Human approval required for this exact action and evidence snapshot")
        return str(row["id"])

    def export_brief(self, case_id: str) -> str:
        approval_id = self.require_approval(case_id, "publish_report")
        case = self.get_case(case_id)
        claims = self.list_claims(case_id)
        def cell(s: object) -> str:
            return str(s or "").replace("|", "\\|").replace("\n", " ")
        lines = [
            f"# Source Research Brief: {cell(case['title'])}",
            "",
            f"**Research requirement:** {cell(case['research_question'])}",
            f"**Approved export:** {approval_id}",
            "",
            "| Claim ID | Claim | Source / location | Source SHA-256 | Source passage | Support check | Human review |",
            "|---|---|---|---|---|---|---|",
        ]
        for c in claims:
            lines.append(
                f"| {c['id']} | {cell(c['claim'])} | {cell(c['url'])} "
                f"({cell(c['locator'])}) | {c['sha256']} | {cell(c['excerpt'])} "
                f"| {c['verification']} | {c['review_status']} |"
            )
        lines.extend(["", "## Evidence interpretation", "",
                      "Passage matched = literal quote located, not an independently proven claim.",
                      "Unreviewed entries are investigative leads; reviewer status is recorded per row.",
                      ""])
        with self.conn:
            self._audit("operator", "report.exported", {
                "case_id": case_id, "approval_id": approval_id, "claims": len(claims)
            })
        return "\n".join(lines)

    def backup(self, destination: str | Path) -> None:
        with sqlite3.connect(str(destination)) as other:
            self.conn.backup(other)
