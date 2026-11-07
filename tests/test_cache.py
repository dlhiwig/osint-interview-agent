"""Tool-cache tests."""
from __future__ import annotations

from osint_agent._cache import NEVER_CACHE, ToolCache


def test_put_and_get_roundtrip():
    c = ToolCache()
    c.put("web_search", {"query": "x"}, {"result": 1})
    assert c.get("web_search", {"query": "x"}) == {"result": 1}


def test_get_is_arg_order_independent():
    c = ToolCache()
    c.put("web_search", {"a": 1, "b": 2}, {"ok": True})
    assert c.get("web_search", {"b": 2, "a": 1}) == {"ok": True}


def test_cache_miss_returns_none():
    c = ToolCache()
    assert c.get("web_search", {"query": "nope"}) is None


def test_never_cache_write_tools():
    assert "record_evidence" in NEVER_CACHE
    c = ToolCache()
    c.put("record_evidence", {"claim": "x", "source_url": "u"}, {"ok": True})
    assert c.get("record_evidence", {"claim": "x", "source_url": "u"}) is None
    assert len(c) == 0
