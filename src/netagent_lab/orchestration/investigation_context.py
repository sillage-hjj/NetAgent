from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.controls.data_budget import apply_context_budget
from netagent_lab.controls.evidence import collect_evidence_refs
from netagent_lab.controls.redaction import redact_sensitive_fields
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.reasoning.alerts import evaluate_alerts
from netagent_lab.reasoning.reachability import collect_reachability_matrix


def build_investigation_context(
    conn: sqlite3.Connection,
    focus: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kb = KnowledgeBase.from_db(conn)
    state = kb.get_current_state()
    link_metadata = {link_id: state.link_metadata(link_id) for link_id in state.links}
    alerts = evaluate_alerts(kb)
    reachability = collect_reachability_matrix(kb)
    latest_snapshot = kb.get_snapshot("latest")
    context = {
        "topology_summary": {
            "name": state.topology.name,
            "devices": len(state.topology.devices),
            "links": len(state.topology.links),
            "services": len(state.topology.services),
        },
        "current_tick": state.current_tick,
        "focus": focus or {},
        "active_alerts": alerts,
        "affected_links": [alert["target_id"] for alert in alerts if alert["target_type"] == "link"],
        "affected_devices": [alert["target_id"] for alert in alerts if alert["target_type"] == "device"],
        "affected_services": [alert["target_id"] for alert in alerts if alert["target_type"] == "service"],
        "recent_events": kb.get_recent_events(),
        "recent_telemetry": kb.get_recent_telemetry(),
        "reachability_matrix": reachability,
        "link_state_metadata": link_metadata,
        "latest_snapshot_id": latest_snapshot["id"] if latest_snapshot else None,
    }
    context["evidence_refs"] = [ref.model_dump(mode="json") for ref in collect_evidence_refs(context)]
    context["evidence_ids"] = [ref["id"] for ref in context["evidence_refs"]]
    return apply_context_budget(redact_sensitive_fields(context), budget)
