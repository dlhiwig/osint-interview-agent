"""Minimal programmatic use of the OSINT agent.

Requires a .env with at least OPENAI_API_KEY (or ANTHROPIC_API_KEY) and
optionally one or more search-backend keys. Run:

    python examples/basic_usage.py
"""
from __future__ import annotations

from osint_agent import OSINTAgent, ResearchRequest
from osint_agent.logging_config import configure_logging


def main() -> None:
    configure_logging("INFO")
    agent = OSINTAgent()  # reads .env
    result = agent.research(
        ResearchRequest(
            subject_name="Jane Doe",
            context={"role": "Senior Product Manager", "company": "Acme Inc."},
            authorization=(
                "Example run: subject is fictional; no real-person research is performed. "
                "This script demonstrates the programmatic API."
            ),
        )
    )
    print(f"Report:   {result.report_path}")
    print(f"Evidence: {result.evidence_path}")
    print(f"Records:  {len(result.evidence_records)}")


if __name__ == "__main__":
    main()
