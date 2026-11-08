"""Source report mode and provenance metadata regression tests."""

from __future__ import annotations

from osint_agent.agent import ResearchRequest
from osint_agent.audit import AuditLog
from osint_agent.evidence import EvidenceLedger, EvidenceRecord, write_csv
from osint_agent.report import render_report


def test_source_brief_has_document_locations_without_boilerplate(tmp_path):
    evidence = EvidenceLedger()
    evidence.add(EvidenceRecord(
        claim="Fictional Example authored a public paper.",
        source_url="https://example.org/papers/fictional",
        source_title="Fictional Paper",
        document_locator="page 2, paragraph 3",
        extract="Author: Fictional Example.",
        identity_match_rationale="Official publisher's author record.",
        confidence="Medium",
    ))
    result = render_report(
        request=ResearchRequest(subject_name="Fictional Example", authorization="Consented test"),
        final_narrative="Source-based finding E1; alternative explanation not excluded.",
        evidence=evidence, audit=AuditLog(), report_mode="source_brief",
    )
    assert "page 2, paragraph 3" in result
    assert "Fictional Paper" in result
    assert "unreviewed" in result
    assert "Fair Credit Reporting Act" not in result
    output = tmp_path / "record.csv"
    write_csv(evidence.records(), output)
    rows = output.read_text(encoding="utf-8")
    assert "document_locator" in rows
    assert "Fictional Paper" in rows


def test_standard_mode_retained():
    result = render_report(
        request=ResearchRequest(subject_name="Fictional Example", authorization="Consented test"),
        final_narrative="No findings.",
        evidence=EvidenceLedger(), audit=AuditLog(), report_mode="standard",
    )
    assert "Evidence and confidence table" in result
