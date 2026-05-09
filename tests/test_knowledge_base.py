from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.ingestion.simulated_collectors import collect_sim_all
from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.normalization.normalizers import normalize_all
from netfabric_mini.normalization.schemas import EvidenceRef
from netfabric_mini.monitoring.monitor import run_monitor_once
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_knowledge_base_loads_topology_and_current_link_state() -> None:
    conn = _conn()
    kb = KnowledgeBase.from_db(conn)

    assert kb.get_topology().name == "simple_branch_app"
    assert kb.get_link("link_r1_r2")["effective_state"] == "up"


def test_knowledge_base_stores_and_retrieves_normalized_observations() -> None:
    conn = _conn()
    kb = KnowledgeBase.from_db(conn)
    normalized = normalize_all(collect_sim_all(conn))

    state_id = kb.save_normalized_state(normalized)

    assert kb.get_normalized_state(state_id)["id"] == state_id
    observations = kb.get_observations("link", "link_r1_r2")
    assert observations
    assert observations[-1]["object_id"] == "link_r1_r2"


def test_knowledge_base_snapshot_aliases_work() -> None:
    conn = _conn()
    run_monitor_once(conn)
    run_monitor_once(conn)
    kb = KnowledgeBase.from_db(conn)

    assert kb.get_snapshot("latest")["id"].endswith("0002")
    assert kb.get_snapshot("latest-1")["id"].endswith("0001")


def test_knowledge_base_evidence_lookup() -> None:
    conn = _conn()
    event = SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})
    run_monitor_once(conn)
    kb = KnowledgeBase.from_db(conn)
    telemetry_id = kb.get_recent_telemetry()[0]["id"]
    snapshot_id = kb.get_snapshot("latest")["id"]

    assert kb.get_evidence(EvidenceRef(type="event", id=event.id))["id"] == event.id
    assert kb.get_evidence(EvidenceRef(type="telemetry", id=telemetry_id))["id"] == telemetry_id
    assert kb.get_evidence(EvidenceRef(type="link", id="link_r1_r2"))["link_id"] == "link_r1_r2"
    assert kb.get_evidence(EvidenceRef(type="service", id="app_b"))["topology"]["id"] == "app_b"
    assert kb.get_evidence(EvidenceRef(type="snapshot", id=snapshot_id))["id"] == snapshot_id


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

