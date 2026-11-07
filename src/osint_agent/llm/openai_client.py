"""OpenAI chat-completions client with native tool calling."""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from ..tools.registry import ToolSpec
from .base import AssistantMessage, LLMClient, Message, ToolCall


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> AssistantMessage:
        oa_messages = [self._to_openai(m) for m in messages]
        oa_tools = [self._tool_schema(t) for t in tools]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": oa_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if oa_tools:
            kwargs["tools"] = oa_tools
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        tool_calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            tool_calls.append(
                ToolCall(call_id=tc.id, name=tc.function.name, arguments=args)
            )

        return AssistantMessage(content=msg.content, tool_calls=tool_calls, raw=response)

    @staticmethod
    def _to_openai(m: Message) -> dict[str, Any]:
        if m.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": m.tool_call_id or "",
                "content": m.content or "",
            }
        if m.role == "assistant" and m.tool_calls:
            return {
                "role": "assistant",
                "content": m.content,
                "tool_calls": [
                    {
                        "id": tc.call_id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ],
            }
        return {"role": m.role, "content": m.content or ""}

    @staticmethod
    def _tool_schema(spec: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters_json_schema,
            },
        }
