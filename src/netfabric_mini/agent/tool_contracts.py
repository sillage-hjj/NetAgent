from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from netfabric_mini.normalization.schemas import EvidenceRef


ToolHandler = Callable[[dict[str, Any]], "AgentToolResult"]


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool
    requires_approval: bool
    handler: ToolHandler


class AgentToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    ok: bool
    result: dict[str, Any] | list[Any] | str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    trace_id: str
    read_only: bool
    data_budget: dict[str, Any] | None = None


def make_tool_result(
    *,
    tool_name: str,
    ok: bool,
    trace_id: str,
    read_only: bool = True,
    result: dict[str, Any] | list[Any] | str | None = None,
    evidence: list[EvidenceRef] | list[dict[str, Any]] | None = None,
    errors: list[str] | None = None,
    data_budget: dict[str, Any] | None = None,
) -> AgentToolResult:
    refs = [ref if isinstance(ref, EvidenceRef) else EvidenceRef.model_validate(ref) for ref in (evidence or [])]
    return AgentToolResult(
        tool_name=tool_name,
        ok=ok,
        result=result,
        evidence=refs,
        errors=errors or [],
        trace_id=trace_id,
        read_only=read_only,
        data_budget=data_budget,
    )

