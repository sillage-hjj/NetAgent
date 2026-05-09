from __future__ import annotations

from typing import Any

from netagent_lab.knowledge.store import KnowledgeBase


def evaluate_link_health(kb: KnowledgeBase, link_id: str) -> dict[str, Any]:
    link = kb.get_link(link_id)
    reasons = []
    if link["effective_state"] != "up":
        reasons.append("link_down")
    if link["latency_ms"] > 100:
        reasons.append("high_latency")
    if link["loss_percent"] > 5:
        reasons.append("packet_loss")
    if link["utilization_percent"] > 85:
        reasons.append("high_utilization")
    if link["error_rate_percent"] > 5:
        reasons.append("high_error_rate")
    status = "down" if "link_down" in reasons else "degraded" if reasons else "healthy"
    return {
        "object_type": "link",
        "object_id": link_id,
        "status": status,
        "reasons": reasons,
        "evidence": [{"type": "link", "id": link_id, "description": "Link health evaluated from KB link state."}],
    }


def evaluate_device_health(kb: KnowledgeBase, device_id: str) -> dict[str, Any]:
    device = kb.get_device(device_id)
    reasons = []
    if device["admin_state"] != "up" or device["oper_state"] != "up":
        reasons.append("device_down")
    if device["cpu_utilization_percent"] > 85:
        reasons.append("high_cpu")
    if device["memory_utilization_percent"] > 90:
        reasons.append("high_memory")
    status = "down" if "device_down" in reasons else "degraded" if reasons else "healthy"
    return {
        "object_type": "device",
        "object_id": device_id,
        "status": status,
        "reasons": reasons,
        "evidence": [{"type": "device", "id": device_id, "description": "Device health evaluated from KB state."}],
    }


def evaluate_service_health(kb: KnowledgeBase, service_id: str) -> dict[str, Any]:
    service = kb.get_service(service_id)
    status = service["runtime"]["status"]
    reasons = [] if status == "up" else [f"service_{status}"]
    return {
        "object_type": "service",
        "object_id": service_id,
        "status": "healthy" if status == "up" else status,
        "reasons": reasons,
        "evidence": [{"type": "service", "id": service_id, "description": "Service health evaluated from KB state."}],
    }


def evaluate_path_health(path_result: dict[str, Any]) -> dict[str, Any]:
    if not path_result.get("reachable"):
        status = "unreachable"
        reasons = path_result.get("blocking_reasons", [])
    elif path_result.get("degraded"):
        status = "degraded"
        reasons = path_result.get("degradation_reasons", [])
    else:
        status = "healthy"
        reasons = []
    return {
        "status": status,
        "reasons": reasons,
        "evidence": path_result.get("evidence", []),
    }

