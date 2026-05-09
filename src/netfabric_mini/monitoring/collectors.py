from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.ingestion.simulated_collectors import (
    collect_sim_all,
    collect_sim_device_states,
    collect_sim_interface_states,
    collect_sim_inventory,
    collect_sim_link_states,
    collect_sim_probe_results,
    collect_sim_reachability_matrix,
    collect_sim_recent_events,
    collect_sim_recent_telemetry,
    collect_sim_service_states,
)


def collect_inventory(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_inventory", collect_sim_inventory(conn))


def collect_device_states(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_device_states", collect_sim_device_states(conn))


def collect_interface_states(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_interface_states", collect_sim_interface_states(conn))


def collect_link_states(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_link_states", collect_sim_link_states(conn))


def collect_service_states(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_service_states", collect_sim_service_states(conn))


def collect_probe_results(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_probe_results", collect_sim_probe_results(conn))


def collect_recent_events(conn: sqlite3.Connection, since_tick: int | None = None) -> dict[str, Any]:
    return _legacy_response("collect_recent_events", collect_sim_recent_events(conn, since_tick))


def collect_recent_telemetry(conn: sqlite3.Connection, since_tick: int | None = None) -> dict[str, Any]:
    return _legacy_response("collect_recent_telemetry", collect_sim_recent_telemetry(conn, since_tick))


def collect_reachability_matrix(conn: sqlite3.Connection) -> dict[str, Any]:
    return _legacy_response("collect_reachability_matrix", collect_sim_reachability_matrix(conn))


def collect_all_state(conn: sqlite3.Connection) -> dict[str, Any]:
    results = collect_sim_all(conn)
    by_name = {result.collector: result for result in results}
    reachability = collect_sim_reachability_matrix(conn)
    result = {
        "inventory": by_name["collect_sim_inventory"].result,
        "devices": by_name["collect_sim_device_states"].result,
        "interfaces": by_name["collect_sim_interface_states"].result,
        "links": by_name["collect_sim_link_states"].result,
        "services": by_name["collect_sim_service_states"].result,
        "probes": by_name["collect_sim_probe_results"].result,
        "reachability": reachability.result,
        "events": by_name["collect_sim_recent_events"].result,
        "telemetry": by_name["collect_sim_recent_telemetry"].result,
    }
    return _response("collect_all_state", results[0].tick if results else 0, result, [{"type": "collector", "id": "collect_all_state"}])


def _response(
    collector: str,
    tick: int,
    result: Any,
    evidence: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "collector": collector,
        "ok": not errors,
        "tick": tick,
        "result": result,
        "evidence": evidence,
        "errors": errors or [],
    }


def _legacy_response(collector: str, result: Any) -> dict[str, Any]:
    return _response(
        collector,
        result.tick,
        result.result,
        [item.model_dump(mode="json") for item in result.evidence],
        result.errors,
    )
