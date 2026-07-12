"""OpenAI Responses API tool loop with bounded calls and structured traces."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from telecom_agent.agent.tools import AgentTools


INSTRUCTIONS = """You are an evidence-grounded assistant for 3GPP TS 24.501 v19.2.0.

Rules:
1. Use tools for every standards claim. Do not answer from model memory.
2. Prefer search_spec for definitions, conditions, procedures, and version-specific behavior.
3. Graph results are structural hints. A graph path is never sufficient evidence by itself.
4. Cite only metadata returned by tools. Never invent section numbers, pages, or quotations.
5. Distinguish TS 24.501 provenance from contextual edges belonging to other specifications.
6. If evidence is insufficient or conflicting, state that explicitly.
7. Keep quotations short and otherwise paraphrase the specification.

Return these headings: Answer, Key evidence, Graph paths (only when useful), Citations,
Evidence limitations. Each citation must include specification, version, section, page when
available, and chunk_id.
"""


class ResponsesClient(Protocol):
    responses: Any


@dataclass(frozen=True)
class ToolTrace:
    round: int
    name: str
    arguments: dict[str, Any]
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round,
            "name": self.name,
            "arguments": self.arguments,
            "ok": self.ok,
        }


@dataclass(frozen=True)
class AgentResult:
    answer: str
    response_id: str
    tool_calls: int
    trace: tuple[ToolTrace, ...]
    cited_chunk_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "response_id": self.response_id,
            "tool_calls": self.tool_calls,
            "trace": [item.to_dict() for item in self.trace],
            "cited_chunk_ids": list(self.cited_chunk_ids),
        }


def _value(item: Any, key: str, default: Any = None) -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


class OpenAIResponsesAgent:
    def __init__(
        self,
        client: ResponsesClient,
        model: str,
        tools: AgentTools,
        *,
        max_tool_calls: int = 6,
    ) -> None:
        if not model:
            raise ValueError("A model name is required")
        if not 1 <= max_tool_calls <= 12:
            raise ValueError("max_tool_calls must be between 1 and 12")
        self.client = client
        self.model = model
        self.tools = tools
        self.max_tool_calls = max_tool_calls

    def ask(self, question: str) -> AgentResult:
        if not question.strip():
            raise ValueError("Question must not be empty")
        response = self.client.responses.create(
            model=self.model,
            instructions=INSTRUCTIONS,
            input=question,
            tools=self.tools.schemas,
        )
        trace: list[ToolTrace] = []
        observed_chunk_ids: set[str] = set()
        total_calls = 0
        round_number = 0

        while True:
            calls = [
                item for item in _value(response, "output", []) if _value(item, "type") == "function_call"
            ]
            if not calls:
                answer = _value(response, "output_text", "")
                if not answer:
                    raise RuntimeError("The model returned neither tool calls nor final text")
                cited_chunk_ids = _cited_chunk_ids(answer)
                unsupported = set(cited_chunk_ids) - observed_chunk_ids
                if unsupported:
                    raise RuntimeError(
                        "The model cited chunk IDs that were not returned by tools: "
                        + ", ".join(sorted(unsupported))
                    )
                return AgentResult(
                    answer=answer,
                    response_id=_value(response, "id", ""),
                    tool_calls=total_calls,
                    trace=tuple(trace),
                    cited_chunk_ids=cited_chunk_ids,
                )
            if total_calls + len(calls) > self.max_tool_calls:
                raise RuntimeError(
                    f"Agent exceeded the maximum of {self.max_tool_calls} tool calls"
                )

            round_number += 1
            tool_outputs = []
            for call in calls:
                name = _value(call, "name", "")
                raw_arguments = _value(call, "arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("tool arguments must be an object")
                    result = self.tools.call(name, arguments)
                    observed_chunk_ids.update(_find_chunk_ids(result))
                except (json.JSONDecodeError, ValueError) as error:
                    arguments = {}
                    result = {"ok": False, "error": f"Invalid tool arguments: {error}"}
                total_calls += 1
                trace.append(ToolTrace(round_number, name, arguments, bool(result.get("ok"))))
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": _value(call, "call_id", ""),
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
            try:
                response = self.client.responses.create(
                    model=self.model,
                    instructions=INSTRUCTIONS,
                    previous_response_id=_value(response, "id", ""),
                    input=tool_outputs,
                    tools=self.tools.schemas,
                )
            except Exception as error:
                if not _is_stateful_reference_error(error):
                    raise
                response = self.client.responses.create(
                    model=self.model,
                    instructions=INSTRUCTIONS,
                    input=[_minimal_function_call(call) for call in calls] + tool_outputs,
                    tools=self.tools.schemas,
                )


def _find_chunk_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "chunk_id" and isinstance(child, str):
                found.add(child)
            else:
                found.update(_find_chunk_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_chunk_ids(child))
    return found


def _minimal_function_call(call: Any) -> dict[str, Any]:
    return {
        "type": "function_call",
        "name": _value(call, "name", ""),
        "arguments": _value(call, "arguments", "{}"),
        "call_id": _value(call, "call_id", ""),
    }


def _is_stateful_reference_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "different azure openai resource" in message
        or "created under a different" in message
    )


def _cited_chunk_ids(answer: str) -> tuple[str, ...]:
    values = re.findall(
        r"chunk_id\s*(?:[:=]\s*)?(?:[`*_]+)?([A-Za-z0-9._-]+)",
        answer,
        flags=re.IGNORECASE,
    )
    return tuple(dict.fromkeys(values))
