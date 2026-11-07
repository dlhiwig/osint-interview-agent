"""Provider-agnostic LLM abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:  # avoid runtime dependency on tools.registry here
    from ..tools.registry import ToolSpec

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    """A single tool invocation proposed by the model."""

    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None  # for role == "tool"
    name: str | None = None


@dataclass
class AssistantMessage:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # provider-specific response, for debugging


class LLMClient(ABC):
    """One method: given messages and tool specs, return the next assistant turn."""

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> AssistantMessage:
        raise NotImplementedError
