from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from netfabric_mini.db import (
    insert_acl_rule,
    insert_device,
    insert_link,
    insert_metric,
    insert_raw_log,
    insert_ticket,
    reset_case_tables,
)
from netfabric_mini.schemas import AclRulesFile, MetricsFile, RawLog, TicketsFile, TopologyFile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_DIR = PROJECT_ROOT / "data" / "cases"
REQUIRED_CASE_FILES = {
    "topology.yaml",
    "acl_rules.yaml",
    "raw_logs.txt",
    "metrics.yaml",
    "tickets.yaml",
}


def list_cases(cases_dir: Path | None = None) -> list[str]:
    root = cases_dir or DEFAULT_CASES_DIR
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def load_case(
    conn: sqlite3.Connection,
    case_name: str,
    cases_dir: Path | None = None,
    *,
    reset: bool = True,
) -> dict[str, Any]:
    root = cases_dir or DEFAULT_CASES_DIR
    case_dir = root / case_name
    if not case_dir.exists() or not case_dir.is_dir():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    missing = sorted(filename for filename in REQUIRED_CASE_FILES if not (case_dir / filename).exists())
    if missing:
        raise ValueError(f"Case {case_name!r} missing required file(s): {', '.join(missing)}")

    topology = TopologyFile.model_validate(_read_yaml(case_dir / "topology.yaml"))
    acl_rules = AclRulesFile.model_validate(_read_yaml(case_dir / "acl_rules.yaml"))
    metrics = MetricsFile.model_validate(_read_yaml(case_dir / "metrics.yaml"))
    tickets = TicketsFile.model_validate(_read_yaml(case_dir / "tickets.yaml"))
    raw_lines = [
        line.strip()
        for line in (case_dir / "raw_logs.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if reset:
        reset_case_tables(conn)

    for device in topology.devices:
        insert_device(conn, device)
    for index, link in enumerate(topology.links, start=1):
        insert_link(conn, f"link-{index:04d}", link)
    for rule in acl_rules.acl_rules:
        insert_acl_rule(conn, rule)
    for ticket in tickets.tickets:
        insert_ticket(conn, ticket)
    for metric in metrics.metrics:
        insert_metric(conn, metric)
    for index, line in enumerate(raw_lines, start=1):
        insert_raw_log(conn, RawLog(id=f"rawlog-{index:04d}", line=line))

    conn.commit()

    return {
        "case_name": case_name,
        "devices": len(topology.devices),
        "links": len(topology.links),
        "raw_logs": len(raw_lines),
        "acl_rules": len(acl_rules.acl_rules),
        "tickets": len(tickets.tickets),
        "metrics": len(metrics.metrics),
    }


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML in {path}: {exc}") from exc

