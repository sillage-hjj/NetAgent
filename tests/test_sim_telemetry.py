import json

from netfabric_mini.db import (
    init_sim_db,
    initialize_runtime_state,
    insert_telemetry_sample,
    list_telemetry_samples,
)
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.state import SimulationStateStore
from netfabric_mini.sim.telemetry import generate_all_telemetry
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_telemetry_samples_cover_all_domains_and_are_json_serializable() -> None:
    conn = _conn()
    state = SimulationStateStore.load(conn)

    samples = generate_all_telemetry(state, state.current_tick)

    target_types = {sample.target_type for sample in samples}
    assert {"device", "interface", "link", "service", "probe"} <= target_types
    json.dumps([sample.model_dump(mode="json") for sample in samples])


def test_link_metadata_contains_required_fields() -> None:
    conn = _conn()
    state = SimulationStateStore.load(conn)

    metadata = state.link_metadata("link_r1_r2")

    required = {
        "link_id",
        "endpoint_a",
        "endpoint_b",
        "admin_state",
        "oper_state",
        "effective_state",
        "bandwidth_mbps",
        "latency_ms",
        "jitter_ms",
        "loss_percent",
        "utilization_percent",
        "error_rate_percent",
        "flap_count",
        "last_change_tick",
        "last_event_id",
        "failure_reason",
        "tags",
    }
    assert required <= set(metadata)


def test_high_loss_and_utilization_appear_in_telemetry_and_persist() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)
    engine.inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})
    engine.inject_event("set_link_utilization", "link_r1_r2", {"utilization_percent": 92})
    state = SimulationStateStore.load(conn)

    samples = generate_all_telemetry(state, state.current_tick)
    for sample in samples:
        insert_telemetry_sample(conn, sample)
    conn.commit()
    persisted = list_telemetry_samples(conn)

    assert any(sample["metric"] == "link_loss_percent" and sample["value"] == 9 for sample in persisted)
    assert any(sample["metric"] == "link_utilization_percent" and sample["value"] == 92 for sample in persisted)


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

