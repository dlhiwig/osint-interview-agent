"""Public API for the OSINT interview-prep agent."""
from __future__ import annotations

from .agent import OSINTAgent, ResearchRequest, ResearchResult, run_research
from .config import Settings, load_settings
from .evidence import EvidenceLedger, EvidenceRecord
from .html_export import markdown_to_html, write_html
from .verify import VerifyRow, summarize, verify_csv

__all__ = [
    "EvidenceLedger",
    "EvidenceRecord",
    "OSINTAgent",
    "ResearchRequest",
    "ResearchResult",
    "Settings",
    "VerifyRow",
    "load_settings",
    "markdown_to_html",
    "run_research",
    "summarize",
    "verify_csv",
    "write_html",
]

__version__ = "0.2.0"
