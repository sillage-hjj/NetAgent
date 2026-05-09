from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from netfabric_mini.agent.tool_contracts import AgentToolResult, make_tool_result
from netfabric_mini.agent.tool_registry import ToolRegistry
from netfabric_mini.controls.data_budget import apply_context_budget
from netfabric_mini.controls.redaction import redact_sensitive_fields
from netfabric_mini.llm.client_protocol import LLMToolCall


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(self, tool_call: LLMToolCall) -> AgentToolResult:
        tool = self.registry.get_tool(tool_call.name)
        trace_id = f"trace-{tool_call.id}"
        if tool is None:
            return _error(tool_call.name, trace_id, f"Unknown tool: {tool_call.name}")
        validation_errors = _validate_arguments(tool_call.arguments, tool.input_schema)
        if validation_errors:
            return _error(tool.name, trace_id, "; ".join(validation_errors), read_only=tool.read_only)
        if tool.requires_approval and not tool_call.arguments.get("approval_id"):
            return _error(tool.name, trace_id, "Tool requires explicit approval and cannot run directly.", read_only=tool.read_only)
        try:
            result = tool.handler(tool_call.arguments)
        except Exception as exc:
            return _error(tool.name, trace_id, str(exc), read_only=tool.read_only)
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        redacted_payload = redact_sensitive_fields(payload)
        budgeted = _budget_tool_payload(redacted_payload)
        return AgentToolResult.model_validate(budgeted)


def _validate_arguments(arguments: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = schema.get("required") or []
    for key in required:
        if key not in arguments:
            errors.append(f"Missing required argument: {key}")
    allowed = set((schema.get("properties") or {}).keys())
    for key in arguments:
        if key not in allowed:
            errors.append(f"Unexpected argument: {key}")
    return errors


def _budget_tool_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if isinstance(result, dict):
        payload["result"] = apply_context_budget(result, payload.get("data_budget"))
    return payload


def _error(tool_name: str, trace_id: str, message: str, *, read_only: bool = True) -> AgentToolResult:
    return make_tool_result(
        tool_name=tool_name,
        ok=False,
        trace_id=trace_id,
        read_only=read_only,
        errors=[message],
    )


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
