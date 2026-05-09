from __future__ import annotations

import sqlite3
from typing import Any

from netagent_lab.db import get_current_tick, insert_snapshot, list_snapshots, next_sim_sequence
from netagent_lab.monitoring import collectors
from netagent_lab.sim.schemas import MonitoringSnapshot
from netagent_lab.sim.state import SimulationStateStore


def create_monitoring_snapshot(
    conn: sqlite3.Connection,
    *,
    alerts: list[dict[str, Any]] | None = None,
    since_tick: int | None = None,
) -> MonitoringSnapshot:
    state = SimulationStateStore.load(conn)
    tick = get_current_tick(conn)
    sequence = next_sim_sequence(conn, "sim_snapshots", tick)
    recent_events = collectors.collect_recent_events(conn, since_tick)["result"]
    reachability = collectors.collect_reachability_matrix(conn)["result"]
    return MonitoringSnapshot(
        id=f"snapshot-{tick}-{sequence:04d}",
        tick=tick,
        ts=f"tick-{tick:06d}",
        topology_name=state.topology.name,
        inventory=collectors.collect_inventory(conn)["result"],
        devices=collectors.collect_device_states(conn)["result"],
        interfaces=collectors.collect_interface_states(conn)["result"],
        links=collectors.collect_link_states(conn)["result"],
        services=collectors.collect_service_states(conn)["result"],
        probes=collectors.collect_probe_results(conn)["result"],
        paths=reachability,
        alerts=alerts or [],
        events_since_previous=recent_events,
    )


def save_monitoring_snapshot(conn: sqlite3.Connection, snapshot: MonitoringSnapshot) -> str:
    return insert_snapshot(conn, snapshot)


def latest_snapshot_tick(conn: sqlite3.Connection) -> int | None:
    snapshots = list_snapshots(conn)
    if not snapshots:
        return None
    return int(snapshots[-1]["tick"])

