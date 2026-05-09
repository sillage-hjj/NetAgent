from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from typing import Any

from netagent_lab.db import insert_event, query_all
from netagent_lab.schemas import ParsedEvent


Parser = Callable[[str, str], ParsedEvent | None]


LINK_RE = re.compile(
    r"^(?P<ts>\S+) (?P<device>\S+) %LINK-(?P<severity>\d+)-UPDOWN: "
    r"Interface (?P<interface>\S+) changed state to (?P<state>up|down)$",
    re.IGNORECASE,
)
ROUTING_RE = re.compile(
    r"^(?P<ts>\S+) (?P<device>\S+) %(?P<protocol>OSPF)-(?P<severity>\d+)-ADJCHG: "
    r"Neighbor (?P<neighbor>\S+) on (?P<interface>\S+) from "
    r"(?P<from_state>\S+) to (?P<to_state>\S+)$",
    re.IGNORECASE,
)
ACL_DENY_RE = re.compile(
    r"^(?P<ts>\S+) (?P<device>\S+) %ACL-(?P<severity>\d+)-DENY: "
    r"(?P<protocol>\S+) (?P<src_ip>[0-9.]+):(?P<src_port>\d+) -> "
    r"(?P<dst_ip>[0-9.]+):(?P<dst_port>\d+) denied by (?P<acl_name>\S+)$",
    re.IGNORECASE,
)
CPU_HIGH_RE = re.compile(
    r"^(?P<ts>\S+) (?P<device>\S+) %CPU-(?P<severity>\d+)-HIGH: "
    r"CPU utilization (?P<utilization_percent>\d+) percent for "
    r"(?P<duration_seconds>\d+) seconds$",
    re.IGNORECASE,
)
PACKET_LOSS_RE = re.compile(
    r"^(?P<ts>\S+) (?P<device>\S+) %SLA-(?P<severity>\d+)-LOSS: "
    r"Packet loss to (?P<target_ip>[0-9.]+) is (?P<loss_percent>\d+) percent over "
    r"(?P<duration_seconds>\d+) seconds$",
    re.IGNORECASE,
)


def parse_log_line(raw_log_id: str, line: str) -> ParsedEvent | None:
    for parser in PARSERS:
        event = parser(raw_log_id, line)
        if event is not None:
            return event
    return None


def parse_and_store_all(conn: sqlite3.Connection) -> dict[str, Any]:
    conn.execute("DELETE FROM events")
    parsed = 0
    skipped = 0
    for raw_log in query_all(conn, "raw_logs"):
        event = parse_log_line(raw_log["id"], raw_log["line"])
        if event is None:
            skipped += 1
            continue
        insert_event(conn, event)
        parsed += 1
    conn.commit()
    return {"parsed_events": parsed, "skipped_logs": skipped}


def _parse_link_state_change(raw_log_id: str, line: str) -> ParsedEvent | None:
    match = LINK_RE.match(line)
    if not match:
        return None
    data = match.groupdict()
    return _event(
        raw_log_id,
        data,
        "link_state_change",
        {
            "interface": data["interface"],
            "state": data["state"].lower(),
        },
    )


def _parse_routing_neighbor_change(raw_log_id: str, line: str) -> ParsedEvent | None:
    match = ROUTING_RE.match(line)
    if not match:
        return None
    data = match.groupdict()
    return _event(
        raw_log_id,
        data,
        "routing_neighbor_change",
        {
            "protocol": data["protocol"].upper(),
            "neighbor": data["neighbor"],
            "interface": data["interface"],
            "from_state": data["from_state"].upper(),
            "to_state": data["to_state"].upper(),
        },
    )


def _parse_acl_deny(raw_log_id: str, line: str) -> ParsedEvent | None:
    match = ACL_DENY_RE.match(line)
    if not match:
        return None
    data = match.groupdict()
    return _event(
        raw_log_id,
        data,
        "acl_deny",
        {
            "protocol": data["protocol"].lower(),
            "src_ip": data["src_ip"],
            "src_port": int(data["src_port"]),
            "dst_ip": data["dst_ip"],
            "dst_port": int(data["dst_port"]),
            "acl_name": data["acl_name"],
        },
    )


def _parse_cpu_high(raw_log_id: str, line: str) -> ParsedEvent | None:
    match = CPU_HIGH_RE.match(line)
    if not match:
        return None
    data = match.groupdict()
    return _event(
        raw_log_id,
        data,
        "cpu_high",
        {
            "utilization_percent": int(data["utilization_percent"]),
            "duration_seconds": int(data["duration_seconds"]),
        },
    )


def _parse_packet_loss(raw_log_id: str, line: str) -> ParsedEvent | None:
    match = PACKET_LOSS_RE.match(line)
    if not match:
        return None
    data = match.groupdict()
    return _event(
        raw_log_id,
        data,
        "packet_loss",
        {
            "target_ip": data["target_ip"],
            "loss_percent": int(data["loss_percent"]),
            "duration_seconds": int(data["duration_seconds"]),
        },
    )


def _event(raw_log_id: str, data: dict[str, str], event_type: str, params: dict[str, Any]) -> ParsedEvent:
    event_id = raw_log_id.replace("rawlog-", "event-", 1)
    return ParsedEvent(
        id=event_id,
        ts=data["ts"],
        device=data["device"],
        event_type=event_type,
        severity=data["severity"],
        params=params,
        raw_log_id=raw_log_id,
    )


PARSERS: tuple[Parser, ...] = (
    _parse_link_state_change,
    _parse_routing_neighbor_change,
    _parse_acl_deny,
    _parse_cpu_high,
    _parse_packet_loss,
)

