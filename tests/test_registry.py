"""Registry + tool-schema sanity tests."""
from __future__ import annotations

from osint_agent.config import Settings
from osint_agent.llm.anthropic_client import AnthropicClient
from osint_agent.llm.openai_client import OpenAIClient
from osint_agent.toolkit import build_registry


def test_build_registry_with_all_keys_registers_all_tools():
    s = Settings(
        openai_api_key="x",
        perplexity_api_key="x",
        tavily_api_key="x",
        serper_api_key="x",
        brave_search_api_key="x",
        fec_api_key="x",
        sec_edgar_user_agent="Test test@example.com",
    )
    reg = build_registry(s)
    expected = {
        "web_search_grounded",
        "web_search",
        "search_news",
        "google_search",
        "brave_search",
        "search_fec",
        "search_sec_edgar",
        "screen_opensanctions",
        "wayback_snapshot",
        "fetch_page",
        "github_user",
        "github_user_repos",
        "github_search_users",
        "opencorporates_officer_search",
        "orcid_search",
        "crossref_works",
    }
    assert expected <= set(reg.names())


def test_build_registry_with_no_search_keys_only_registers_free_tools():
    s = Settings(openai_api_key="x")
    reg = build_registry(s)
    assert set(reg.names()) == {
        "screen_opensanctions",
        "wayback_snapshot",
        "fetch_page",
        "github_user",
        "github_user_repos",
        "github_search_users",
        "opencorporates_officer_search",
        "orcid_search",
        "crossref_works",
    }


def test_each_tool_emits_valid_openai_schema():
    s = Settings(
        openai_api_key="x",
        perplexity_api_key="x",
        tavily_api_key="x",
        serper_api_key="x",
        brave_search_api_key="x",
        fec_api_key="x",
        sec_edgar_user_agent="Test test@example.com",
    )
    reg = build_registry(s)
    for spec in reg.list():
        schema = OpenAIClient._tool_schema(spec)
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] == spec.name
        assert fn["description"] == spec.description
        assert fn["parameters"]["type"] == "object"
        assert "properties" in fn["parameters"]


def test_each_tool_emits_valid_anthropic_schema():
    s = Settings(
        openai_api_key="x",
        perplexity_api_key="x",
        tavily_api_key="x",
        serper_api_key="x",
        brave_search_api_key="x",
        fec_api_key="x",
        sec_edgar_user_agent="Test test@example.com",
    )
    reg = build_registry(s)
    for spec in reg.list():
        schema = AnthropicClient._tool_schema(spec)
        assert schema["name"] == spec.name
        assert schema["description"] == spec.description
        assert schema["input_schema"]["type"] == "object"
        assert "properties" in schema["input_schema"]
