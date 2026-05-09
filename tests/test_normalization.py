import json

import pytest

from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.ingestion.collector_contracts import CollectorResult
from netfabric_mini.ingestion.simulated_collectors import collect_sim_all, collect_sim_link_states
from netfabric_mini.normalization.normalizers import normalize_all, normalize_link_states
from netfabric_mini.normalization.schemas import EvidenceRef
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_collector_outputs_normalize_successfully() -> None:
    conn = _conn()

    normalized = normalize_all(collect_sim_all(conn))

    assert normalized.tick == 0
    assert "r1" in normalized.inventory.devices
    assert any(observation.object_type == "link" for observation in normalized.observations)
    json.dumps(normalized.model_dump(mode="json"))


def test_missing_link_metadata_fails_validation() -> None:
    conn = _conn()
    result = collect_sim_link_states(conn)
    broken = dict(result.result)
    broken["link_r1_r2"] = dict(broken["link_r1_r2"])
    broken["link_r1_r2"].pop("endpoint_a")
    broken_result = CollectorResult(
        collector=result.collector,
        source=result.source,
        ok=True,
        tick=result.tick,
        result=broken,
        evidence=result.evidence,
        errors=[],
    )

    with pytest.raises(ValueError, match="missing required metadata"):
        normalize_link_states(broken_result)


def test_evidence_survives_normalization() -> None:
    conn = _conn()

    observations = normalize_link_states(collect_sim_link_states(conn))

    link_observation = next(item for item in observations if item.object_id == "link_r1_r2")
    assert any(ref.id == "link_r1_r2" for ref in link_observation.evidence)


def test_normalized_schema_rejects_extra_fields() -> None:
    with pytest.raises(ValueError):
        EvidenceRef(type="x", id="y", surprise=True)


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

