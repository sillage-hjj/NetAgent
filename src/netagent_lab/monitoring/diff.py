from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.db import get_snapshot


def diff_snapshots(snapshot_a: dict[str, Any], snapshot_b: dict[str, Any]) -> dict[str, Any]:
    changed_devices = _changed(snapshot_a, snapshot_b, "devices")
    changed_interfaces = _changed(snapshot_a, snapshot_b, "interfaces")
    changed_links = _changed(snapshot_a, snapshot_b, "links")
    changed_services = _changed(snapshot_a, snapshot_b, "services")
    changed_probes = _changed(snapshot_a, snapshot_b, "probes")
    old_alerts = {alert["id"]: alert for alert in snapshot_a.get("alerts", [])}
    new_alerts_by_id = {alert["id"]: alert for alert in snapshot_b.get("alerts", [])}
    old_events = {event["id"]: event for event in snapshot_a.get("events_since_previous", [])}
    new_events_by_id = {event["id"]: event for event in snapshot_b.get("events_since_previous", [])}
    result = {
        "from_snapshot": snapshot_a["id"],
        "to_snapshot": snapshot_b["id"],
        "changed_devices": changed_devices,
        "changed_interfaces": changed_interfaces,
        "changed_links": changed_links,
        "changed_services": changed_services,
        "changed_probes": changed_probes,
        "new_alerts": [alert for alert_id, alert in new_alerts_by_id.items() if alert_id not in old_alerts],
        "resolved_alerts": [alert for alert_id, alert in old_alerts.items() if alert_id not in new_alerts_by_id],
        "new_events": [event for event_id, event in new_events_by_id.items() if event_id not in old_events],
    }
    changed_count = sum(len(result[key]) for key in result if key.startswith("changed_"))
    result["summary"] = (
        f"{changed_count} state group change(s), "
        f"{len(result['new_alerts'])} new alert(s), "
        f"{len(result['new_events'])} new event(s)."
    )
    return result


def diff_latest_snapshots(conn: sqlite3.Connection) -> dict[str, Any]:
    from_snapshot = get_snapshot(conn, "latest-1")
    to_snapshot = get_snapshot(conn, "latest")
    if from_snapshot is None or to_snapshot is None:
        raise ValueError("At least two snapshots are required")
    return diff_snapshots(from_snapshot, to_snapshot)


def diff_snapshot_aliases(conn: sqlite3.Connection, from_alias: str, to_alias: str) -> dict[str, Any]:
    from_snapshot = get_snapshot(conn, from_alias)
    to_snapshot = get_snapshot(conn, to_alias)
    if from_snapshot is None:
        raise ValueError(f"Snapshot not found: {from_alias}")
    if to_snapshot is None:
        raise ValueError(f"Snapshot not found: {to_alias}")
    return diff_snapshots(from_snapshot, to_snapshot)


def _changed(snapshot_a: dict[str, Any], snapshot_b: dict[str, Any], key: str) -> list[dict[str, Any]]:
    before = snapshot_a.get(key, {})
    after = snapshot_b.get(key, {})
    ids = sorted(set(before) | set(after))
    return [
        {"id": item_id, "before": before.get(item_id), "after": after.get(item_id)}
        for item_id in ids
        if before.get(item_id) != after.get(item_id)
    ]

