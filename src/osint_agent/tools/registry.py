"""Shared tool-spec type and in-memory registry."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ToolFunc = Callable[..., dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters_json_schema: dict[str, Any]
    func: ToolFunc


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool {spec.name!r} is already registered")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)
