"""Verify parallel tool execution and in-session caching behavior."""
from __future__ import annotations

import time

from osint_agent.agent import OSINTAgent, ResearchRequest
from osint_agent.llm.base import AssistantMessage, LLMClient, ToolCall
from osint_agent.tools.registry import ToolRegistry, ToolSpec


class _ScriptedLLM(LLMClient):
    def __init__(self, script: list[AssistantMessage]) -> None:
        self._script = list(script)

    def chat_with_tools(self, messages, tools, model, *, max_tokens=4096, temperature=0.1):
        return self._script.pop(0)


def _slow_tool(name: str, delay: float, counter: dict[str, int]) -> ToolSpec:
    def func(**_: object) -> dict:
        counter[name] = counter.get(name, 0) + 1
        time.sleep(delay)
        return {"name": name, "slept": delay}

    return ToolSpec(
        name=name,
        description="slow fake",
        parameters_json_schema={
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
            "additionalProperties": False,
        },
        func=func,
    )


def test_parallel_tool_execution_is_faster_than_sequential(minimal_settings, tmp_path):
    minimal_settings.osint_report_dir = tmp_path / "reports"
    minimal_settings.osint_tool_workers = 4

    counter: dict[str, int] = {}
    registry = ToolRegistry()
    for i in range(3):
        registry.register(_slow_tool(f"slow_{i}", 0.3, counter))

    script = [
        AssistantMessage(
            content=None,
            tool_calls=[
                ToolCall(call_id=f"c{i}", name=f"slow_{i}", arguments={"q": "x"})
                for i in range(3)
            ],
        ),
        AssistantMessage(content="Done.\n\nFair Credit Reporting Act footer...", tool_calls=[]),
    ]
    agent = OSINTAgent(settings=minimal_settings, llm=_ScriptedLLM(script), registry=registry)

    t0 = time.monotonic()
    agent.research(ResearchRequest(subject_name="X", authorization="t"))
    elapsed = time.monotonic() - t0

    # Serially this would take ~0.9s; in parallel ~0.3-0.4s. Give plenty of margin.
    assert elapsed < 0.75, f"parallel exec took {elapsed:.2f}s (expected < 0.75s)"
    assert counter == {"slow_0": 1, "slow_1": 1, "slow_2": 1}


def test_cache_hits_skip_second_call(minimal_settings, tmp_path):
    minimal_settings.osint_report_dir = tmp_path / "reports"

    counter: dict[str, int] = {}

    def func(**_: object) -> dict:
        counter["calls"] = counter.get("calls", 0) + 1
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="stub",
            description="stub",
            parameters_json_schema={
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
                "additionalProperties": False,
            },
            func=func,
        )
    )

    script = [
        AssistantMessage(
            content=None,
            tool_calls=[ToolCall(call_id="c1", name="stub", arguments={"q": "same"})],
        ),
        AssistantMessage(
            content=None,
            tool_calls=[ToolCall(call_id="c2", name="stub", arguments={"q": "same"})],
        ),
        AssistantMessage(content="Done.", tool_calls=[]),
    ]

    agent = OSINTAgent(settings=minimal_settings, llm=_ScriptedLLM(script), registry=registry)
    result = agent.research(ResearchRequest(subject_name="Y", authorization="t"))

    # Despite two tool calls with the same args, the underlying function ran once.
    assert counter["calls"] == 1
    # Audit records both calls, second marked cached.
    tool_entries = [e for e in result.audit_entries if e["tool"] == "stub"]
    assert len(tool_entries) == 2
    assert tool_entries[1]["result"].get("cached") is True


def test_cache_can_be_disabled(minimal_settings, tmp_path):
    minimal_settings.osint_report_dir = tmp_path / "reports"
    minimal_settings.osint_enable_cache = False

    counter: dict[str, int] = {}

    def func(**_: object) -> dict:
        counter["calls"] = counter.get("calls", 0) + 1
        return {"ok": True}

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="stub",
            description="stub",
            parameters_json_schema={
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
                "additionalProperties": False,
            },
            func=func,
        )
    )

    script = [
        AssistantMessage(
            content=None,
            tool_calls=[ToolCall(call_id="c1", name="stub", arguments={"q": "same"})],
        ),
        AssistantMessage(
            content=None,
            tool_calls=[ToolCall(call_id="c2", name="stub", arguments={"q": "same"})],
        ),
        AssistantMessage(content="Done.", tool_calls=[]),
    ]
    agent = OSINTAgent(settings=minimal_settings, llm=_ScriptedLLM(script), registry=registry)
    agent.research(ResearchRequest(subject_name="Z", authorization="t"))
    # With cache disabled, both calls execute.
    assert counter["calls"] == 2
