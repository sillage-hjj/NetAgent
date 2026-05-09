from netfabric_mini.controls.data_budget import apply_context_budget
from netfabric_mini.controls.evidence import collect_evidence_refs, validate_evidence_refs
from netfabric_mini.controls.guardrails import (
    classify_sim_action,
    enforce_no_external_network_access_config,
    validate_collector_is_read_only,
)
from netfabric_mini.controls.redaction import redact_sensitive_fields


def test_data_budget_truncates_events_telemetry_alerts_and_links() -> None:
    context = {
        "recent_events": [{"id": str(i)} for i in range(3)],
        "recent_telemetry": [{"id": str(i)} for i in range(4)],
        "active_alerts": [{"id": str(i)} for i in range(3)],
        "link_state_metadata": {str(i): {} for i in range(4)},
        "raw_payload": {"large": True},
    }

    result = apply_context_budget(
        context,
        {"max_events": 1, "max_telemetry_samples": 2, "max_alerts": 1, "max_links": 2},
    )

    assert len(result["recent_events"]) == 1
    assert len(result["recent_telemetry"]) == 2
    assert len(result["active_alerts"]) == 1
    assert len(result["link_state_metadata"]) == 2
    assert "raw_payload" not in result


def test_redaction_removes_sensitive_fields() -> None:
    result = redact_sensitive_fields(
        {
            "management_ip": "192.0.2.1",
            "nested": {"password": "secret", "community_string": "public", "safe": "ok"},
        }
    )

    assert "management_ip" not in result
    assert "password" not in result["nested"]
    assert "community_string" not in result["nested"]
    assert result["nested"]["safe"] == "ok"


def test_evidence_validation() -> None:
    good = {"alerts": [{"evidence": [{"type": "link", "id": "l1"}]}]}
    bad = {"alerts": [{"evidence": []}]}

    assert collect_evidence_refs(good)[0].id == "l1"
    assert validate_evidence_refs(good) is True
    assert validate_evidence_refs(bad) is False


def test_guardrails_classify_actions() -> None:
    assert enforce_no_external_network_access_config()["ok"] is True
    assert validate_collector_is_read_only("collect_sim_links")["ok"] is True
    assert validate_collector_is_read_only("inject_link_down")["ok"] is False
    assert classify_sim_action("ssh to r1")["classification"] == "forbidden_for_mvp"
    assert classify_sim_action("link_down link_r1_r2")["classification"] == "simulated_mutation_only"

