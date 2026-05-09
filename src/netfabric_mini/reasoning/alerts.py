from __future__ import annotations

from typing import Any

from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.reasoning.reachability import collect_reachability_matrix


def evaluate_alerts(kb: KnowledgeBase) -> list[dict[str, Any]]:
    state = kb.get_current_state()
    alerts: list[dict[str, Any]] = []
    tick = kb.get_current_tick()
    for device in state.list_devices():
        if not state.effective_device_up(device.device_id):
            alerts.append(_alert(tick, "critical", "device_down", "device", device.device_id, device.last_event_id))
        if device.cpu_utilization_percent > 85:
            alerts.append(_alert(tick, "warning", "high_cpu", "device", device.device_id, device.last_event_id))
        if device.memory_utilization_percent > 90:
            alerts.append(_alert(tick, "warning", "high_memory", "device", device.device_id, device.last_event_id))
    for service in state.list_services():
        topology_service = state.get_topology_service(service.service_id)
        if service.status == "down":
            severity = "critical" if topology_service.criticality == "critical" else "warning"
            alerts.append(_alert(tick, severity, "service_down", "service", service.service_id, service.last_event_id))
    for link_id in state.links:
        link = state.link_metadata(link_id)
        critical = "critical" in link["tags"]
        if link["effective_state"] == "down":
            alerts.append(_alert(tick, "critical" if critical else "warning", "link_down", "link", link_id, link.get("last_event_id")))
        if link["latency_ms"] > 100:
            alerts.append(_alert(tick, "warning", "high_latency", "link", link_id, link.get("last_event_id")))
        if link["loss_percent"] > 5:
            alerts.append(_alert(tick, "warning", "high_packet_loss", "link", link_id, link.get("last_event_id")))
        if link["utilization_percent"] > 85:
            alerts.append(_alert(tick, "warning", "high_utilization", "link", link_id, link.get("last_event_id")))
        if link["error_rate_percent"] > 5:
            alerts.append(_alert(tick, "warning", "high_error_rate", "link", link_id, link.get("last_event_id")))
        if link["flap_count"] >= 3:
            alerts.append(_alert(tick, "warning", "repeated_flaps", "link", link_id, link.get("last_event_id")))
    reachability = collect_reachability_matrix(kb)
    for probe_id, result in reachability["probes"].items():
        service_id = result.get("target_service")
        service = state.get_topology_service(service_id) if service_id else None
        if not result.get("reachable", False):
            severity = "critical" if service and service.criticality == "critical" else "warning"
            alerts.append(_alert(tick, severity, "probe_unreachable", "probe", probe_id, None))
        elif result.get("degraded", False):
            alerts.append(_alert(tick, "warning", "probe_degraded", "probe", probe_id, None))
    for index, alert in enumerate(alerts, start=1):
        alert["id"] = f"alert-{tick}-{index:04d}"
    return alerts


def _alert(
    tick: int,
    severity: str,
    alert_type: str,
    target_type: str,
    target_id: str,
    event_id: str | None,
) -> dict[str, Any]:
    evidence = [{"type": target_type, "id": target_id, "description": f"{alert_type} target evidence."}]
    if event_id:
        evidence.append({"type": "event", "id": event_id, "description": f"{alert_type} event evidence."})
    return {
        "id": f"alert-{tick}-pending",
        "tick": tick,
        "ts": f"tick-{tick:06d}",
        "severity": severity,
        "alert_type": alert_type,
        "target_type": target_type,
        "target_id": target_id,
        "summary": f"{alert_type} on {target_type} {target_id}.",
        "evidence": evidence,
    }

