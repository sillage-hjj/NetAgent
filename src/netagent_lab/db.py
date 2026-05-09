from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from netagent_lab.schemas import AclRule, Device, Link, MetricSample, ParsedEvent, RawLog, Ticket
from netagent_lab.sim.schemas import (
    DeviceRuntimeState,
    InterfaceRuntimeState,
    LinkRuntimeState,
    MonitoringSnapshot,
    ServiceRuntimeState,
    SimTopology,
    SimulationEvent,
    TelemetrySample,
)


TABLES = {
    "devices",
    "links",
    "raw_logs",
    "events",
    "acl_rules",
    "tickets",
    "metrics",
}


def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, Any]:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def init_db(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    return conn


def init_sim_db(path: str | Path) -> sqlite3.Connection:
    conn = init_db(path)
    _create_sim_tables(conn)
    return conn


def connect_db(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            site TEXT,
            vendor TEXT
        );

        CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY,
            src_device TEXT NOT NULL,
            src_interface TEXT NOT NULL,
            dst_device TEXT NOT NULL,
            dst_interface TEXT NOT NULL,
            weight INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('up', 'down'))
        );

        CREATE TABLE IF NOT EXISTS raw_logs (
            id TEXT PRIMARY KEY,
            line TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            device TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            params_json TEXT NOT NULL,
            raw_log_id TEXT NOT NULL,
            FOREIGN KEY(raw_log_id) REFERENCES raw_logs(id)
        );

        CREATE TABLE IF NOT EXISTS acl_rules (
            id TEXT PRIMARY KEY,
            device TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            src_prefix TEXT NOT NULL,
            dst_prefix TEXT NOT NULL,
            protocol TEXT NOT NULL,
            port INTEGER NOT NULL,
            action TEXT NOT NULL CHECK (action IN ('allow', 'deny'))
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            text TEXT NOT NULL,
            src_site TEXT,
            dst_service TEXT,
            protocol TEXT,
            port INTEGER
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            device TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT
        );
        """
    )
    conn.commit()


def _create_sim_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sim_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_topology (
            id TEXT PRIMARY KEY,
            topology_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_devices (
            device_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_interfaces (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            interface_id TEXT NOT NULL,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_links (
            link_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_services (
            service_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_probes (
            probe_id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_events (
            event_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            ts TEXT NOT NULL,
            event_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_telemetry (
            sample_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            ts TEXT NOT NULL,
            source TEXT NOT NULL,
            metric TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            ts TEXT NOT NULL,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_alerts (
            alert_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            ts TEXT NOT NULL,
            severity TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_normalized_states (
            state_id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL,
            data_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sim_normalized_observations (
            observation_id TEXT PRIMARY KEY,
            state_id TEXT NOT NULL,
            tick INTEGER NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            data_json TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset_case_tables(conn: sqlite3.Connection) -> None:
    for table in ("events", "metrics", "tickets", "acl_rules", "raw_logs", "links", "devices"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def _ensure_table(table: str) -> None:
    if table not in TABLES:
        raise ValueError(f"Unsupported table: {table}")


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    _ensure_table(table)
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])


def query_all(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    _ensure_table(table)
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    return [_normalize_row(table, row) for row in rows]


def get_by_id(conn: sqlite3.Connection, table: str, item_id: str) -> dict[str, Any] | None:
    _ensure_table(table)
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    return _normalize_row(table, row) if row else None


def insert_device(conn: sqlite3.Connection, device: Device) -> None:
    conn.execute(
        "INSERT INTO devices (id, role, site, vendor) VALUES (?, ?, ?, ?)",
        (device.id, device.role, device.site, device.vendor),
    )


def insert_link(conn: sqlite3.Connection, link_id: str, link: Link) -> None:
    conn.execute(
        """
        INSERT INTO links
            (id, src_device, src_interface, dst_device, dst_interface, weight, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            link_id,
            link.src_device,
            link.src_interface,
            link.dst_device,
            link.dst_interface,
            link.weight,
            link.status,
        ),
    )


def insert_raw_log(conn: sqlite3.Connection, raw_log: RawLog) -> None:
    conn.execute("INSERT INTO raw_logs (id, line) VALUES (?, ?)", (raw_log.id, raw_log.line))


def insert_event(conn: sqlite3.Connection, event: ParsedEvent) -> None:
    conn.execute(
        """
        INSERT INTO events
            (id, ts, device, event_type, severity, params_json, raw_log_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.id,
            event.ts,
            event.device,
            event.event_type,
            event.severity,
            json.dumps(event.params, sort_keys=True),
            event.raw_log_id,
        ),
    )


def insert_acl_rule(conn: sqlite3.Connection, rule: AclRule) -> None:
    conn.execute(
        """
        INSERT INTO acl_rules
            (id, device, rule_name, src_prefix, dst_prefix, protocol, port, action)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rule.id,
            rule.device,
            rule.rule_name,
            rule.src_prefix,
            rule.dst_prefix,
            rule.protocol.lower(),
            rule.port,
            rule.action,
        ),
    )


def insert_ticket(conn: sqlite3.Connection, ticket: Ticket) -> None:
    conn.execute(
        """
        INSERT INTO tickets
            (id, ts, text, src_site, dst_service, protocol, port)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticket.id,
            ticket.ts,
            ticket.text,
            ticket.src_site,
            ticket.dst_service,
            ticket.protocol.lower() if ticket.protocol else None,
            ticket.port,
        ),
    )


def insert_metric(conn: sqlite3.Connection, metric: MetricSample) -> None:
    conn.execute(
        """
        INSERT INTO metrics
            (id, ts, device, metric, value, unit)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (metric.id, metric.ts, metric.device, metric.metric, metric.value, metric.unit),
    )


def _normalize_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    if table == "events" and "params_json" in normalized:
        normalized["params"] = json.loads(normalized.pop("params_json"))
    return normalized


def save_topology(conn: sqlite3.Connection, topology: SimTopology) -> None:
    conn.execute("DELETE FROM sim_topology")
    conn.execute(
        "INSERT INTO sim_topology (id, topology_json) VALUES (?, ?)",
        (topology.name, _json_dumps(topology.model_dump(mode="json"))),
    )
    conn.commit()


def load_topology_from_db(conn: sqlite3.Connection) -> SimTopology:
    row = conn.execute("SELECT topology_json FROM sim_topology ORDER BY id LIMIT 1").fetchone()
    if row is None:
        raise ValueError("Simulation topology has not been initialized")
    return SimTopology.model_validate(json.loads(row["topology_json"]))


def initialize_runtime_state(conn: sqlite3.Connection, topology: SimTopology) -> None:
    save_topology(conn, topology)
    for table in (
        "sim_devices",
        "sim_interfaces",
        "sim_links",
        "sim_services",
        "sim_probes",
        "sim_events",
        "sim_telemetry",
        "sim_snapshots",
        "sim_alerts",
        "sim_normalized_states",
        "sim_normalized_observations",
    ):
        conn.execute(f"DELETE FROM {table}")

    set_metadata(conn, "topology_name", topology.name)
    set_metadata(conn, "current_tick", "0")
    set_metadata(conn, "random_seed", "")
    set_metadata(conn, "created_at", _sim_ts(0))
    set_metadata(conn, "updated_at", _sim_ts(0))
    set_metadata(conn, "route_blocks_json", "[]")

    for device in topology.devices:
        upsert_sim_device_state(
            conn,
            DeviceRuntimeState(
                device_id=device.id,
                admin_state="up",
                oper_state=device.interfaces and device.interfaces[0].oper_state or "up",
                cpu_utilization_percent=10.0,
                memory_utilization_percent=25.0,
                last_change_tick=0,
            ),
        )
        for interface in device.interfaces:
            upsert_sim_interface_state(
                conn,
                InterfaceRuntimeState(
                    device_id=device.id,
                    interface_id=interface.id,
                    admin_state=interface.admin_state,
                    oper_state=interface.oper_state,
                    rx_errors=0,
                    tx_errors=0,
                    utilization_percent=0.0,
                    last_change_tick=0,
                ),
            )

    for link in topology.links:
        upsert_sim_link_state(
            conn,
            LinkRuntimeState(
                link_id=link.id,
                admin_state=link.admin_state,
                oper_state=link.oper_state,
                bandwidth_mbps=link.bandwidth_mbps,
                latency_ms=link.latency_ms,
                jitter_ms=link.jitter_ms,
                loss_percent=link.loss_percent,
                utilization_percent=link.utilization_percent,
                error_rate_percent=link.error_rate_percent,
                flap_count=0,
                last_change_tick=0,
            ),
        )

    for service in topology.services:
        upsert_sim_service_state(
            conn,
            ServiceRuntimeState(
                service_id=service.id,
                status="up",
                latency_ms=None,
                loss_percent=None,
                last_change_tick=0,
            ),
        )

    for probe in topology.probes:
        conn.execute(
            """
            INSERT OR REPLACE INTO sim_probes (probe_id, data_json)
            VALUES (?, ?)
            """,
            (probe.id, _json_dumps(probe.model_dump(mode="json"))),
        )
    conn.commit()


def get_current_tick(conn: sqlite3.Connection) -> int:
    value = get_metadata(conn, "current_tick")
    return int(value or 0)


def set_current_tick(conn: sqlite3.Connection, tick: int) -> None:
    if tick < 0:
        raise ValueError("tick must be >= 0")
    set_metadata(conn, "current_tick", str(tick))
    set_metadata(conn, "updated_at", _sim_ts(tick))
    conn.commit()


def set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sim_metadata (key, value) VALUES (?, ?)",
        (key, value),
    )


def get_metadata(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM sim_metadata WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else None


def upsert_sim_device_state(conn: sqlite3.Connection, state: DeviceRuntimeState) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sim_devices (device_id, data_json) VALUES (?, ?)",
        (state.device_id, _json_dumps(state.model_dump(mode="json"))),
    )


def upsert_sim_interface_state(conn: sqlite3.Connection, state: InterfaceRuntimeState) -> None:
    row_id = f"{state.device_id}:{state.interface_id}"
    conn.execute(
        """
        INSERT OR REPLACE INTO sim_interfaces (id, device_id, interface_id, data_json)
        VALUES (?, ?, ?, ?)
        """,
        (row_id, state.device_id, state.interface_id, _json_dumps(state.model_dump(mode="json"))),
    )


def upsert_sim_link_state(conn: sqlite3.Connection, state: LinkRuntimeState) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sim_links (link_id, data_json) VALUES (?, ?)",
        (state.link_id, _json_dumps(state.model_dump(mode="json"))),
    )


def upsert_sim_service_state(conn: sqlite3.Connection, state: ServiceRuntimeState) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sim_services (service_id, data_json) VALUES (?, ?)",
        (state.service_id, _json_dumps(state.model_dump(mode="json"))),
    )


def list_sim_device_states(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_json_rows(conn, "SELECT data_json FROM sim_devices ORDER BY device_id")


def list_sim_interface_states(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_json_rows(conn, "SELECT data_json FROM sim_interfaces ORDER BY id")


def list_sim_link_states(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_json_rows(conn, "SELECT data_json FROM sim_links ORDER BY link_id")


def list_sim_service_states(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_json_rows(conn, "SELECT data_json FROM sim_services ORDER BY service_id")


def list_sim_probe_defs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_json_rows(conn, "SELECT data_json FROM sim_probes ORDER BY probe_id")


def insert_sim_event(conn: sqlite3.Connection, event: SimulationEvent) -> None:
    conn.execute(
        """
        INSERT INTO sim_events
            (event_id, tick, ts, event_type, target_type, target_id, severity, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.id,
            event.tick,
            event.ts,
            event.event_type,
            event.target_type,
            event.target_id,
            event.severity,
            _json_dumps(event.model_dump(mode="json")),
        ),
    )
    conn.commit()


def list_sim_events(conn: sqlite3.Connection, since_tick: int | None = None) -> list[dict[str, Any]]:
    if since_tick is None:
        return _list_json_rows(conn, "SELECT data_json FROM sim_events ORDER BY tick, event_id")
    return _list_json_rows(
        conn,
        "SELECT data_json FROM sim_events WHERE tick >= ? ORDER BY tick, event_id",
        (since_tick,),
    )


def insert_telemetry_sample(conn: sqlite3.Connection, sample: TelemetrySample) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO sim_telemetry
            (sample_id, tick, ts, source, metric, target_type, target_id, value, unit, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sample.id,
            sample.tick,
            sample.ts,
            sample.source,
            sample.metric,
            sample.target_type,
            sample.target_id,
            sample.value,
            sample.unit,
            _json_dumps(sample.model_dump(mode="json")),
        ),
    )


def list_telemetry_samples(conn: sqlite3.Connection, since_tick: int | None = None) -> list[dict[str, Any]]:
    if since_tick is None:
        return _list_json_rows(conn, "SELECT data_json FROM sim_telemetry ORDER BY tick, sample_id")
    return _list_json_rows(
        conn,
        "SELECT data_json FROM sim_telemetry WHERE tick >= ? ORDER BY tick, sample_id",
        (since_tick,),
    )


def insert_snapshot(conn: sqlite3.Connection, snapshot: MonitoringSnapshot) -> str:
    conn.execute(
        """
        INSERT OR REPLACE INTO sim_snapshots (snapshot_id, tick, ts, data_json)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot.id, snapshot.tick, snapshot.ts, _json_dumps(snapshot.model_dump(mode="json"))),
    )
    conn.commit()
    return snapshot.id


def list_snapshots(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_json_rows(conn, "SELECT data_json FROM sim_snapshots ORDER BY rowid")


def get_snapshot(conn: sqlite3.Connection, snapshot_id_or_alias: str) -> dict[str, Any] | None:
    snapshot_id = _resolve_snapshot_alias(conn, snapshot_id_or_alias)
    if snapshot_id is None:
        return None
    row = conn.execute(
        "SELECT data_json FROM sim_snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def insert_alert(conn: sqlite3.Connection, alert: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO sim_alerts
            (alert_id, tick, ts, severity, alert_type, target_type, target_id, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert["id"],
            alert["tick"],
            alert["ts"],
            alert["severity"],
            alert["alert_type"],
            alert["target_type"],
            alert["target_id"],
            _json_dumps(alert),
        ),
    )


def list_alerts(conn: sqlite3.Connection, since_tick: int | None = None) -> list[dict[str, Any]]:
    if since_tick is None:
        return _list_json_rows(conn, "SELECT data_json FROM sim_alerts ORDER BY tick, alert_id")
    return _list_json_rows(
        conn,
        "SELECT data_json FROM sim_alerts WHERE tick >= ? ORDER BY tick, alert_id",
        (since_tick,),
    )


def insert_normalized_state(conn: sqlite3.Connection, normalized_state: Any) -> str:
    data = normalized_state.model_dump(mode="json")
    conn.execute(
        """
        INSERT OR REPLACE INTO sim_normalized_states (state_id, tick, data_json)
        VALUES (?, ?, ?)
        """,
        (data["id"], data["tick"], _json_dumps(data)),
    )
    conn.execute(
        "DELETE FROM sim_normalized_observations WHERE state_id = ?",
        (data["id"],),
    )
    for observation in data["observations"]:
        conn.execute(
            """
            INSERT OR REPLACE INTO sim_normalized_observations
                (observation_id, state_id, tick, object_type, object_id, data_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                observation["id"],
                data["id"],
                observation["observed_at_tick"],
                observation["object_type"],
                observation["object_id"],
                _json_dumps(observation),
            ),
        )
    conn.commit()
    return data["id"]


def get_normalized_state(conn: sqlite3.Connection, state_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT data_json FROM sim_normalized_states WHERE state_id = ?",
        (state_id,),
    ).fetchone()
    return json.loads(row["data_json"]) if row else None


def list_normalized_observations(
    conn: sqlite3.Connection,
    object_type: str | None = None,
    object_id: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT data_json FROM sim_normalized_observations"
    clauses: list[str] = []
    params: list[Any] = []
    if object_type is not None:
        clauses.append("object_type = ?")
        params.append(object_type)
    if object_id is not None:
        clauses.append("object_id = ?")
        params.append(object_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY tick, observation_id"
    return _list_json_rows(conn, query, tuple(params))


def next_sim_sequence(conn: sqlite3.Connection, table: str, tick: int) -> int:
    table_to_column = {
        "sim_events": "event_id",
        "sim_telemetry": "sample_id",
        "sim_snapshots": "snapshot_id",
        "sim_alerts": "alert_id",
    }
    if table not in table_to_column:
        raise ValueError(f"Unsupported simulation sequence table: {table}")
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE tick = ?", (tick,)).fetchone()
    return int(row["count"]) + 1


def _resolve_snapshot_alias(conn: sqlite3.Connection, snapshot_id_or_alias: str) -> str | None:
    if not snapshot_id_or_alias.startswith("latest"):
        return snapshot_id_or_alias
    rows = conn.execute(
        "SELECT snapshot_id FROM sim_snapshots ORDER BY rowid DESC"
    ).fetchall()
    if not rows:
        return None
    if snapshot_id_or_alias == "latest":
        index = 0
    else:
        try:
            index = int(snapshot_id_or_alias.split("-", 1)[1])
        except (IndexError, ValueError):
            raise ValueError(f"Invalid snapshot alias: {snapshot_id_or_alias}") from None
    if index >= len(rows):
        return None
    return rows[index]["snapshot_id"]


def _list_json_rows(
    conn: sqlite3.Connection,
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    rows = conn.execute(query, params).fetchall()
    return [json.loads(row["data_json"]) for row in rows]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _sim_ts(tick: int) -> str:
    return f"tick-{tick:06d}"
