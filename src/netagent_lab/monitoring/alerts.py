from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.db import next_sim_sequence
from netagent_lab.sim.schemas import TelemetrySample
from netagent_lab.sim.state import SimulationStateStore


def evaluate_alerts(
    conn: sqlite3.Connection,
    state_store: SimulationStateStore,
    telemetry_samples: list[TelemetrySample],
    probe_results: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    tick = state_store.current_tick

    for device in state_store.list_devices():
        if not state_store.effective_device_up(device.device_id):
            alerts.append(_alert(conn, tick, "critical", "device_down", "device", device.device_id, f"Device {device.device_id} is down.", device.last_event_id))
        if device.cpu_utilization_percent > 85:
            alerts.append(_alert(conn, tick, "warning", "high_cpu", "device", device.device_id, f"CPU is {device.cpu_utilization_percent}%.", device.last_event_id))
        if device.memory_utilization_percent > 90:
            alerts.append(_alert(conn, tick, "warning", "high_memory", "device", device.device_id, f"Memory is {device.memory_utilization_percent}%.", device.last_event_id))

    for service in state_store.list_services():
        topology_service = state_store.get_topology_service(service.service_id)
        if service.status == "down":
            severity = "critical" if topology_service.criticality == "critical" else "warning"
            alerts.append(_alert(conn, tick, severity, "service_down", "service", service.service_id, f"Service {service.service_id} is down.", service.last_event_id))

    for link_id in state_store.links:
        metadata = state_store.link_metadata(link_id)
        critical = "critical" in metadata["tags"]
        if metadata["effective_state"] == "down":
            alerts.append(_alert(conn, tick, "critical" if critical else "warning", "link_down", "link", link_id, f"Link {link_id} is down.", metadata.get("last_event_id")))
        if metadata["latency_ms"] > 100:
            alerts.append(_alert(conn, tick, "warning", "high_latency", "link", link_id, f"Latency is {metadata['latency_ms']} ms.", metadata.get("last_event_id")))
        if metadata["loss_percent"] > 5:
            alerts.append(_alert(conn, tick, "warning", "high_packet_loss", "link", link_id, f"Packet loss is {metadata['loss_percent']}%.", metadata.get("last_event_id")))
        if metadata["utilization_percent"] > 85:
            alerts.append(_alert(conn, tick, "warning", "high_utilization", "link", link_id, f"Utilization is {metadata['utilization_percent']}%.", metadata.get("last_event_id")))
        if metadata["error_rate_percent"] > 5:
            alerts.append(_alert(conn, tick, "warning", "high_error_rate", "link", link_id, f"Error rate is {metadata['error_rate_percent']}%.", metadata.get("last_event_id")))
        if metadata["flap_count"] >= 3:
            alerts.append(_alert(conn, tick, "warning", "repeated_flaps", "link", link_id, f"Flap count is {metadata['flap_count']}.", metadata.get("last_event_id")))

    for probe_id, result in probe_results.items():
        target_service = result.get("target_service")
        service = state_store.get_topology_service(target_service) if target_service else None
        if not result.get("reachable", False):
            severity = "critical" if service and service.criticality == "critical" else "warning"
            alerts.append(_alert(conn, tick, severity, "probe_unreachable", "probe", probe_id, f"Probe {probe_id} is unreachable.", None))
        elif result.get("degraded", False):
            alerts.append(_alert(conn, tick, "warning", "probe_degraded", "probe", probe_id, f"Probe {probe_id} is degraded.", None))

    return _renumber_alerts(alerts)


def _alert(
    conn: sqlite3.Connection,
    tick: int,
    severity: str,
    alert_type: str,
    target_type: str,
    target_id: str,
    summary: str,
    event_id: str | None,
) -> dict[str, Any]:
    sequence = next_sim_sequence(conn, "sim_alerts", tick)
    return {
        "id": f"alert-{tick}-{sequence:04d}",
        "tick": tick,
        "ts": f"tick-{tick:06d}",
        "severity": severity,
        "alert_type": alert_type,
        "target_type": target_type,
        "target_id": target_id,
        "summary": summary,
        "evidence": [{"type": target_type, "id": target_id}] + ([{"type": "event", "id": event_id}] if event_id else []),
    }


def _renumber_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not alerts:
        return []
    tick = alerts[0]["tick"]
    for index, alert in enumerate(alerts, start=1):
        alert["id"] = f"alert-{tick}-{index:04d}"
    return alerts

