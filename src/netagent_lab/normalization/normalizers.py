from __future__ import annotations

from typing import Any

from netagent_lab.ingestion.collector_contracts import CollectorResult
from netagent_lab.normalization.schemas import (
    EvidenceRef,
    NormalizedInventory,
    NormalizedNetworkState,
    NormalizedObservation,
)


REQUIRED_LINK_METADATA = {
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


def normalize_inventory(collector_result: CollectorResult) -> NormalizedInventory:
    _ensure_ok(collector_result)
    result = _expect_dict(collector_result)
    interfaces: dict[str, Any] = {}
    devices = {device["id"]: device for device in result.get("devices", [])}
    for device in result.get("devices", []):
        for interface in device.get("interfaces", []):
            interfaces[f"{device['id']}:{interface['id']}"] = interface
    return NormalizedInventory(
        devices=devices,
        interfaces=interfaces,
        links={link["id"]: link for link in result.get("links", [])},
        services={service["id"]: service for service in result.get("services", [])},
        probes={probe["id"]: probe for probe in result.get("probes", [])},
    )


def normalize_device_states(collector_result: CollectorResult) -> list[NormalizedObservation]:
    return _normalize_mapping(collector_result, "device")


def normalize_interface_states(collector_result: CollectorResult) -> list[NormalizedObservation]:
    return _normalize_mapping(collector_result, "interface")


def normalize_link_states(collector_result: CollectorResult) -> list[NormalizedObservation]:
    result = _expect_dict(collector_result)
    for link_id, attributes in result.items():
        missing = sorted(REQUIRED_LINK_METADATA - set(attributes))
        if missing:
            raise ValueError(f"Link {link_id} missing required metadata: {', '.join(missing)}")
    return _normalize_mapping(collector_result, "link")


def normalize_service_states(collector_result: CollectorResult) -> list[NormalizedObservation]:
    return _normalize_mapping(collector_result, "service")


def normalize_probe_results(collector_result: CollectorResult) -> list[NormalizedObservation]:
    return _normalize_mapping(collector_result, "probe")


def normalize_events(collector_result: CollectorResult) -> list[NormalizedObservation]:
    return _normalize_sequence(collector_result, "event")


def normalize_telemetry(collector_result: CollectorResult) -> list[NormalizedObservation]:
    return _normalize_sequence(collector_result, "telemetry")


def normalize_all(collector_results: list[CollectorResult]) -> NormalizedNetworkState:
    inventory = NormalizedInventory()
    observations: list[NormalizedObservation] = []
    evidence: list[EvidenceRef] = []
    tick = 0
    for collector_result in collector_results:
        tick = max(tick, collector_result.tick)
        evidence.extend(collector_result.evidence)
        if collector_result.collector == "collect_sim_inventory":
            inventory = normalize_inventory(collector_result)
        elif collector_result.collector == "collect_sim_device_states":
            observations.extend(normalize_device_states(collector_result))
        elif collector_result.collector == "collect_sim_interface_states":
            observations.extend(normalize_interface_states(collector_result))
        elif collector_result.collector == "collect_sim_link_states":
            observations.extend(normalize_link_states(collector_result))
        elif collector_result.collector == "collect_sim_service_states":
            observations.extend(normalize_service_states(collector_result))
        elif collector_result.collector == "collect_sim_probe_results":
            observations.extend(normalize_probe_results(collector_result))
        elif collector_result.collector == "collect_sim_recent_events":
            observations.extend(normalize_events(collector_result))
        elif collector_result.collector == "collect_sim_recent_telemetry":
            observations.extend(normalize_telemetry(collector_result))
    return NormalizedNetworkState(
        id=f"normalized-state-{tick}",
        tick=tick,
        inventory=inventory,
        observations=observations,
        evidence=_unique_evidence(evidence),
    )


def _normalize_mapping(collector_result: CollectorResult, object_type: str) -> list[NormalizedObservation]:
    _ensure_ok(collector_result)
    result = _expect_dict(collector_result)
    return [
        NormalizedObservation(
            id=f"obs-{collector_result.tick}-{object_type}-{object_id}",
            source=collector_result.collector,
            observed_at_tick=collector_result.tick,
            object_type=object_type,
            object_id=object_id,
            attributes=attributes,
            evidence=_evidence_for_object(collector_result, object_type, object_id),
        )
        for object_id, attributes in result.items()
    ]


def _normalize_sequence(collector_result: CollectorResult, object_type: str) -> list[NormalizedObservation]:
    _ensure_ok(collector_result)
    if not isinstance(collector_result.result, list):
        raise ValueError(f"{collector_result.collector} result must be a list")
    observations: list[NormalizedObservation] = []
    for item in collector_result.result:
        object_id = str(item.get("id"))
        observations.append(
            NormalizedObservation(
                id=f"obs-{collector_result.tick}-{object_type}-{object_id}",
                source=collector_result.collector,
                observed_at_tick=collector_result.tick,
                object_type=object_type,
                object_id=object_id,
                attributes=item,
                evidence=_evidence_for_object(collector_result, object_type, object_id),
            )
        )
    return observations


def _evidence_for_object(
    collector_result: CollectorResult,
    object_type: str,
    object_id: str,
) -> list[EvidenceRef]:
    matches = [
        evidence
        for evidence in collector_result.evidence
        if evidence.id == object_id or evidence.type == object_type
    ]
    return matches or list(collector_result.evidence)


def _ensure_ok(collector_result: CollectorResult) -> None:
    if not collector_result.ok:
        raise ValueError(f"Collector failed: {collector_result.collector}: {collector_result.errors}")


def _expect_dict(collector_result: CollectorResult) -> dict[str, Any]:
    if not isinstance(collector_result.result, dict):
        raise ValueError(f"{collector_result.collector} result must be a dict")
    return collector_result.result


def _unique_evidence(evidence: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[tuple[str, str]] = set()
    unique: list[EvidenceRef] = []
    for item in evidence:
        key = (item.type, item.id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

