"""Regression tests for authorization and report rendering safeguards."""

from __future__ import annotations

import pytest

from osint_agent.agent import OSINTAgent, ResearchRequest
from osint_agent.html_export import markdown_to_html
from osint_agent.tools.registry import ToolRegistry


class FailsIfCalled:
    """Unexpected external model use should fail the test."""

    def chat_with_tools(self, *args, **kwargs):
        raise AssertionError("No model/tool calls are allowed without authorization")


@pytest.mark.parametrize("authorization", ["", "   ", "\t\n"])
def test_python_api_rejects_missing_authorization(
    minimal_settings, authorization
):
    agent = OSINTAgent(
        settings=minimal_settings,
        llm=FailsIfCalled(),
        registry=ToolRegistry(),
    )
    with pytest.raises(ValueError, match="authorization"):
        agent.research(
            ResearchRequest(subject_name="Fictional Example", authorization=authorization)
        )


@pytest.mark.parametrize("url", ["javascript:alert", "data:text/html,hi", "file:///tmp/x", "//example.test/path"])
def test_html_export_does_not_link_to_unsafe_schemes(url):
    out = markdown_to_html(f"Source: [record]({url}).")
    assert "<a href=" not in out
    assert "record" in out


def test_html_export_escapes_quotes_in_link_targets():
    out = markdown_to_html('See [record](https://example.test/path"onmouseover="alert).')
    assert 'onmouseover="' not in out
    assert "&quot;onmouseover=&quot;" in out


def test_html_export_keeps_https_links():
    out = markdown_to_html("See [record](https://example.test/record).")
    assert '<a href="https://example.test/record"' in out
