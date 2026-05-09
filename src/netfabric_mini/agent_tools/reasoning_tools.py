from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.agent_tools._common import ok_result
from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.reasoning.alerts import evaluate_alerts as _evaluate_alerts
from netfabric_mini.reasoning.diff import diff_snapshots as _diff_snapshots
from netfabric_mini.reasoning.health import evaluate_device_health as _evaluate_device_health
from netfabric_mini.reasoning.health import evaluate_link_health as _evaluate_link_health
from netfabric_mini.reasoning.health import evaluate_service_health as _evaluate_service_health
from netfabric_mini.reasoning.pathing import infer_path as _infer_path
from netfabric_mini.reasoning.reachability import check_service_reachability as _check_service
from netfabric_mini.reasoning.reachability import collect_reachability_matrix as _reachability_matrix


def infer_path(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("infer_path", _infer_path(KnowledgeBase.from_db(conn), args["src_device"], args["dst_device"]))


def check_service_reachability(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("check_service_reachability", _check_service(KnowledgeBase.from_db(conn), args["source_device"], args["service_id"]))


def get_reachability_matrix(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("get_reachability_matrix", _reachability_matrix(KnowledgeBase.from_db(conn)))


def evaluate_link_health(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("evaluate_link_health", _evaluate_link_health(KnowledgeBase.from_db(conn), args["link_id"]))


def evaluate_device_health(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("evaluate_device_health", _evaluate_device_health(KnowledgeBase.from_db(conn), args["device_id"]))


def evaluate_service_health(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("evaluate_service_health", _evaluate_service_health(KnowledgeBase.from_db(conn), args["service_id"]))


def evaluate_alerts(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("evaluate_alerts", {"alerts": _evaluate_alerts(KnowledgeBase.from_db(conn))})


def diff_snapshots(conn: sqlite3.Connection, args: dict[str, Any]):
    kb = KnowledgeBase.from_db(conn)
    before = kb.get_snapshot(args["from_snapshot"])
    after = kb.get_snapshot(args["to_snapshot"])
    if before is None or after is None:
        raise ValueError("Requested snapshots are not available")
    return ok_result("diff_snapshots", _diff_snapshots(before, after))

