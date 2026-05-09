from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from netagent_lab.agent.run_store import list_tool_calls
from netagent_lab.controls.evidence import collect_evidence_refs
from netagent_lab.controls.redaction import redact_sensitive_fields
from netagent_lab.db import get_snapshot, list_alerts, list_sim_events, list_snapshots, list_telemetry_samples
from netagent_lab.evals.runner import run_all_agent_evals
from netagent_lab.knowledge.store import KnowledgeBase
from netagent_lab.monitoring.diff import diff_snapshot_aliases
from netagent_lab.normalization.schemas import EvidenceRef
from netagent_lab.reasoning.alerts import evaluate_alerts
from netagent_lab.sim.state import SimulationStateStore


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = lambda cursor, row: {column[0]: row[index] for index, column in enumerate(cursor.description)}
    return conn


def get_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    state = SimulationStateStore.load(conn)
    latest_snapshot = get_snapshot(conn, "latest")
    payload = {
        "topology_name": state.topology.name,
        "current_tick": state.current_tick,
        "device_count": len(state.devices),
        "link_count": len(state.links),
        "service_count": len(state.services),
        "active_alerts": evaluate_alerts(KnowledgeBase.from_db(conn)),
        "latest_snapshot_id": latest_snapshot["id"] if latest_snapshot else None,
    }
    return redact_sensitive_fields(payload)


def get_simulation_state(conn: sqlite3.Connection) -> dict[str, Any]:
    state = SimulationStateStore.load(conn)
    payload = {
        "devices": {device_id: device.model_dump(mode="json") for device_id, device in state.devices.items()},
        "interfaces": {key: item.model_dump(mode="json") for key, item in state.interfaces.items()},
        "links": {link_id: state.link_metadata(link_id) for link_id in state.links},
        "services": {service_id: service.model_dump(mode="json") for service_id, service in state.services.items()},
        "probes": {probe_id: probe.model_dump(mode="json") for probe_id, probe in state.probes.items()},
        "route_blocks": state.route_blocks,
    }
    return redact_sensitive_fields(payload)


def get_snapshots_and_diff(
    conn: sqlite3.Connection,
    from_snapshot: str = "latest-1",
    to_snapshot: str = "latest",
) -> dict[str, Any]:
    snapshots = list_snapshots(conn)
    diff = None
    errors: list[str] = []
    if len(snapshots) >= 2:
        try:
            diff = diff_snapshot_aliases(conn, from_snapshot, to_snapshot)
        except Exception as exc:
            errors.append(str(exc))
    return redact_sensitive_fields({"snapshots": snapshots, "diff": diff, "errors": errors})


def list_agent_runs_readonly(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    if not _table_exists(conn, "agent_runs"):
        return []
    rows = conn.execute("SELECT * FROM agent_runs ORDER BY created_at DESC").fetchall()
    return [redact_sensitive_fields(_decode_run(row)) for row in rows]


def get_agent_run_detail(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _table_exists(conn, "agent_runs"):
        return None
    row = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
    return redact_sensitive_fields(_decode_run(row)) if row else None


def get_tool_trace(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "agent_tool_calls"):
        return []
    return redact_sensitive_fields({"calls": list_tool_calls(conn, run_id)})["calls"]


def get_evidence_explorer(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = get_agent_run_detail(conn, run_id)
    if not run or not run.get("final_report"):
        return {"run_id": run_id, "evidence": []}
    refs = collect_evidence_refs(run["final_report"])
    items = []
    for ref in refs:
        target = resolve_evidence(conn, ref)
        items.append(
            {
                "type": ref.type,
                "id": ref.id,
                "description": ref.description,
                "exists": target is not None,
                "source": _source_for_evidence_type(ref.type),
                "target": target,
            }
        )
    return redact_sensitive_fields({"run_id": run_id, "evidence": items})


def resolve_evidence(conn: sqlite3.Connection, evidence_ref: EvidenceRef | dict[str, Any]) -> dict[str, Any] | None:
    ref = evidence_ref if isinstance(evidence_ref, EvidenceRef) else EvidenceRef.model_validate(evidence_ref)
    kb = KnowledgeBase.from_db(conn)
    if ref.type in {"event", "telemetry", "link", "service", "snapshot", "observation", "device", "interface", "probe"}:
        return kb.get_evidence(ref)
    if ref.type == "alert":
        return _find_by_id(list_alerts(conn), ref.id)
    if ref.type == "route_block":
        state = SimulationStateStore.load(conn)
        return _find_by_id(state.route_blocks, ref.id)
    if ref.type == "path_result":
        return _find_path_result(conn, ref.id)
    if ref.type == "topology":
        topology = kb.get_topology().model_dump(mode="json")
        return topology if topology.get("name") == ref.id else None
    if ref.type == "context":
        return {"id": ref.id, "type": "context", "description": ref.description}
    return None


def run_mock_evals_for_ui() -> dict[str, Any]:
    return redact_sensitive_fields(run_all_agent_evals("mock"))


def get_recent_events_and_telemetry(conn: sqlite3.Connection) -> dict[str, Any]:
    return redact_sensitive_fields({"events": list_sim_events(conn), "telemetry": list_telemetry_samples(conn)})


def _decode_run(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["final_report"] = json.loads(item.pop("final_report_json")) if item.get("final_report_json") else None
    item["errors"] = json.loads(item.pop("errors_json")) if item.get("errors_json") else []
    item["usage"] = json.loads(item.pop("usage_json")) if item.get("usage_json") else {}
    return item


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
    return row is not None


def _find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def _find_path_result(conn: sqlite3.Connection, evidence_id: str) -> dict[str, Any] | None:
    for snapshot in list_snapshots(conn):
        target = _find_nested_id(snapshot.get("paths"), evidence_id)
        if target is not None:
            return target
    return None


def _find_nested_id(value: Any, evidence_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("id") == evidence_id:
            return value
        for evidence in value.get("evidence", []) if isinstance(value.get("evidence"), list) else []:
            if isinstance(evidence, dict) and evidence.get("id") == evidence_id:
                return value
        for child in value.values():
            found = _find_nested_id(child, evidence_id)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_nested_id(child, evidence_id)
            if found is not None:
                return found
    return None


def _source_for_evidence_type(evidence_type: str) -> str:
    mapping = {
        "event": "event log",
        "telemetry": "telemetry sample",
        "link": "link state",
        "service": "service state",
        "snapshot": "snapshot",
        "alert": "alert",
        "path_result": "deterministic pathing",
        "route_block": "simulated route block",
        "probe": "probe result",
    }
    return mapping.get(evidence_type, evidence_type)
