from __future__ import annotations


def classify_question(question: str) -> dict[str, str]:
    text = question.lower()
    if any(word in text for word in ("unreachable", "cannot reach", "can't reach", "down")) and "route" in text:
        category = "route_withdrawal"
    elif any(word in text for word in ("unreachable", "cannot access", "cannot reach", "can't reach")):
        category = "service_unreachable"
    elif any(word in text for word in ("slow", "latency", "loss", "degraded")):
        category = "service_degraded"
    elif any(word in text for word in ("congestion", "utilization", "packet loss")):
        category = "congestion"
    elif any(word in text for word in ("link", "fiber")):
        category = "link_failure"
    elif "device" in text or "router" in text:
        category = "device_failure"
    elif "diff" in text or "changed" in text:
        category = "snapshot_diff"
    elif "summary" in text or "state" in text or "monitor" in text:
        category = "monitoring_summary"
    else:
        category = "unknown"
    return {"category": category}


def suggest_initial_tools(question: str, focus: dict | None = None) -> list[str]:
    category = classify_question(question)["category"]
    if category in {"service_unreachable", "route_withdrawal"}:
        return ["run_monitoring_cycle", "get_active_alerts", "check_service_reachability", "infer_path"]
    if category in {"service_degraded", "congestion"}:
        return ["get_current_context", "collect_link_states", "evaluate_alerts"]
    if category == "snapshot_diff":
        return ["get_latest_snapshot", "diff_snapshots"]
    if category == "device_failure":
        return ["run_monitoring_cycle", "collect_device_states", "evaluate_alerts"]
    return ["get_current_context"]

