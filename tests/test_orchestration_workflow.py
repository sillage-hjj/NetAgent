import inspect
import json

from netagent_lab.db import init_sim_db, initialize_runtime_state
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.orchestration.investigation_context import build_investigation_context
from netagent_lab.orchestration.monitoring_workflow import run_monitoring_cycle
from netagent_lab.sim.engine import SimulationEngine
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_monitoring_workflow_runs_end_to_end_and_persists_normalized_state() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})

    result = run_monitoring_cycle(conn)
    kb = KnowledgeBase.from_db(conn)

    assert result.normalized_state_id is not None
    assert kb.get_normalized_state(result.normalized_state_id) is not None
    assert result.snapshot_id
    assert any(alert["alert_type"] == "high_packet_loss" for alert in result.alerts)
    assert result.reasoning_results["reachability_matrix"]


def test_monitoring_workflow_has_no_llm_or_external_api_imports() -> None:
    import netagent_lab.orchestration.monitoring_workflow as workflow

    source = inspect.getsource(workflow).lower()

    assert "openai" not in source
    assert "langchain" not in source
    assert "requests" not in source
    assert "httpx" not in source


def test_investigation_context_is_json_serializable_budgeted_and_evidence_grounded() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})
    run_monitoring_cycle(conn)

    context = build_investigation_context(conn, budget={"max_events": 1, "max_telemetry_samples": 2})

    json.dumps(context)
    assert context["budget"]["max_events"] == 1
    assert len(context["recent_events"]) == 1
    assert len(context["recent_telemetry"]) == 2
    assert context["evidence_refs"]
    assert "prompt" not in context


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

