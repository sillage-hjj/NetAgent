from __future__ import annotations

from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.db import init_sim_db
from netagent_lab.llm.config import LLMProviderConfig


def test_registry_includes_read_only_tools_and_unique_names() -> None:
    conn = init_sim_db(":memory:")
    registry = build_default_tool_registry(conn, LLMProviderConfig(provider="mock"))
    names = [tool.name for tool in registry.list_tools()]

    assert "get_current_context" in names
    assert "run_monitoring_cycle" in names
    assert "infer_path" in names
    assert len(names) == len(set(names))
    assert all(tool.description for tool in registry.list_tools())
    assert all(tool.read_only for tool in registry.list_tools())
    assert "apply_approved_sim_event" not in names


def test_mutation_tools_are_approval_gated_when_enabled() -> None:
    conn = init_sim_db(":memory:")
    config = LLMProviderConfig(provider="mock", allow_sim_mutation=True)
    registry = build_default_tool_registry(conn, config)

    apply_tool = registry.get_tool("apply_approved_sim_event")

    assert apply_tool is not None
    assert apply_tool.requires_approval is True
    assert apply_tool.read_only is False


def test_tool_specs_are_json_schema_like() -> None:
    conn = init_sim_db(":memory:")
    registry = build_default_tool_registry(conn, LLMProviderConfig(provider="mock"))

    specs = registry.to_llm_tool_specs()

    assert specs
    assert all(spec.parameters_json_schema["type"] == "object" for spec in specs)

