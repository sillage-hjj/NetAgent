from __future__ import annotations

from netagent_lab.agent.tool_executor import ToolExecutor
from netagent_lab.agent.approvals import approve_request, create_approval_request
from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.db import init_sim_db, initialize_runtime_state
from netagent_lab.llm.client_protocol import LLMToolCall
from netagent_lab.llm.config import LLMProviderConfig
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def _conn():
    conn = init_sim_db(":memory:")
    initialize_runtime_state(conn, load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml"))
    return conn


def test_executor_runs_valid_tool() -> None:
    conn = _conn()
    executor = ToolExecutor(build_default_tool_registry(conn, LLMProviderConfig(provider="mock")))

    result = executor.execute(LLMToolCall(id="tc-1", name="infer_path", arguments={"src_device": "client_zurich", "dst_device": "app_b"}))

    assert result.ok is True
    assert result.result["reachable"] is True
    assert result.evidence
    assert result.trace_id


def test_executor_unknown_tool_fails_safely() -> None:
    conn = _conn()
    executor = ToolExecutor(build_default_tool_registry(conn, LLMProviderConfig(provider="mock")))

    result = executor.execute(LLMToolCall(id="tc-1", name="shell", arguments={}))

    assert result.ok is False
    assert "Unknown tool" in result.errors[0]


def test_executor_invalid_arguments_fail_safely() -> None:
    conn = _conn()
    executor = ToolExecutor(build_default_tool_registry(conn, LLMProviderConfig(provider="mock")))

    result = executor.execute(LLMToolCall(id="tc-1", name="infer_path", arguments={"src_device": "client_zurich"}))

    assert result.ok is False
    assert "Missing required argument" in result.errors[0]


def test_executor_blocks_approval_required_tool() -> None:
    conn = _conn()
    config = LLMProviderConfig(provider="mock", allow_sim_mutation=True)
    executor = ToolExecutor(build_default_tool_registry(conn, config))

    result = executor.execute(LLMToolCall(id="tc-1", name="apply_approved_sim_event", arguments={}))

    assert result.ok is False
    assert "approval_id" in result.errors[0]


def test_executor_allows_approved_simulated_mutation_only() -> None:
    conn = _conn()
    config = LLMProviderConfig(provider="mock", allow_sim_mutation=True)
    approval = create_approval_request(
        conn,
        run_id="run-test",
        tool_name="apply_approved_sim_event",
        arguments={"event_type": "link_down", "target": "link_r1_r2", "params": {"reason": "test"}},
    )
    approve_request(conn, approval.approval_id)
    executor = ToolExecutor(build_default_tool_registry(conn, config))

    result = executor.execute(
        LLMToolCall(id="tc-2", name="apply_approved_sim_event", arguments={"approval_id": approval.approval_id})
    )

    assert result.ok is True
    assert result.read_only is False
    assert result.evidence[0].type == "event"
