from __future__ import annotations

from typing import Any
from uuid import uuid4

from netfabric_mini.agent.tool_contracts import AgentToolResult, make_tool_result
from netfabric_mini.normalization.schemas import EvidenceRef


def trace_id() -> str:
    return f"trace-{uuid4().hex[:12]}"


def evidence_from_payload(payload: Any, fallback: list[dict[str, Any]] | None = None) -> list[EvidenceRef]:
    refs = _collect_explicit_evidence(payload)
    if not refs and fallback:
        refs = [EvidenceRef.model_validate(ref) for ref in fallback]
    return refs


def _collect_explicit_evidence(payload: Any) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            evidence = value.get("evidence")
            if isinstance(evidence, list):
                for ref in evidence:
                    if isinstance(ref, dict) and {"type", "id"} <= set(ref):
                        refs.append(EvidenceRef.model_validate(ref))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    seen: set[tuple[str, str]] = set()
    unique: list[EvidenceRef] = []
    for ref in refs:
        key = (ref.type, ref.id)
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


def ok_result(
    tool_name: str,
    payload: Any,
    *,
    read_only: bool = True,
    fallback_evidence: list[dict[str, Any]] | None = None,
    data_budget: dict[str, Any] | None = None,
) -> AgentToolResult:
    return make_tool_result(
        tool_name=tool_name,
        ok=True,
        trace_id=trace_id(),
        read_only=read_only,
        result=payload,
        evidence=evidence_from_payload(payload, fallback_evidence),
        data_budget=data_budget,
    )


def error_result(tool_name: str, message: str, *, read_only: bool = True) -> AgentToolResult:
    return make_tool_result(
        tool_name=tool_name,
        ok=False,
        trace_id=trace_id(),
        read_only=read_only,
        errors=[message],
    )
