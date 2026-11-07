"""Anthropic Messages API client with tool_use blocks."""
from __future__ import annotations

from typing import Any

from anthropic import Anthropic

from ..tools.registry import ToolSpec
from .base import AssistantMessage, LLMClient, Message, ToolCall


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self._client = Anthropic(api_key=api_key)

    def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> AssistantMessage:
        system_text: str | None = None
        other: list[Message] = []
        for m in messages:
            if m.role == "system":
                system_text = (system_text + "\n\n" if system_text else "") + (m.content or "")
            else:
                other.append(m)

        anth_messages = [self._to_anthropic(m) for m in other]
        anth_tools = [self._tool_schema(t) for t in tools]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anth_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_text:
            kwargs["system"] = system_text
        if anth_tools:
            kwargs["tools"] = anth_tools

        response = self._client.messages.create(**kwargs)

        content_text: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                content_text.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        call_id=block.id,
                        name=block.name,
                        arguments=dict(block.input) if block.input else {},
                    )
                )

        return AssistantMessage(
            content="\n".join(content_text) if content_text else None,
            tool_calls=tool_calls,
            raw=response,
        )

    @staticmethod
    def _to_anthropic(m: Message) -> dict[str, Any]:
        if m.role == "tool":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id or "",
                        "content": m.content or "",
                    }
                ],
            }
        if m.role == "assistant" and m.tool_calls:
            blocks: list[dict[str, Any]] = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.call_id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            return {"role": "assistant", "content": blocks}
        return {"role": m.role, "content": m.content or ""}

    @staticmethod
    def _tool_schema(spec: ToolSpec) -> dict[str, Any]:
        return {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.parameters_json_schema,
        }
