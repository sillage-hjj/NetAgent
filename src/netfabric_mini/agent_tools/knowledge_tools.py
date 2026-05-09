from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.agent_tools._common import ok_result
from netfabric_mini.knowledge.store import KnowledgeBase


def collect_link_states(conn: sqlite3.Connection, args: dict[str, Any]):
    kb = KnowledgeBase.from_db(conn)
    state = kb.get_current_state()
    link_ids = args.get("link_ids") or list(state.links)
    links = {link_id: kb.get_link(link_id) for link_id in link_ids}
    return ok_result("collect_link_states", {"links": links})


def collect_device_states(conn: sqlite3.Connection, args: dict[str, Any]):
    kb = KnowledgeBase.from_db(conn)
    state = kb.get_current_state()
    device_ids = args.get("device_ids") or list(state.devices)
    devices = {device_id: kb.get_device(device_id) for device_id in device_ids}
    return ok_result("collect_device_states", {"devices": devices})


def collect_service_states(conn: sqlite3.Connection, args: dict[str, Any]):
    kb = KnowledgeBase.from_db(conn)
    state = kb.get_current_state()
    service_ids = args.get("service_ids") or list(state.services)
    services = {service_id: kb.get_service(service_id) for service_id in service_ids}
    return ok_result("collect_service_states", {"services": services})


def get_recent_events(conn: sqlite3.Connection, args: dict[str, Any]):
    events = KnowledgeBase.from_db(conn).get_recent_events(args.get("since_tick"))
    if args.get("target_id"):
        events = [event for event in events if event.get("target_id") == args["target_id"]]
    if args.get("event_type"):
        events = [event for event in events if event.get("event_type") == args["event_type"]]
    return ok_result("get_recent_events", {"events": events})


def get_recent_telemetry(conn: sqlite3.Connection, args: dict[str, Any]):
    telemetry = KnowledgeBase.from_db(conn).get_recent_telemetry(args.get("since_tick"))
    if args.get("target_id"):
        telemetry = [sample for sample in telemetry if sample.get("target_id") == args["target_id"]]
    if args.get("metric"):
        telemetry = [sample for sample in telemetry if sample.get("metric") == args["metric"]]
    return ok_result("get_recent_telemetry", {"telemetry": telemetry})


def get_latest_snapshot(conn: sqlite3.Connection, args: dict[str, Any]):
    snapshot = KnowledgeBase.from_db(conn).get_snapshot("latest")
    return ok_result("get_latest_snapshot", {"snapshot": snapshot}, fallback_evidence=[{"type": "snapshot", "id": snapshot["id"]}] if snapshot else None)


def get_snapshot(conn: sqlite3.Connection, args: dict[str, Any]):
    snapshot = KnowledgeBase.from_db(conn).get_snapshot(args["snapshot_id_or_alias"])
    return ok_result("get_snapshot", {"snapshot": snapshot}, fallback_evidence=[{"type": "snapshot", "id": snapshot["id"]}] if snapshot else None)

