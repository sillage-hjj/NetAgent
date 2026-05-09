from __future__ import annotations

import json
import sqlite3
from typing import Any

from netfabric_mini.db import get_snapshot, list_alerts, list_sim_events, list_telemetry_samples
from netfabric_mini.monitoring.collectors import collect_all_state, collect_link_states, collect_reachability_matrix
from netfabric_mini.orchestration.investigation_context import build_investigation_context
from netfabric_mini.sim.state import SimulationStateStore


def export_current_state_json(conn: sqlite3.Connection) -> dict[str, Any]:
    return collect_all_state(conn)["result"]


def export_latest_snapshot_json(conn: sqlite3.Connection) -> dict[str, Any]:
    snapshot = get_snapshot(conn, "latest")
    if snapshot is None:
        raise ValueError("No snapshots are available")
    return snapshot


def export_events_jsonl(conn: sqlite3.Connection) -> str:
    return _jsonl(list_sim_events(conn))


def export_telemetry_jsonl(conn: sqlite3.Connection) -> str:
    return _jsonl(list_telemetry_samples(conn))


def export_llm_ready_context(conn: sqlite3.Connection) -> dict[str, Any]:
    return build_investigation_context(conn)


def _jsonl(items: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(item, sort_keys=True) for item in items)
