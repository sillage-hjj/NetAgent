from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.acl_checker import check_acl
from netagent_lab.db import get_by_id
from netagent_lab.metrics import query_metric_trend
from netagent_lab.topology_model import infer_path

EVENT_PRIORITIES = {
    "link_state_change": 1,
    "routing_neighbor_change": 2,
    "acl_deny": 3,
    "cpu_high": 4,
    "packet_loss": 5,
}


def get_ticket(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    ticket = get_by_id(conn, "tickets", ticket_id)
    if ticket is None:
        return _tool_response("get_ticket", False, None, [], [f"Ticket not found: {ticket_id}"])
    evidence = [
        {
            "type": "ticket",
            "id": ticket["id"],
            "description": f"Ticket {ticket['id']} opened at {ticket['ts']}: {ticket['text']}",
        }
    ]
    return _tool_response("get_ticket", True, ticket, evidence, [])


def get_recent_events(
    conn: sqlite3.Connection,
    device: str | None = None,
    event_type: str | None = None,
) -> dict[str, Any]:
    query = "SELECT * FROM events"
    clauses: list[str] = []
    params: list[str] = []
    if device is not None:
        clauses.append("device = ?")
        params.append(device)
    if event_type is not None:
        clauses.append("event_type = ?")
        params.append(event_type)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY ts, id"
    events = [_normalize_event(row) for row in conn.execute(query, tuple(params)).fetchall()]
    evidence = [
        {
            "type": "event",
            "id": event["id"],
            "description": f"{event['event_type']} on {event['device']} from raw log {event['raw_log_id']}.",
        }
        for event in events
    ]
    return _tool_response("get_recent_events", True, events, evidence, [])


def get_raw_log(conn: sqlite3.Connection, raw_log_id: str) -> dict[str, Any]:
    raw_log = get_by_id(conn, "raw_logs", raw_log_id)
    if raw_log is None:
        return _tool_response("get_raw_log", False, None, [], [f"Raw log not found: {raw_log_id}"])
    evidence = [
        {
            "type": "raw_log",
            "id": raw_log["id"],
            "description": raw_log["line"],
        }
    ]
    return _tool_response("get_raw_log", True, raw_log, evidence, [])


def infer_path_tool(conn: sqlite3.Connection, src_device: str, dst_device: str) -> dict[str, Any]:
    result = infer_path(conn, src_device, dst_device)
    return _tool_response("infer_path", True, result, result["evidence"], [])


def check_acl_tool(
    conn: sqlite3.Connection,
    src_ip: str,
    dst_ip: str,
    protocol: str,
    port: int,
    path: list[str] | None = None,
) -> dict[str, Any]:
    result = check_acl(conn, src_ip, dst_ip, protocol, port, path)
    return _tool_response("check_acl", True, result, result["evidence"], [])


def query_metric_trend_tool(conn: sqlite3.Connection, device: str, metric: str) -> dict[str, Any]:
    result = query_metric_trend(conn, device, metric)
    return _tool_response("query_metric_trend", True, result, result["evidence"], [])


def find_relevant_events_on_path(conn: sqlite3.Connection, path: list[str]) -> dict[str, Any]:
    if not path:
        return {
            "relevant": False,
            "events": [],
            "evidence": [],
            "explanation": "No path devices were supplied for event correlation.",
        }

    placeholders = ",".join("?" for _ in path)
    rows = conn.execute(
        f"""
        SELECT * FROM events
        WHERE device IN ({placeholders})
        ORDER BY ts, id
        """,
        tuple(path),
    ).fetchall()
    relevant_events = [_normalize_event(row) for row in rows if _is_relevant_event(row)]
    relevant_events.sort(key=lambda event: (EVENT_PRIORITIES[event["event_type"]], event["ts"]))
    evidence = [
        {
            "type": "event",
            "id": event["id"],
            "description": (
                f"{event['event_type']} on {event['device']} at {event['ts']} "
                f"from raw log {event['raw_log_id']}."
            ),
        }
        for event in relevant_events
    ]
    if relevant_events:
        explanation = f"Found {len(relevant_events)} relevant event(s) on path devices."
    else:
        explanation = "No prioritized event types were found on the supplied path devices."

    return {
        "relevant": bool(relevant_events),
        "events": relevant_events,
        "evidence": evidence,
        "explanation": explanation,
    }


def _normalize_event(row: dict[str, Any]) -> dict[str, Any]:
    import json

    event = dict(row)
    if "params_json" in event:
        event["params"] = json.loads(event.pop("params_json"))
    return event


def _is_relevant_event(row: dict[str, Any]) -> bool:
    event = _normalize_event(row)
    event_type = event["event_type"]
    params = event["params"]
    if event_type == "link_state_change":
        return params.get("state") == "down"
    if event_type == "routing_neighbor_change":
        return params.get("to_state") == "DOWN"
    return event_type in {"acl_deny", "cpu_high", "packet_loss"}


def _tool_response(
    tool_name: str,
    ok: bool,
    result: Any,
    evidence: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "ok": ok,
        "result": result,
        "evidence": evidence,
        "errors": errors,
    }
