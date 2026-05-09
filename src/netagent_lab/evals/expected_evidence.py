from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExpectedEvidenceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    root_cause_type: str
    required_evidence_types: list[str]
    preferred_object_ids: list[str]
    negative_evidence_types: list[str] = Field(default_factory=list)
    max_irrelevant_refs: int = 2


EXPECTED_EVIDENCE_SPECS = {
    "link_failure": ExpectedEvidenceSpec(
        scenario_name="link_failure",
        root_cause_type="link_down",
        required_evidence_types=["event", "link", "alert", "path_result", "probe", "snapshot_diff"],
        preferred_object_ids=["link_r1_r2", "event-0-0001", "probe_zurich_app_b_https"],
        negative_evidence_types=[],
    ),
    "congestion": ExpectedEvidenceSpec(
        scenario_name="congestion",
        root_cause_type="performance_degradation",
        required_evidence_types=["telemetry", "alert", "probe", "path_result", "link", "event"],
        preferred_object_ids=["link_r1_r2", "probe_zurich_app_b_https", "event-0-0001", "event-0-0002", "event-0-0003"],
        negative_evidence_types=[],
    ),
    "route_withdrawal": ExpectedEvidenceSpec(
        scenario_name="route_withdrawal",
        root_cause_type="route_withdrawal",
        required_evidence_types=["event", "route_block", "probe", "path_result", "link", "snapshot_diff"],
        preferred_object_ids=["routeblock-1", "event-0-0001", "app_b", "probe_zurich_app_b_https"],
        negative_evidence_types=["link_down"],
    ),
    "acl_block": ExpectedEvidenceSpec(
        scenario_name="acl_block",
        root_cause_type="acl_block",
        required_evidence_types=["acl_rule", "event", "path_result", "ticket"],
        preferred_object_ids=["ACL-DENY-ZRH-APPB-HTTPS", "T-001", "path-client_zurich-to-app_b"],
        negative_evidence_types=[],
    ),
}


def get_expected_evidence_spec(scenario_name: str) -> ExpectedEvidenceSpec | None:
    return EXPECTED_EVIDENCE_SPECS.get(scenario_name)

