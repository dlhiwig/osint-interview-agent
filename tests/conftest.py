from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_report_dir(tmp_path: Path) -> Path:
    d = tmp_path / "reports"
    d.mkdir()
    return d


@pytest.fixture
def minimal_settings(tmp_report_dir: Path):
    """A Settings object with no API keys and a temp report dir."""
    from osint_agent.config import Settings

    return Settings(
        openai_api_key="test-openai-key",
        osint_llm_provider="openai",
        osint_llm_model="gpt-4o",
        osint_report_dir=tmp_report_dir,
        osint_max_tool_turns=5,
    )
