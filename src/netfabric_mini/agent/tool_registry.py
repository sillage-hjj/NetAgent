from __future__ import annotations

import sqlite3
from typing import Any, Callable

from netfabric_mini.agent.tool_contracts import AgentTool
from netfabric_mini.agent_tools import context_tools, knowledge_tools, monitoring_tools, reasoning_tools, simulation_tools, snapshot_tools
from netfabric_mini.llm.client_protocol import LLMToolSpec
from netfabric_mini.llm.config import LLMProviderConfig


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> list[AgentTool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def to_llm_tool_specs(self) -> list[LLMToolSpec]:
        return [
            LLMToolSpec(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.input_schema,
                read_only=tool.read_only,
                requires_approval=tool.requires_approval,
            )
            for tool in self.list_tools()
        ]


def build_default_tool_registry(conn: sqlite3.Connection, config: LLMProviderConfig) -> ToolRegistry:
    registry = ToolRegistry()

    def bind(fn: Callable[[sqlite3.Connection, dict[str, Any]], Any]):
        return lambda args: fn(conn, args)

    _register(registry, "get_current_context", "Build a budgeted, redacted investigation context.", _schema({"focus": "object", "budget": "object"}), bind(context_tools.get_current_context))
    _register(registry, "run_monitoring_cycle", "Run one read-only monitoring workflow cycle.", _schema({"focus": "object"}), bind(monitoring_tools.run_monitoring_cycle))
    _register(registry, "get_active_alerts", "Evaluate deterministic active alerts.", _schema({"severity": "string"}), bind(monitoring_tools.get_active_alerts))
    _register(registry, "collect_link_states", "Collect current link metadata and runtime state.", _schema({"link_ids": "array"}), bind(knowledge_tools.collect_link_states))
    _register(registry, "collect_device_states", "Collect current device runtime state.", _schema({"device_ids": "array"}), bind(knowledge_tools.collect_device_states))
    _register(registry, "collect_service_states", "Collect current service state.", _schema({"service_ids": "array"}), bind(knowledge_tools.collect_service_states))
    _register(registry, "get_recent_events", "Fetch recent simulated events from the knowledge base.", _schema({"since_tick": "integer", "target_id": "string", "event_type": "string"}), bind(knowledge_tools.get_recent_events))
    _register(registry, "get_recent_telemetry", "Fetch recent telemetry samples from the knowledge base.", _schema({"since_tick": "integer", "target_id": "string", "metric": "string"}), bind(knowledge_tools.get_recent_telemetry))
    _register(registry, "infer_path", "Run deterministic path inference between devices.", _schema({"src_device": "string", "dst_device": "string"}, ["src_device", "dst_device"]), bind(reasoning_tools.infer_path))
    _register(registry, "check_service_reachability", "Run deterministic source-to-service reachability.", _schema({"source_device": "string", "service_id": "string"}, ["source_device", "service_id"]), bind(reasoning_tools.check_service_reachability))
    _register(registry, "get_reachability_matrix", "Collect deterministic probe and service reachability matrix.", _schema({"include_all_sources": "boolean"}), bind(reasoning_tools.get_reachability_matrix))
    _register(registry, "evaluate_link_health", "Evaluate deterministic health for a link.", _schema({"link_id": "string"}, ["link_id"]), bind(reasoning_tools.evaluate_link_health))
    _register(registry, "evaluate_device_health", "Evaluate deterministic health for a device.", _schema({"device_id": "string"}, ["device_id"]), bind(reasoning_tools.evaluate_device_health))
    _register(registry, "evaluate_service_health", "Evaluate deterministic health for a service.", _schema({"service_id": "string"}, ["service_id"]), bind(reasoning_tools.evaluate_service_health))
    _register(registry, "evaluate_alerts", "Evaluate deterministic alerts.", _schema({}), bind(reasoning_tools.evaluate_alerts))
    _register(registry, "get_latest_snapshot", "Fetch latest monitoring snapshot.", _schema({}), bind(knowledge_tools.get_latest_snapshot))
    _register(registry, "get_snapshot", "Fetch a snapshot by id or alias.", _schema({"snapshot_id_or_alias": "string"}, ["snapshot_id_or_alias"]), bind(knowledge_tools.get_snapshot))
    _register(registry, "diff_snapshots", "Diff two snapshots by id or alias.", _schema({"from_snapshot": "string", "to_snapshot": "string"}, ["from_snapshot", "to_snapshot"]), bind(reasoning_tools.diff_snapshots))
    _register(registry, "export_llm_context", "Export future-agent context with budget and redaction.", _schema({"focus": "object", "budget": "object"}), bind(context_tools.export_llm_context))
    _register(registry, "list_snapshots", "List saved monitoring snapshots.", _schema({}), bind(snapshot_tools.list_snapshots))
    _register(registry, "diff_latest_snapshots", "Diff latest two snapshots.", _schema({}), bind(snapshot_tools.diff_latest_snapshots))

    if config.allow_sim_mutation:
        _register(
            registry,
            "propose_sim_event",
            "Create an approval request for a simulated mutation. Does not mutate state.",
            _schema({"event_type": "string", "target": "string", "params": "object"}, ["event_type", "target"]),
            bind(lambda c, a: simulation_tools.propose_sim_event(c, a)),
            requires_approval=False,
        )
        _register(
            registry,
            "apply_approved_sim_event",
            "Apply a previously approved simulated event. Never touches real devices.",
            _schema({"approval_id": "string"}, ["approval_id"]),
            bind(simulation_tools.apply_approved_sim_event),
            read_only=False,
            requires_approval=True,
        )
    return registry


def _register(
    registry: ToolRegistry,
    name: str,
    description: str,
    schema: dict[str, Any],
    handler,
    *,
    read_only: bool = True,
    requires_approval: bool = False,
) -> None:
    registry.register(
        AgentTool(
            name=name,
            description=description,
            input_schema=schema,
            read_only=read_only,
            requires_approval=requires_approval,
            handler=handler,
        )
    )


def _schema(properties: dict[str, str], required: list[str] | None = None) -> dict[str, Any]:
    schema_properties: dict[str, Any] = {}
    for key, value in properties.items():
        entry: dict[str, Any] = {"type": value}
        if value == "array":
            entry["items"] = {"type": "string"}
        schema_properties[key] = entry
    return {
        "type": "object",
        "properties": schema_properties,
        "required": required or [],
        "additionalProperties": False,
    }
