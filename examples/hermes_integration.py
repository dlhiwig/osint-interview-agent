"""Reference pattern for calling this agent from Hermes (or any outer agent).

The OSINT agent is a self-contained unit of work: outer agents pass a
ResearchRequest and consume a ResearchResult. This file sketches how a
Hermes skill (or any Python-side orchestrator) would wrap it as a tool.

It does NOT import Hermes — Hermes is expected to import/call this module.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from osint_agent import OSINTAgent, ResearchRequest


def osint_interview_tool(
    subject_name: str,
    role: str = "",
    company: str = "",
    authorization: str = "",
) -> dict[str, Any]:
    """Tool-style entrypoint: produce a dict ready for serialization to an LLM.

    Hermes (or any orchestrator) can register this function as one of its tools.
    The returned dict is intentionally compact — the Markdown report path is
    included so the outer agent can read/attach it on demand rather than
    stuffing the full text into every subsequent message.
    """
    agent = OSINTAgent()
    result = agent.research(
        ResearchRequest(
            subject_name=subject_name,
            context={k: v for k, v in {"role": role, "company": company}.items() if v},
            authorization=authorization or "Delegated from Hermes skill; operator authorized.",
        )
    )
    return {
        "ok": True,
        "report_path": str(result.report_path) if result.report_path else None,
        "evidence_path": str(result.evidence_path) if result.evidence_path else None,
        "evidence_count": len(result.evidence_records),
        "evidence_preview": [asdict(r) for r in result.evidence_records[:5]],
        "audit_count": len(result.audit_entries),
    }


if __name__ == "__main__":
    print(osint_interview_tool("Jane Doe", role="PM", authorization="demo"))
