"""Core research agent: ReAct-style tool-calling loop with parallel execution + caching."""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._cache import ToolCache
from .audit import AuditLog
from .config import Settings, load_settings
from .evidence import EvidenceLedger, EvidenceRecord, write_csv
from .llm.anthropic_client import AnthropicClient
from .llm.base import AssistantMessage, LLMClient, Message, ToolCall
from .llm.openai_client import OpenAIClient
from .report import render_report
from .tools.registry import ToolRegistry, ToolSpec

_MAX_TOOL_RESULT_CHARS = 12_000
log = logging.getLogger("osint_agent.agent")


@dataclass
class ResearchRequest:
    subject_name: str
    context: dict[str, Any] = field(default_factory=dict)
    authorization: str = ""
    additional_identifiers: dict[str, str] = field(default_factory=dict)


@dataclass
class ResearchResult:
    report_markdown: str
    evidence_records: list[EvidenceRecord]
    audit_entries: list[dict[str, Any]]
    report_path: Path | None = None
    evidence_path: Path | None = None


class OSINTAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.llm = llm or self._default_llm()
        self.registry = registry if registry is not None else self._default_registry()

    # ----- construction helpers -----

    def _default_llm(self) -> LLMClient:
        self.settings.validate_llm_credentials()
        provider = self.settings.osint_llm_provider
        if provider == "openai":
            assert self.settings.openai_api_key
            return OpenAIClient(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.osint_llm_base_url,
            )
        if provider == "anthropic":
            assert self.settings.anthropic_api_key
            return AnthropicClient(api_key=self.settings.anthropic_api_key)
        if provider == "ollama":
            # Ollama exposes an OpenAI-compatible endpoint; reuse OpenAIClient with its base_url.
            return OpenAIClient(
                api_key="ollama",  # Ollama ignores this but the SDK requires non-empty.
                base_url=self.settings.osint_llm_base_url or self.settings.osint_ollama_base_url,
            )
        raise ValueError(f"Unknown LLM provider: {provider!r}")

    def _default_registry(self) -> ToolRegistry:
        from .toolkit import build_registry  # local import to avoid cycles

        return build_registry(self.settings)

    # ----- public API -----

    def research(self, request: ResearchRequest) -> ResearchResult:
        ledger = EvidenceLedger()
        audit = AuditLog()
        cache = ToolCache() if self.settings.osint_enable_cache else None

        system_prompt = self._load_system_prompt()
        user_message = self._build_user_message(request)

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_message),
        ]
        tools: list[ToolSpec] = list(self.registry.list()) + [self._evidence_tool(ledger)]

        response: AssistantMessage | None = None
        for turn in range(self.settings.osint_max_tool_turns):
            response = self.llm.chat_with_tools(
                messages=messages,
                tools=tools,
                model=self.settings.osint_llm_model,
            )
            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=list(response.tool_calls),
                )
            )
            if not response.tool_calls:
                break
            log.info(
                "turn %d: executing %d tool call(s) in parallel",
                turn + 1,
                len(response.tool_calls),
            )
            results = self._execute_tools_parallel(response.tool_calls, tools, audit, cache)
            for tc, result in zip(response.tool_calls, results, strict=True):
                messages.append(
                    Message(
                        role="tool",
                        tool_call_id=tc.call_id,
                        content=self._encode_result(result),
                    )
                )

        final_narrative = (response.content if response else "") or ""
        report_md = render_report(
            request=request,
            final_narrative=final_narrative,
            evidence=ledger,
            audit=audit,
        )
        report_path, evidence_path = self._save_outputs(request, report_md, ledger, audit)

        if cache is not None:
            log.info("cache: %s", cache.stats())

        return ResearchResult(
            report_markdown=report_md,
            evidence_records=ledger.records(),
            audit_entries=audit.entries(),
            report_path=report_path,
            evidence_path=evidence_path,
        )

    # ----- tool execution -----

    def _execute_tools_parallel(
        self,
        tool_calls: list[ToolCall],
        tools: list[ToolSpec],
        audit: AuditLog,
        cache: ToolCache | None,
    ) -> list[dict[str, Any]]:
        """Execute all tool calls from one assistant turn concurrently.

        Preserves order: results[i] corresponds to tool_calls[i].
        """
        if len(tool_calls) == 1:
            return [self._execute_one(tool_calls[0], tools, audit, cache)]

        workers = min(self.settings.osint_tool_workers, len(tool_calls))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(self._execute_one, tc, tools, audit, cache) for tc in tool_calls
            ]
            return [f.result() for f in futures]

    def _execute_one(
        self,
        tc: ToolCall,
        tools: list[ToolSpec],
        audit: AuditLog,
        cache: ToolCache | None,
    ) -> dict[str, Any]:
        spec = next((t for t in tools if t.name == tc.name), None)
        started = datetime.now(UTC)
        if spec is None:
            payload = {"error": f"Unknown tool {tc.name!r}"}
            audit.record(tc.name, tc.arguments, payload, started)
            return payload

        # Cache lookup
        if cache is not None:
            cached = cache.get(tc.name, tc.arguments)
            if cached is not None:
                audit.record(
                    tc.name, tc.arguments, {"ok": True, "cached": True}, started
                )
                return cached

        try:
            result = spec.func(**tc.arguments)
            normalized = result if isinstance(result, dict) else {"result": result}
            summary = {"ok": True, "keys": list(normalized.keys())}
            audit.record(tc.name, tc.arguments, summary, started)
            if cache is not None:
                cache.put(tc.name, tc.arguments, normalized)
            return normalized
        except Exception as e:  # pragma: no cover - defensive
            payload = {"error": f"{type(e).__name__}: {e}"}
            audit.record(tc.name, tc.arguments, payload, started)
            return payload

    @staticmethod
    def _encode_result(result: dict[str, Any]) -> str:
        encoded = json.dumps(result, default=str, ensure_ascii=False)
        if len(encoded) > _MAX_TOOL_RESULT_CHARS:
            encoded = encoded[:_MAX_TOOL_RESULT_CHARS] + '..."_TRUNCATED_"'
        return encoded

    def _evidence_tool(self, ledger: EvidenceLedger) -> ToolSpec:
        def record_evidence(**kwargs: Any) -> dict[str, Any]:
            allowed = {
                "claim",
                "source_url",
                "confidence",
                "source_type",
                "pub_date",
                "accessed_at",
                "extract",
                "identity_match_rationale",
                "corroboration",
                "caveats",
                "notes",
            }
            data = {k: v for k, v in kwargs.items() if k in allowed}
            record = EvidenceRecord(**data)  # type: ignore[arg-type]
            ledger.add(record)
            return {"ok": True, "total_records": len(ledger)}

        return ToolSpec(
            name="record_evidence",
            description=(
                "Append a verified claim to the evidence ledger. Call this BEFORE including any "
                "factual statement in the final report. The report's Evidence & Confidence table "
                "is built from these records; claims not recorded here will not appear."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "Short factual statement."},
                    "source_url": {"type": "string", "description": "Direct URL to the source."},
                    "source_type": {
                        "type": "string",
                        "description": "e.g. 'government record', 'official bio', 'news article', 'SEC filing', 'FEC contribution'.",
                    },
                    "pub_date": {
                        "type": "string",
                        "description": "Publication or record date (ISO 8601 if known).",
                    },
                    "accessed_at": {
                        "type": "string",
                        "description": "ISO 8601 timestamp of access (defaults to now if omitted).",
                    },
                    "extract": {
                        "type": "string",
                        "description": "Short direct quotation or factual extract supporting the claim.",
                    },
                    "identity_match_rationale": {
                        "type": "string",
                        "description": "Why this source refers to the subject (not just name match).",
                    },
                    "corroboration": {
                        "type": "string",
                        "description": "Independent corroboration, if any. Empty string if none.",
                    },
                    "caveats": {
                        "type": "string",
                        "description": "Contradictions, limitations, outdatedness.",
                    },
                    "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    "notes": {"type": "string"},
                },
                "required": ["claim", "source_url", "confidence"],
                "additionalProperties": False,
            },
            func=record_evidence,
        )

    # ----- prompt assembly -----

    def _load_system_prompt(self) -> str:
        path = Path(__file__).parent / "prompts" / "system.md"
        return path.read_text(encoding="utf-8")

    def _build_user_message(self, request: ResearchRequest) -> str:
        lines = [
            "RESEARCH REQUEST",
            "",
            f"Subject: {request.subject_name}",
        ]
        if request.context:
            lines.append("")
            lines.append("Context:")
            for k, v in request.context.items():
                lines.append(f"- {k}: {v}")
        if request.additional_identifiers:
            lines.append("")
            lines.append("Additional identifiers (use only for verification, not expansion):")
            for k, v in request.additional_identifiers.items():
                lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append(
            f"Operator authorization statement: "
            f"{request.authorization or '(not supplied — scope must remain narrow)'}"
        )
        lines.append("")
        lines.append(
            "Research the subject using the available tools, following the system prompt's "
            "workflow. You may emit SEVERAL tool calls in a single turn — the harness executes "
            "them in parallel. For every factual claim you plan to put in the final report, call "
            "`record_evidence` FIRST. When further search is unlikely to change confidence, stop "
            "calling tools and produce the final narrative (summary + caveats + gaps + identity-"
            "resolution limitations + the required legal footer). The report shell is assembled "
            "automatically from the evidence ledger."
        )
        return "\n".join(lines)

    # ----- output -----

    def _save_outputs(
        self,
        request: ResearchRequest,
        report_md: str,
        ledger: EvidenceLedger,
        audit: AuditLog,
    ) -> tuple[Path, Path]:
        out_dir = Path(self.settings.osint_report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(request.subject_name) or "subject"
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        report_path = out_dir / f"{slug}-{stamp}.md"
        evidence_path = out_dir / f"{slug}-{stamp}-evidence.csv"
        report_path.write_text(report_md, encoding="utf-8")
        write_csv(ledger.records(), evidence_path)
        audit.write_jsonl(out_dir / "audit.jsonl")
        return report_path, evidence_path


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def run_research(
    subject_name: str,
    *,
    context: dict[str, Any] | None = None,
    authorization: str = "",
    additional_identifiers: dict[str, str] | None = None,
) -> ResearchResult:
    """Convenience wrapper: build the default agent and run one request."""
    agent = OSINTAgent()
    return agent.research(
        ResearchRequest(
            subject_name=subject_name,
            context=context or {},
            authorization=authorization,
            additional_identifiers=additional_identifiers or {},
        )
    )
