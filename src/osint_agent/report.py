"""Render the final Markdown report from the evidence ledger + narrative."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from .agent import ResearchRequest
    from .audit import AuditLog
    from .evidence import EvidenceLedger

_TEMPLATE_DIR = Path(__file__).parent / "prompts"


def render_report(
    *,
    request: ResearchRequest,
    final_narrative: str,
    evidence: EvidenceLedger,
    audit: AuditLog,
    report_mode: str = "standard",
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),  # markdown output
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    if report_mode not in {"standard", "source_brief"}:
        raise ValueError("Unsupported report mode")
    template_name = "source_brief.md" if report_mode == "source_brief" else "report_template.md"
    tmpl = env.get_template(template_name)
    return tmpl.render(
        request=request,
        final_narrative=(final_narrative or "").strip(),
        records=evidence.records(),
        audit=audit.entries(),
        now=datetime.now(UTC).isoformat(),
    )
