from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.agent_tools._common import ok_result
from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.reasoning.diff import diff_latest_snapshots as _diff_latest


def list_snapshots(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("list_snapshots", {"snapshots": KnowledgeBase.from_db(conn).list_snapshots()})


def diff_latest_snapshots(conn: sqlite3.Connection, args: dict[str, Any]):
    return ok_result("diff_latest_snapshots", _diff_latest(KnowledgeBase.from_db(conn)))

